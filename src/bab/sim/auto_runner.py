"""Headless random-run simulator.

The simulator deliberately makes naive random choices:
- random character
- random map path
- random playable cards
- random targets
- random card rewards or skip
- random event choices
- random shop purchases

It is not meant to play well. It is meant to expose bugs and produce rough
balancing signals.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import ceil
from random import Random
import traceback
from typing import Any

from bab.combat.deck import shuffle_draw_pile
from bab.combat.effects import resolve_card
from bab.combat.enemies import create_enemies_for_encounter
from bab.combat.state import CombatState, Combatant
from bab.combat.turns import end_player_turn, run_enemy_turn, start_player_turn
from bab.console.run_flow import create_run_state
from bab.content.catalog import ContentCatalog, load_default_content_catalog
from bab.models import Card, EventDefinition, RelicDefinition
from bab.run.map import MapNode
from bab.run.state import (
    RunState,
    complete_current_map_node,
    create_combat_state_for_next_encounter,
    enter_map_node,
    finish_victorious_combat,
)
from bab.systems.act_progression import advance_to_next_act, has_next_act
from bab.systems.card_removal import remove_card_from_deck, removable_card_indices
from bab.systems.relics import (
    apply_combat_start_relics,
    apply_relic_pickup_effects_to_run_state,
    card_reward_count_bonus,
    shop_price_discount_percent,
)
from bab.systems.rewards import choose_card_rewards, choose_epic_card_rewards
from bab.systems.shop import (
    DEFAULT_SHOP_CARD_OFFER_COUNT,
    DEFAULT_SHOP_RELIC_OFFER_COUNT,
    card_removal_price,
    choose_shop_card_offers,
    choose_shop_relic_offers,
    discounted_shop_price,
)


@dataclass
class SimConfig:
    runs: int = 1000
    seed: int = 1
    max_combat_turns: int = 80
    reward_skip_chance: float = 0.20
    card_play_stop_chance: float = 0.12
    shop_leave_chance: float = 0.25
    shop_buy_attempt_limit: int = 20


@dataclass
@dataclass
@dataclass
class SimulatedRun:
    index: int
    seed: int
    character_id: str
    outcome: str
    completed_nodes: int
    fights_won: int
    gold: int
    deck_size: int
    relic_count: int
    error: str | None = None
    traceback: str | None = None
    last_node_id: str | None = None
    last_node_type: str | None = None
    last_node_depth: int | None = None
    last_encounter_id: str | None = None
    last_encounter_name: str | None = None
    last_enemy_ids: list[str] | None = None
    last_enemy_names: list[str] | None = None
    last_enemy_hp: dict[str, int] | None = None
    last_player_hp: int | None = None
    last_player_hp_before_node: int | None = None
    last_player_hp_after_node: int | None = None
    last_combat_turns: int | None = None
    path_history: list[dict[str, Any]] | None = None


@dataclass
class SimulationSummary:
    total_runs: int
    wins: int
    defeats: int
    errors: int
    stalled: int
    win_rate: float
    defeat_rate: float
    error_rate: float
    average_completed_nodes: float
    average_fights_won: float
    average_gold: float
    results: list[SimulatedRun]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["results"] = [asdict(result) for result in self.results]
        return data


def simulate_runs(
    config: SimConfig,
    *,
    catalog: ContentCatalog | None = None,
    raise_errors: bool = False,
) -> SimulationSummary:
    if catalog is None:
        catalog = load_default_content_catalog()

    results: list[SimulatedRun] = []

    for index in range(config.runs):
        run_seed = config.seed + index
        result = simulate_one_run(
            index=index,
            seed=run_seed,
            config=config,
            catalog=catalog,
        )

        if raise_errors and result.error is not None:
            raise AssertionError(
                f"Simulation run {index} failed with {result.error}\n"
                f"{result.traceback or ''}"
            )

        results.append(result)

    total_runs = len(results)
    wins = sum(result.outcome == "win" for result in results)
    defeats = sum(result.outcome == "defeat" for result in results)
    errors = sum(result.outcome == "error" for result in results)
    stalled = sum(result.outcome == "stalled" for result in results)

    return SimulationSummary(
        total_runs=total_runs,
        wins=wins,
        defeats=defeats,
        errors=errors,
        stalled=stalled,
        win_rate=wins / total_runs if total_runs else 0.0,
        defeat_rate=defeats / total_runs if total_runs else 0.0,
        error_rate=errors / total_runs if total_runs else 0.0,
        average_completed_nodes=sum(result.completed_nodes for result in results) / total_runs
        if total_runs
        else 0.0,
        average_fights_won=sum(result.fights_won for result in results) / total_runs
        if total_runs
        else 0.0,
        average_gold=sum(result.gold for result in results) / total_runs if total_runs else 0.0,
        results=results,
    )


def simulate_one_run(
    *,
    index: int,
    seed: int,
    config: SimConfig,
    catalog: ContentCatalog,
) -> SimulatedRun:
    rng = Random(seed)
    character_ids = sorted(catalog.character_classes)
    character_id = rng.choice(character_ids)

    run_state = create_run_state(
        character_id,
        catalog=catalog,
        rng=rng,
    )

    ensure_gold_field(run_state)
    initialize_run_diagnostics(run_state)

    try:
        while not run_state.is_complete() and not run_state.is_defeated():
            available_nodes = run_state.available_map_nodes()

            if not available_nodes:
                return make_result(
                    index=index,
                    seed=seed,
                    run_state=run_state,
                    outcome="stalled",
                )

            node = rng.choice(available_nodes)
            enter_map_node(run_state, node.id)
            resolve_random_map_node(run_state, node, rng, config)

        outcome = "win" if run_state.is_complete() else "defeat"

        return make_result(
            index=index,
            seed=seed,
            run_state=run_state,
            outcome=outcome,
        )

    except Exception as error:
        return make_result(
            index=index,
            seed=seed,
            run_state=run_state,
            outcome="error",
            error=f"{type(error).__name__}: {error}",
            traceback_text=traceback.format_exc(),
        )


def make_result(
    *,
    index: int,
    seed: int,
    run_state: RunState,
    outcome: str,
    error: str | None = None,
    traceback_text: str | None = None,
) -> SimulatedRun:
    return SimulatedRun(
        index=index,
        seed=seed,
        character_id=run_state.character_class.id,
        outcome=outcome,
        completed_nodes=len(run_state.completed_node_ids),
        fights_won=max(0, run_state.fight_number - 1),
        gold=getattr(run_state, "gold", 0),
        deck_size=len(run_state.run_deck),
        relic_count=len(run_state.relics),
        error=error,
        traceback=traceback_text,
        last_node_id=getattr(run_state, "sim_last_node_id", None),
        last_node_type=getattr(run_state, "sim_last_node_type", None),
        last_node_depth=getattr(run_state, "sim_last_node_depth", None),
        last_encounter_id=getattr(run_state, "sim_last_encounter_id", None),
        last_encounter_name=getattr(run_state, "sim_last_encounter_name", None),
        last_enemy_ids=list(getattr(run_state, "sim_last_enemy_ids", [])),
        last_enemy_names=list(getattr(run_state, "sim_last_enemy_names", [])),
        last_enemy_hp=dict(getattr(run_state, "sim_last_enemy_hp", {})),
        last_player_hp=getattr(run_state, "sim_last_player_hp", None),
        last_player_hp_before_node=getattr(run_state, "sim_last_player_hp_before_node", None),
        last_player_hp_after_node=getattr(run_state, "sim_last_player_hp_after_node", None),
        last_combat_turns=getattr(run_state, "sim_last_combat_turns", None),
        path_history=list(getattr(run_state, "sim_path_history", [])),
    )


def resolve_random_map_node(
    run_state: RunState,
    node: MapNode,
    rng: Random,
    config: SimConfig,
) -> None:
    record_map_node(run_state, node)

    if node.node_type in {"combat", "elite", "boss"}:
        combat_state = create_combat_state_for_next_encounter(run_state)
        record_combat_start(run_state, combat_state)
        turns_played = simulate_combat(run_state, combat_state, rng, config)
        record_combat_end(run_state, combat_state, turns_played)

        if combat_state.is_victory():
            finish_victorious_combat(run_state, combat_state)

            if node.node_type == "boss":
                if has_next_act(run_state):
                    simulate_epic_card_reward(run_state, rng)
                    advance_to_next_act(run_state)
                return

            simulate_card_reward(run_state, rng, config)
        return

    if node.node_type == "event":
        simulate_event_node(run_state, node, rng, config)
        complete_current_map_node(run_state)
        return

    if node.node_type == "treasure":
        simulate_treasure_node(run_state, rng, config)
        if run_state.current_node_id not in run_state.completed_node_ids:
            complete_current_map_node(run_state)
        return

    if node.node_type == "waiting_room":
        heal_amount = ceil(
            run_state.character_class.max_hp
            * run_state.waiting_room_heal_percent
            / 100
        )
        run_state.current_hp = min(
            run_state.character_class.max_hp,
            run_state.current_hp + heal_amount,
        )
        complete_current_map_node(run_state)
        return

    raise ValueError(f"Unsupported map node type: {node.node_type}")


def simulate_combat(
    run_state: RunState,
    combat_state: CombatState,
    rng: Random,
    config: SimConfig,
) -> int:
    turns_played = 0

    while (
        not combat_state.is_victory()
        and not combat_state.is_defeat()
        and turns_played < config.max_combat_turns
    ):
        start_player_turn(combat_state, rng)
        simulate_player_turn(combat_state, rng, config)

        if combat_state.is_victory() or combat_state.is_defeat():
            break

        end_player_turn(combat_state)
        run_enemy_turn(combat_state)
        turns_played += 1

    run_state.current_hp = combat_state.player.hp

    return turns_played


def simulate_player_turn(
    combat_state: CombatState,
    rng: Random,
    config: SimConfig,
) -> None:
    while not combat_state.is_victory() and not combat_state.is_defeat():
        playable_cards = [
            card
            for card in combat_state.hand
            if card.cost <= combat_state.energy
        ]

        if not playable_cards:
            return

        if rng.random() < config.card_play_stop_chance:
            return

        card = rng.choice(playable_cards)
        target = choose_random_card_target(card, combat_state, rng)

        combat_state.energy -= card.cost
        combat_state.hand.remove(card)

        resolve_card(card, combat_state, target)

        combat_state.discard_pile.append(card)


def choose_random_card_target(
    card: Card,
    combat_state: CombatState,
    rng: Random,
) -> Combatant | None:
    living_enemies = combat_state.living_enemies()

    if not living_enemies:
        return None

    needs_enemy_target = any(
        effect.target in {"enemy", "first_enemy", "random_enemy"}
        for effect in card.effects
    )

    if needs_enemy_target:
        return rng.choice(living_enemies)

    return None



def simulate_epic_card_reward(
    run_state: RunState,
    rng: Random,
) -> None:
    try:
        rewards = choose_epic_card_rewards(
            run_state.card_database,
            rng,
            count=3,
            card_class=run_state.character_class.id,
        )
    except ValueError:
        return

    if rewards:
        run_state.run_deck.append(rng.choice(rewards))


def simulate_card_reward(
    run_state: RunState,
    rng: Random,
    config: SimConfig,
) -> None:
    if rng.random() < config.reward_skip_chance:
        return

    reward_count = 3 + card_reward_count_bonus(run_state.relics)

    try:
        rewards = choose_card_rewards(
            run_state.card_database,
            rng,
            count=reward_count,
            card_class=run_state.character_class.id,
        )
    except ValueError:
        return

    if not rewards:
        return

    if rng.random() < config.reward_skip_chance:
        return

    run_state.run_deck.append(rng.choice(rewards))


def simulate_event_node(
    run_state: RunState,
    node: MapNode,
    rng: Random,
    config: SimConfig,
) -> None:
    event = choose_random_event(run_state, node, rng)
    choice = rng.choice(event.choices)

    for effect in choice.effects:
        if effect.type == "none":
            continue

        if effect.type == "gain_card_reward":
            amount = effect.amount or 1

            for _ in range(amount):
                simulate_card_reward(run_state, rng, config)

            continue

        if effect.type == "upgrade_card":
            amount = effect.amount or 1

            for _ in range(amount):
                simulate_random_card_upgrade(run_state, rng)

            continue

        if effect.type == "remove_card":
            amount = effect.amount or 1

            for _ in range(amount):
                simulate_random_card_removal(
                    run_state,
                    rng,
                    card_id=effect.card_id,
                    tag=effect.tag,
                    free=True,
                )

            continue

        if effect.type == "lose_percent_max_hp":
            percent = effect.amount or 0
            loss = ceil(run_state.character_class.max_hp * percent / 100)
            run_state.current_hp = max(1, run_state.current_hp - loss)
            continue

        if effect.type == "gain_max_hp":
            amount = effect.amount or 0

            try:
                run_state.character_class.max_hp += amount
            except Exception:
                pass

            run_state.current_hp += amount
            continue

        if effect.type == "open_shop":
            simulate_shop(run_state, rng, config)
            continue

        raise NotImplementedError(f"Event effect not supported in simulator: {effect.type}")


def choose_random_event(
    run_state: RunState,
    node: MapNode,
    rng: Random,
) -> EventDefinition:
    events = [
        event
        for event in run_state.event_database.values()
        if event.act == run_state.act
        and (node.event_type is None or event.event_type == node.event_type)
    ]

    if not events:
        events = [
            event
            for event in run_state.event_database.values()
            if event.act == run_state.act
        ]

    if not events:
        raise ValueError(f"No events available for act {run_state.act}.")

    weights = [event.weight for event in events]
    return rng.choices(events, weights=weights, k=1)[0]


def simulate_treasure_node(
    run_state: RunState,
    rng: Random,
    config: SimConfig,
) -> None:
    if rng.random() < run_state.mimic_chance:
        combat_state = create_combat_state_for_encounter_id(
            run_state,
            run_state.treasure_mimic_encounter_id,
        )
        record_combat_start(run_state, combat_state)

        turns_played = simulate_combat(run_state, combat_state, rng, config)
        record_combat_end(run_state, combat_state, turns_played)

        if combat_state.is_victory():
            finish_victorious_combat(run_state, combat_state)
            simulate_card_reward(run_state, rng, config)

        return

    grant_random_unowned_relic(run_state, rng)


def create_combat_state_for_encounter_id(
    run_state: RunState,
    encounter_id: str,
) -> CombatState:
    encounter = run_state.encounter_database[encounter_id]
    enemies = create_enemies_for_encounter(
        encounter_id,
        run_state.encounter_database,
        run_state.enemy_database,
    )
    player = Combatant(
        id=run_state.character_class.id,
        name=run_state.character_class.name,
        max_hp=run_state.character_class.max_hp,
        hp=run_state.current_hp,
    )
    combat_state = CombatState(
        player=player,
        enemies=enemies,
        max_energy=run_state.character_class.starting_energy,
        energy=run_state.character_class.starting_energy,
        draw_pile=list(run_state.run_deck),
        status_database=run_state.status_database,
        card_database=run_state.card_database,
    )
    combat_state.encounter_id = encounter.id
    combat_state.encounter_name = encounter.name
    combat_state.log.append(f"Encounter chosen: {encounter.name}.")
    apply_combat_start_relics(combat_state, run_state.relics)
    shuffle_draw_pile(combat_state, run_state.rng)

    return combat_state


def grant_random_unowned_relic(
    run_state: RunState,
    rng: Random,
) -> None:
    owned_ids = {relic.id for relic in run_state.relics}
    available_relics = [
        relic
        for relic in run_state.relic_database.values()
        if relic.id not in owned_ids
    ]

    if not available_relics:
        return

    relic = rng.choice(available_relics)
    run_state.relics.append(relic)
    apply_relic_pickup_effects_to_run_state(run_state, relic)


def simulate_random_card_upgrade(
    run_state: RunState,
    rng: Random,
) -> bool:
    upgradeable_indices = [
        index
        for index, card in enumerate(run_state.run_deck)
        if card.upgrades_to is not None
        and card.upgrades_to in run_state.card_database
    ]

    if not upgradeable_indices:
        return False

    deck_index = rng.choice(upgradeable_indices)
    upgrade_id = run_state.run_deck[deck_index].upgrades_to

    if upgrade_id is None:
        return False

    run_state.run_deck[deck_index] = run_state.card_database[upgrade_id]
    return True


def simulate_random_card_removal(
    run_state: RunState,
    rng: Random,
    *,
    card_id: str | None = None,
    tag: str | None = None,
    free: bool = False,
    price: int = 0,
) -> bool:
    if not free and getattr(run_state, "gold", 0) < price:
        return False

    indices = removable_card_indices(
        run_state.run_deck,
        card_id=card_id,
        tag=tag,
    )

    if not indices:
        return False

    deck_index = rng.choice(indices)
    remove_card_from_deck(run_state.run_deck, deck_index)

    if not free:
        run_state.gold -= price

    return True


def simulate_shop(
    run_state: RunState,
    rng: Random,
    config: SimConfig,
) -> None:
    discount_percent = shop_price_discount_percent(run_state.relics)

    card_offers = choose_shop_card_offers(
        run_state.card_database,
        rng,
        card_class=run_state.character_class.id,
        act=run_state.act,
        fight_number=run_state.fight_number,
        count=DEFAULT_SHOP_CARD_OFFER_COUNT,
    )
    relic_offers = choose_shop_relic_offers(
        run_state.relic_database,
        run_state.relics,
        rng,
        act=run_state.act,
        fight_number=run_state.fight_number,
        count=DEFAULT_SHOP_RELIC_OFFER_COUNT,
    )

    card_prices = [
        discounted_shop_price(offer.price, discount_percent)
        for offer in card_offers
    ]
    relic_prices = [
        discounted_shop_price(offer.price, discount_percent)
        for offer in relic_offers
    ]

    bought_cards: set[int] = set()
    bought_relics: set[int] = set()
    removal_bought = False

    for _ in range(config.shop_buy_attempt_limit):
        if rng.random() < config.shop_leave_chance:
            return

        options: list[tuple[str, int | None]] = []

        for index, price in enumerate(card_prices):
            if index not in bought_cards and run_state.gold >= price:
                options.append(("card", index))

        for index, price in enumerate(relic_prices):
            if index not in bought_relics and run_state.gold >= price:
                options.append(("relic", index))

        removal_price = discounted_shop_price(
            card_removal_price(
                act=run_state.act,
                fight_number=run_state.fight_number,
            ),
            discount_percent,
        )

        if not removal_bought and run_state.gold >= removal_price:
            options.append(("remove", None))

        if not options:
            return

        option_type, option_index = rng.choice(options)

        if option_type == "card" and option_index is not None:
            offer = card_offers[option_index]
            price = card_prices[option_index]
            run_state.gold -= price
            run_state.run_deck.append(offer.card)
            bought_cards.add(option_index)
            continue

        if option_type == "relic" and option_index is not None:
            offer = relic_offers[option_index]
            price = relic_prices[option_index]
            run_state.gold -= price
            run_state.relics.append(offer.relic)
            apply_relic_pickup_effects_to_run_state(run_state, offer.relic)
            bought_relics.add(option_index)
            continue

        if option_type == "remove":
            removed = simulate_random_card_removal(
                run_state,
                rng,
                free=False,
                price=removal_price,
            )
            removal_bought = removal_bought or removed


def ensure_gold_field(run_state: RunState) -> None:
    if not hasattr(run_state, "gold"):
        run_state.gold = 0


def format_summary(summary: SimulationSummary, *, show_errors: int = 5) -> str:
    lines = [
        "=== Simulation Summary ===",
        f"Runs: {summary.total_runs}",
        f"Wins: {summary.wins} ({summary.win_rate:.1%})",
        f"Defeats: {summary.defeats} ({summary.defeat_rate:.1%})",
        f"Errors: {summary.errors} ({summary.error_rate:.1%})",
        f"Stalled: {summary.stalled}",
        f"Average completed nodes: {summary.average_completed_nodes:.2f}",
        f"Average fights won: {summary.average_fights_won:.2f}",
        f"Average final gold: {summary.average_gold:.2f}",
        "",
        "=== By Character ===",
    ]

    character_ids = sorted({result.character_id for result in summary.results})

    for character_id in character_ids:
        character_results = [
            result
            for result in summary.results
            if result.character_id == character_id
        ]
        wins = sum(result.outcome == "win" for result in character_results)
        defeats = sum(result.outcome == "defeat" for result in character_results)
        errors = sum(result.outcome == "error" for result in character_results)
        total = len(character_results)

        lines.append(
            f"{character_id}: runs={total}, wins={wins}, defeats={defeats}, "
            f"errors={errors}, win_rate={wins / total if total else 0:.1%}"
        )

    defeat_results = [
        result
        for result in summary.results
        if result.outcome == "defeat"
    ]

    if defeat_results:
        lines.extend(["", "=== Defeats by Last Encounter ==="])

        encounter_counter: Counter[str] = Counter()

        for result in defeat_results:
            encounter_name = result.last_encounter_name or result.last_encounter_id or "unknown"
            encounter_counter[encounter_name] += 1

        for encounter_name, count in encounter_counter.most_common(15):
            lines.append(f"{encounter_name}: {count}")

        lines.extend(["", "=== Defeats by Last Enemy Group ==="])

        group_counter: Counter[str] = Counter()

        for result in defeat_results:
            enemy_names = result.last_enemy_names or result.last_enemy_ids or ["unknown"]
            group_name = " + ".join(enemy_names)
            group_counter[group_name] += 1

        for group_name, count in group_counter.most_common(15):
            lines.append(f"{group_name}: {count}")

        lines.extend(["", "=== Defeats by Last Node Type ==="])

        node_type_counter: Counter[str] = Counter(
            result.last_node_type or "unknown"
            for result in defeat_results
        )

        for node_type, count in node_type_counter.most_common():
            lines.append(f"{node_type}: {count}")

        lines.extend(["", "=== Average HP Before Defeating Node Type ==="])

        for node_type, count in node_type_counter.most_common():
            node_results = [
                result
                for result in defeat_results
                if (result.last_node_type or "unknown") == node_type
                and result.last_player_hp_before_node is not None
            ]

            if not node_results:
                continue

            average_hp_before = sum(
                result.last_player_hp_before_node or 0
                for result in node_results
            ) / len(node_results)

            lines.append(f"{node_type}: {average_hp_before:.1f} HP before node")

    error_results = [
        result
        for result in summary.results
        if result.error is not None
    ][:show_errors]

    if error_results:
        lines.extend(["", "=== First Errors ==="])

        for result in error_results:
            lines.append(
                f"Run {result.index} seed={result.seed} "
                f"character={result.character_id}: {result.error}"
            )

    return "\n".join(lines)


def initialize_run_diagnostics(run_state: RunState) -> None:
    run_state.sim_last_node_id = None
    run_state.sim_last_node_type = None
    run_state.sim_last_node_depth = None
    run_state.sim_last_encounter_id = None
    run_state.sim_last_encounter_name = None
    run_state.sim_last_enemy_ids = []
    run_state.sim_last_enemy_names = []
    run_state.sim_last_enemy_hp = {}
    run_state.sim_last_player_hp = run_state.current_hp
    run_state.sim_last_player_hp_before_node = run_state.current_hp
    run_state.sim_last_player_hp_after_node = run_state.current_hp
    run_state.sim_last_combat_turns = None
    run_state.sim_path_history = []


def record_map_node(
    run_state: RunState,
    node: MapNode,
) -> None:
    run_state.sim_last_node_id = node.id
    run_state.sim_last_node_type = node.node_type
    run_state.sim_last_node_depth = node.depth
    run_state.sim_last_player_hp_before_node = run_state.current_hp
    run_state.sim_last_player_hp_after_node = run_state.current_hp

    run_state.sim_path_history.append(
        {
            "node_id": node.id,
            "node_type": node.node_type,
            "depth": node.depth,
            "hp_before": run_state.current_hp,
            "gold_before": getattr(run_state, "gold", 0),
            "deck_size_before": len(run_state.run_deck),
            "relic_count_before": len(run_state.relics),
        }
    )


def record_combat_start(
    run_state: RunState,
    combat_state: CombatState,
) -> None:
    run_state.sim_last_encounter_id = getattr(combat_state, "encounter_id", None)
    run_state.sim_last_encounter_name = getattr(combat_state, "encounter_name", None)
    run_state.sim_last_enemy_ids = [
        enemy.id
        for enemy in combat_state.enemies
    ]
    run_state.sim_last_enemy_names = [
        enemy.name
        for enemy in combat_state.enemies
    ]
    run_state.sim_last_enemy_hp = {
        enemy.name: enemy.hp
        for enemy in combat_state.enemies
    }
    run_state.sim_last_player_hp = combat_state.player.hp
    run_state.sim_last_player_hp_before_node = combat_state.player.hp
    run_state.sim_last_combat_turns = 0

    if run_state.sim_path_history:
        run_state.sim_path_history[-1]["encounter_id"] = run_state.sim_last_encounter_id
        run_state.sim_path_history[-1]["encounter_name"] = run_state.sim_last_encounter_name
        run_state.sim_path_history[-1]["enemy_names"] = list(run_state.sim_last_enemy_names)


def record_combat_end(
    run_state: RunState,
    combat_state: CombatState,
    turns_played: int,
) -> None:
    run_state.sim_last_enemy_hp = {
        enemy.name: enemy.hp
        for enemy in combat_state.enemies
    }
    run_state.sim_last_player_hp = combat_state.player.hp
    run_state.sim_last_player_hp_after_node = combat_state.player.hp
    run_state.sim_last_combat_turns = turns_played

    if run_state.sim_path_history:
        run_state.sim_path_history[-1]["hp_after"] = combat_state.player.hp
        run_state.sim_path_history[-1]["turns"] = turns_played
        run_state.sim_path_history[-1]["enemy_hp_after"] = dict(run_state.sim_last_enemy_hp)
