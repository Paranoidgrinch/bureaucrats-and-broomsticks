"""Stronger hand-authored heuristic policy for full-campaign diagnostics.

HeuristicV2 is deliberately separate from the old HeuristicPolicy:
- the old policy remains a stable keyword baseline
- this policy inspects real card definitions and effect payloads where possible
- it still only uses the public Observation interface, so event/shop decisions remain coarse
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.models import Card
from bab.sim.rl_env import Action, Observation

_ALL_CARD_DEFINITIONS: dict[str, Card] | None = None


def _all_card_definitions() -> dict[str, Card]:
    global _ALL_CARD_DEFINITIONS
    if _ALL_CARD_DEFINITIONS is None:
        cards: dict[str, Card] = {}
        for manifest_path in ACT_MANIFEST_FILES:
            catalog = load_content_catalog_from_act_manifest(manifest_path)
            cards.update(catalog.card_database)
        _ALL_CARD_DEFINITIONS = cards
    return _ALL_CARD_DEFINITIONS


@dataclass(frozen=True)
class CardEstimate:
    damage: int = 0
    aoe_damage: int = 0
    block: int = 0
    draw: int = 0
    energy: int = 0
    heal: int = 0
    self_strength: int = 0
    enemy_debuff: int = 0
    paperwork: int = 0
    paperwork_damage_per_stack: int = 0
    exhaust_or_remove: bool = False
    scaling: int = 0
    utility: int = 0


class HeuristicV2Policy:
    """Effect-aware heuristic policy for campaign benchmarking.

    It is intentionally deterministic-ish and explainable. It does not mutate the
    environment and it does not require private CombatState access.
    """

    name = "heuristic_v2"

    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = Random(seed)
        self.card_database = _all_card_definitions()

    def choose_action(self, observation: Observation) -> Action:
        legal_actions = [action for action in observation.legal_actions if action.kind != "noop"]
        if not legal_actions:
            return Action("noop")

        if observation.phase == "combat":
            return self._choose_combat_action(observation, legal_actions)
        if observation.phase == "map":
            return self._choose_map_action(observation, legal_actions)
        if observation.phase == "card_reward":
            return self._choose_card_reward_action(observation, legal_actions)

        return self.rng.choice(legal_actions)

    def _choose_combat_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        play_actions = [action for action in legal_actions if action.kind == "play_card"]
        end_turn_actions = [action for action in legal_actions if action.kind == "end_turn"]

        if not play_actions:
            return end_turn_actions[0] if end_turn_actions else self.rng.choice(legal_actions)

        scored_actions = [
            (self._score_combat_action(observation, action), action)
            for action in play_actions
        ]
        best_score, best_action = self._best(scored_actions)

        # Avoid spending actions on almost-useless cards when ending is legal.
        if end_turn_actions and best_score < 0.25:
            return end_turn_actions[0]
        return best_action

    def _score_combat_action(self, observation: Observation, action: Action) -> float:
        if action.index is None or action.index >= len(observation.hand_card_ids):
            return -999.0

        card_id = observation.hand_card_ids[action.index]
        card = self.card_database.get(card_id)
        cost = observation.hand_card_costs[action.index]
        estimate = self._estimate_card(card_id, card)

        hp_ratio = observation.hp / max(1, observation.max_hp)
        incoming = max(0, observation.incoming_damage)
        living_enemy_count = sum(1 for hp in observation.enemy_hp if hp > 0)
        energy = observation.energy if observation.energy is not None else 0

        score = 0.0

        target_hp = None
        target_block = 0
        target_paperwork = 0
        if action.target_index is not None and action.target_index < len(observation.enemy_hp):
            target_hp = observation.enemy_hp[action.target_index]
            target_block = observation.enemy_block[action.target_index]
            target_paperwork = self._enemy_status_amount(
                observation,
                action.target_index,
                "paperwork",
            )
            effective_target_hp = max(0, target_hp + target_block)
        else:
            effective_target_hp = 0

        dynamic_status_damage = estimate.paperwork_damage_per_stack * target_paperwork
        single_damage = estimate.damage + dynamic_status_damage
        aoe_total_damage = estimate.aoe_damage * max(1, living_enemy_count)
        total_damage = single_damage + aoe_total_damage

        if target_hp is not None and target_hp > 0:
            damage_into_target = min(single_damage + estimate.aoe_damage, effective_target_hp)
            score += damage_into_target * 2.1

            if single_damage + estimate.aoe_damage >= effective_target_hp and target_hp > 0:
                score += 75.0
                score -= max(0, single_damage + estimate.aoe_damage - effective_target_hp) * 0.2
            else:
                score += max(0.0, 25.0 - effective_target_hp) * 0.15
        else:
            score += total_damage * 1.5

        if estimate.aoe_damage and living_enemy_count >= 2:
            score += estimate.aoe_damage * living_enemy_count * 1.7
            score += 5.0 * min(3, living_enemy_count)

        block_needed = incoming
        if block_needed > 0:
            useful_block = min(estimate.block, block_needed)
            excess_block = max(0, estimate.block - block_needed)
            score += useful_block * (2.6 if hp_ratio < 0.55 else 2.0)
            score += excess_block * 0.25

            if observation.hp <= incoming and estimate.block >= incoming - observation.hp + 1:
                score += 60.0
            if hp_ratio < 0.35 and estimate.block > 0:
                score += 15.0
        else:
            score += estimate.block * 0.3

        # Value and setup. Prefer setup when not under severe pressure.
        pressure = incoming / max(1, observation.max_hp)
        setup_multiplier = 0.6 if pressure > 0.25 else 1.0
        score += estimate.draw * 3.0 * setup_multiplier
        score += estimate.energy * 3.5 * setup_multiplier
        score += estimate.self_strength * 5.0 * setup_multiplier
        score += estimate.scaling * 2.5 * setup_multiplier
        score += estimate.utility * 1.5
        score += estimate.enemy_debuff * (4.0 if incoming > 0 else 2.0)
        score += estimate.paperwork * (2.5 + min(6.0, target_paperwork * 0.35))
        if dynamic_status_damage:
            score += dynamic_status_damage * 2.2
        score += estimate.heal * (2.0 if hp_ratio < 0.75 else 0.5)

        player_paperwork = self._player_status_amount(observation, "paperwork")
        player_panic = self._player_status_amount(observation, "panic")
        player_doubt = self._player_status_amount(observation, "doubt")
        if player_paperwork or player_panic or player_doubt:
            if estimate.block:
                score += min(12.0, estimate.block * 0.35)
            if estimate.draw or estimate.energy:
                score += 1.5

        # Spend energy, but do not blindly prefer expensive low-impact cards.
        if energy > 0:
            score += min(cost, energy) * 0.35
        score -= max(0, cost - 1) * 0.15

        # Class/archetype and relic support.
        score += self._class_synergy_score(observation.character_id, card_id, card) * 0.8
        score += self._relic_synergy_score(observation, card_id, card) * 0.7

        if observation.draw_pile_size <= 3 and estimate.draw > 0:
            score += 3.0
        if observation.discard_pile_size >= 8 and any(word in card_id.lower() for word in ("shuffle", "archive", "recover", "return")):
            score += 3.0

        return score

    def _choose_map_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        map_actions = [
            action
            for action in legal_actions
            if action.kind == "choose_map_node" and action.index is not None
        ]
        if not map_actions:
            return self.rng.choice(legal_actions)

        return self._best(
            [(self._score_map_action(observation, action), action) for action in map_actions]
        )[1]

    def _score_map_action(self, observation: Observation, action: Action) -> float:
        if action.index is None or action.index >= len(observation.available_map_node_types):
            return -999.0

        node_type = observation.available_map_node_types[action.index]
        hp_ratio = observation.hp / max(1, observation.max_hp)

        base_scores = {
            "boss": 100.0,
            "waiting_room": 22.0,
            "treasure": 30.0,
            "combat": 24.0,
            "event": 15.0,
            "shop": 10.0,
            "elite": 4.0,
        }
        score = base_scores.get(node_type, 0.0)

        if node_type == "waiting_room":
            if hp_ratio < 0.35:
                score += 70.0
            elif hp_ratio < 0.55:
                score += 40.0
            elif hp_ratio < 0.75:
                score += 12.0

        if node_type == "elite":
            deck_quality = self._deck_quality(observation)
            if hp_ratio >= 0.85 and deck_quality >= 0:
                score += 38.0
            elif hp_ratio >= 0.70:
                score += 18.0
            elif hp_ratio < 0.50:
                score -= 35.0

        if node_type == "shop":
            if observation.gold >= 220:
                score += 36.0
            elif observation.gold >= 130:
                score += 24.0
            elif observation.gold >= 75:
                score += 10.0
            else:
                score -= 18.0

        if node_type == "event":
            if hp_ratio < 0.45:
                score -= 8.0
            if observation.gold < 40:
                score += 3.0

        return score

    def _choose_card_reward_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        reward_actions = [
            action
            for action in legal_actions
            if action.kind == "choose_card_reward" and action.index is not None
        ]
        skip_actions = [action for action in legal_actions if action.kind == "skip_card_reward"]

        if not reward_actions:
            return self.rng.choice(legal_actions)

        scored = [
            (self._score_reward_card(observation, action), action)
            for action in reward_actions
        ]
        best_score, best_action = self._best(scored)

        # HeuristicV2 skips mediocre cards aggressively once the deck is large.
        skip_threshold = 2.5
        if observation.deck_size >= 24:
            skip_threshold += 1.5
        if observation.deck_size >= 32:
            skip_threshold += 2.0

        if skip_actions and best_score < skip_threshold:
            return skip_actions[0]
        return best_action

    def _score_reward_card(self, observation: Observation, action: Action) -> float:
        if action.index is None or action.index >= len(observation.reward_card_ids):
            return -999.0

        card_id = observation.reward_card_ids[action.index]
        card = self.card_database.get(card_id)
        estimate = self._estimate_card(card_id, card)
        deck_profile = self._deck_profile(observation.deck_card_ids)

        score = 0.0
        score += estimate.damage * 0.35
        score += estimate.aoe_damage * 0.75
        score += estimate.block * 0.30
        score += estimate.draw * 2.5
        score += estimate.energy * 3.0
        score += estimate.self_strength * 3.0
        score += estimate.enemy_debuff * 1.8
        score += estimate.paperwork * 2.2
        score += estimate.scaling * 1.8
        score += estimate.utility * 1.0

        if card is not None:
            if card.rarity == "rare":
                score += 1.5
            elif card.rarity == "uncommon":
                score += 0.8
            elif card.rarity == "common":
                score += 0.2

            score += self._class_synergy_score(observation.character_id, card_id, card)

            tags = set(getattr(card, "tags", []))
            if "starter" in tags:
                score -= 4.0
            if "upgraded" in tags:
                score += 1.5

        lower_id = card_id.lower()
        if any(word in lower_id for word in ("curse", "junk", "wound", "clutter", "dead_weight")):
            score -= 20.0

        # Deck-shaping: patch holes before greedily adding more damage.
        if deck_profile["block"] < 4 and estimate.block > 0:
            score += 4.0
        if deck_profile["damage"] < 5 and (estimate.damage > 0 or estimate.aoe_damage > 0):
            score += 3.0
        if deck_profile["draw"] < 2 and estimate.draw > 0:
            score += 4.0
        if deck_profile["energy"] < 1 and estimate.energy > 0:
            score += 4.0
        if deck_profile["scaling"] < 2 and (estimate.self_strength > 0 or estimate.scaling > 0):
            score += 3.5

        # Avoid bloat.
        if observation.deck_size >= 22:
            score -= 1.5
        if observation.deck_size >= 30:
            score -= 3.0
        if observation.deck_size >= 38:
            score -= 5.0

        return score

    def _estimate_card(self, card_id: str, card: Card | None) -> CardEstimate:
        if card is None:
            return self._keyword_estimate(card_id)

        damage = 0
        aoe_damage = 0
        block = 0
        draw = 0
        energy = 0
        heal = 0
        self_strength = 0
        enemy_debuff = 0
        paperwork = 0
        paperwork_damage_per_stack = 0
        scaling = 0
        utility = 0
        exhaust_or_remove = False

        for effect in getattr(card, "effects", []):
            effect_type = str(getattr(effect, "type", "")).lower()
            target = str(getattr(effect, "target", "") or "").lower()
            status = str(getattr(effect, "status", "") or "").lower()
            resource = str(getattr(effect, "resource", "") or "").lower()
            destination = str(getattr(effect, "destination", "") or "").lower()
            amount = self._effect_amount(effect)
            amount_per_stack = self._effect_amount_per_stack(effect)

            if effect_type in {"deal_damage", "conditional_damage"}:
                if target == "all_enemies":
                    aoe_damage += amount
                else:
                    damage += amount

            elif effect_type == "damage_per_status":
                per_stack = amount_per_stack if amount_per_stack > 0 else max(1, amount)
                # Observation does not expose enemy status stacks yet, so this is
                # valued as scaling/potential plus a small conservative damage proxy.
                if target == "all_enemies":
                    aoe_damage += per_stack
                else:
                    damage += per_stack
                scaling += per_stack
                if status == "paperwork":
                    paperwork += 1
                    paperwork_damage_per_stack += per_stack

            elif effect_type == "gain_block":
                block += amount

            elif effect_type in {"draw_cards", "conditional_draw"}:
                draw += max(1, amount)

            elif effect_type == "discard_cards":
                # Discard can be positive with synergies, but without hand/discard
                # context it should not be valued like draw.
                utility -= max(1, amount) * 0.5

            elif effect_type == "gain_resource":
                if resource == "energy":
                    energy += max(1, amount)
                else:
                    utility += max(1, amount)

            elif effect_type == "gain_strength":
                if target in {"self", "player", "owner", ""}:
                    self_strength += max(1, amount)
                    scaling += max(1, amount)
                else:
                    enemy_debuff += max(1, amount)

            elif effect_type == "apply_status":
                if status == "paperwork":
                    if target in {"enemy", "all_enemies", "random_enemy", "first_enemy"}:
                        paperwork += max(1, amount)
                        scaling += max(0, amount // 2)
                    else:
                        utility -= max(1, amount)
                elif status == "strength":
                    if target in {"self", "player", "owner"}:
                        self_strength += max(1, amount)
                        scaling += max(1, amount)
                    else:
                        enemy_debuff -= max(1, amount)
                elif target in {"enemy", "all_enemies", "random_enemy", "first_enemy"}:
                    enemy_debuff += max(1, amount)
                elif target in {"self", "player", "owner"}:
                    # Some self-statuses are good, some are bad. Without status
                    # semantics in Observation, keep this conservative.
                    utility += max(0, amount // 2)
                else:
                    utility += 1

            elif effect_type == "remove_status":
                utility += max(1, amount)

            elif effect_type == "modify_card_cost":
                energy += max(1, amount)
                utility += 1

            elif effect_type == "skip_action":
                if target in {"enemy", "all_enemies", "random_enemy", "first_enemy"}:
                    enemy_debuff += 3
                else:
                    utility += 1

            elif effect_type == "create_card":
                copies = self._effect_copies(effect)
                created_card_id = getattr(effect, "card_id", None)
                if destination in {"hand", "draw", "draw_pile"}:
                    utility += copies * 2
                elif destination in {"discard", "discard_pile", ""}:
                    utility += copies
                elif destination in {"exhaust", "exhaust_pile"}:
                    utility += 0

                # If the created card is known, add a small hint from its text/ID.
                if created_card_id:
                    utility += self._keyword_estimate(str(created_card_id)).utility
                    created_estimate = self._keyword_estimate(str(created_card_id))
                    damage += max(0, created_estimate.damage // 3)
                    block += max(0, created_estimate.block // 3)

            elif effect_type == "exhaust_cards_by_tag":
                exhaust_or_remove = True
                utility += max(2, amount if amount > 0 else 2)

            else:
                utility += 1

        if not any(
            (
                damage,
                aoe_damage,
                block,
                draw,
                energy,
                heal,
                self_strength,
                enemy_debuff,
                paperwork,
                scaling,
                utility,
            )
        ):
            return self._keyword_estimate(card_id)

        return CardEstimate(
            damage=damage,
            aoe_damage=aoe_damage,
            block=block,
            draw=draw,
            energy=energy,
            heal=heal,
            self_strength=self_strength,
            enemy_debuff=enemy_debuff,
            paperwork=paperwork,
            paperwork_damage_per_stack=paperwork_damage_per_stack,
            exhaust_or_remove=exhaust_or_remove,
            scaling=scaling,
            utility=utility,
        )


    def _keyword_estimate(self, card_id: str) -> CardEstimate:
        text = card_id.lower()
        damage = 8 if any(word in text for word in ("attack", "strike", "stab", "damage", "blast", "bolt", "hit", "smite")) else 0
        block = 7 if any(word in text for word in ("block", "defend", "guard", "shield", "ward", "barrier")) else 0
        draw = 1 if any(word in text for word in ("draw", "memo", "file", "form", "archive", "report")) else 0
        energy = 1 if any(word in text for word in ("energy", "free", "refund", "coffee", "haste")) else 0
        paperwork = 2 if "paperwork" in text or "stamp" in text or "form" in text else 0
        scaling = 1 if any(word in text for word in ("strength", "ritual", "engine", "engine", "scaling")) else 0
        return CardEstimate(
            damage=damage,
            block=block,
            draw=draw,
            energy=energy,
            paperwork=paperwork,
            scaling=scaling,
        )

    def _effect_amount(self, effect: Any) -> int:
        value = getattr(effect, "amount", None)
        if isinstance(value, int):
            return max(0, value)
        return 0

    def _effect_amount_per_stack(self, effect: Any) -> int:
        value = getattr(effect, "amount_per_stack", None)
        if isinstance(value, int):
            return max(0, value)
        return 0

    def _effect_copies(self, effect: Any) -> int:
        value = getattr(effect, "copies", None)
        if isinstance(value, int):
            return max(0, value)
        value = getattr(effect, "amount", None)
        if isinstance(value, int):
            return max(0, value)
        return 1


    def _player_status_amount(self, observation: Observation, status_id: str) -> int:
        for index, current_status_id in enumerate(observation.player_status_ids):
            if current_status_id == status_id and index < len(observation.player_status_amounts):
                return observation.player_status_amounts[index]
        return 0

    def _enemy_status_amount(
        self,
        observation: Observation,
        enemy_index: int,
        status_id: str,
    ) -> int:
        if enemy_index >= len(observation.enemy_status_ids):
            return 0

        status_ids = observation.enemy_status_ids[enemy_index]
        status_amounts = observation.enemy_status_amounts[enemy_index]

        for index, current_status_id in enumerate(status_ids):
            if current_status_id == status_id and index < len(status_amounts):
                return status_amounts[index]
        return 0

    def _relic_synergy_score(
        self,
        observation: Observation,
        card_id: str,
        card: Card | None,
    ) -> float:
        if not observation.relic_ids:
            return 0.0

        text_parts = [card_id.lower()]
        if card is not None:
            text_parts.extend(str(tag).lower() for tag in getattr(card, "tags", []))
            text_parts.append(str(getattr(card, "name", "")).lower())

        card_text = " ".join(text_parts)
        relic_text = " ".join(relic_id.lower() for relic_id in observation.relic_ids)

        score = 0.0

        if "paperwork" in relic_text and any(
            word in card_text for word in ("paperwork", "stamp", "form", "file")
        ):
            score += 3.0

        if any(word in relic_text for word in ("block", "shield", "guard", "ward")) and any(
            word in card_text for word in ("block", "shield", "guard", "ward")
        ):
            score += 2.0

        if any(word in relic_text for word in ("poison", "bleed", "stab", "assassin")) and any(
            word in card_text for word in ("poison", "bleed", "stab", "dagger")
        ):
            score += 2.0

        if any(word in relic_text for word in ("draw", "archive", "memo", "file")) and any(
            word in card_text for word in ("draw", "archive", "memo", "file")
        ):
            score += 2.0

        if "energy" in relic_text and any(
            word in card_text for word in ("energy", "refund", "free")
        ):
            score += 2.0

        return score

    def _deck_profile(self, deck_card_ids: tuple[str, ...]) -> dict[str, int]:
        profile = {
            "damage": 0,
            "block": 0,
            "draw": 0,
            "energy": 0,
            "paperwork": 0,
            "scaling": 0,
        }
        for card_id in deck_card_ids:
            estimate = self._estimate_card(card_id, self.card_database.get(card_id))
            if estimate.damage or estimate.aoe_damage:
                profile["damage"] += 1
            if estimate.block:
                profile["block"] += 1
            if estimate.draw:
                profile["draw"] += 1
            if estimate.energy:
                profile["energy"] += 1
            if estimate.paperwork:
                profile["paperwork"] += 1
            if estimate.scaling or estimate.self_strength:
                profile["scaling"] += 1
        return profile

    def _deck_quality(self, observation: Observation) -> float:
        profile = self._deck_profile(observation.deck_card_ids)
        return (
            profile["damage"] * 1.0
            + profile["block"] * 0.8
            + profile["draw"] * 1.2
            + profile["energy"] * 1.2
            + profile["scaling"] * 1.0
            - max(0, observation.deck_size - 24) * 0.15
        )

    def _class_synergy_score(self, character_id: str, card_id: str, card: Card | None) -> float:
        text_parts = [card_id.lower()]
        if card is not None:
            text_parts.extend(str(tag).lower() for tag in getattr(card, "tags", []))
            text_parts.append(str(getattr(card, "name", "")).lower())
        text = " ".join(text_parts)

        synergy_keywords = {
            "bureaucrat": ("paperwork", "stamp", "form", "file", "ledger", "archive"),
            "failed_wizard": ("spell", "mana", "arcane", "blast", "random", "volatile"),
            "guild_assassin_apprentice": ("stab", "poison", "bleed", "critical", "shadow", "dagger"),
            "hedge_witch": ("brew", "herb", "ward", "curse", "hex", "poultice"),
            "mortuary_apprentice": ("bone", "spirit", "grave", "corpse", "mortuary", "soul"),
            "night_watch_recruit": ("guard", "watch", "shield", "patrol", "block", "arrest"),
            "sewer_diplomat": ("rat", "sewer", "diplomacy", "negotiate", "stench", "filth"),
            "shroomancer": ("spore", "mushroom", "fungus", "compost", "rot", "bloom"),
            "witch_clerk": ("hex", "file", "charm", "curse", "memo", "ward"),
        }

        score = 0.0
        for keyword in synergy_keywords.get(character_id, ()):
            if keyword in text:
                score += 2.0
        return score

    def _best(self, scored_actions: list[tuple[float, Action]]) -> tuple[float, Action]:
        best_score = max(score for score, _action in scored_actions)
        best_actions = [action for score, action in scored_actions if score == best_score]
        return best_score, self.rng.choice(best_actions)
