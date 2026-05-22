from random import Random

from bab.combat_state import CombatState
from bab.models import RelicDefinition


def choose_random_unowned_relic(
    relic_database: dict[str, RelicDefinition],
    owned_relics: list[RelicDefinition],
    rng: Random,
) -> RelicDefinition:
    owned_ids = {relic.id for relic in owned_relics}

    available_relics = [
        relic
        for relic in relic_database.values()
        if relic.id not in owned_ids
    ]

    if not available_relics:
        raise ValueError("No unowned relics available.")

    return rng.choice(available_relics)


def apply_combat_start_relics(
    state: CombatState,
    relics: list[RelicDefinition],
) -> None:
    for relic in relics:
        for effect in relic.effects:
            if effect.type == "increase_max_energy":
                amount = require_amount(effect.amount, relic.name)
                state.max_energy += amount
                state.energy += amount
                state.log.append(
                    f"{relic.name} increases Max Energy by {amount}."
                )
                continue

            if effect.type == "gain_block_at_combat_start":
                amount = require_amount(effect.amount, relic.name)
                state.player.gain_block(amount)
                state.log.append(
                    f"{relic.name} grants {amount} Block."
                )
                continue

            if effect.type == "apply_status_to_all_enemies_at_combat_start":
                amount = require_amount(effect.amount, relic.name)

                if effect.status is None:
                    raise ValueError(
                        f"{relic.name} relic effect requires a status."
                    )

                for enemy in state.living_enemies():
                    enemy.apply_status(effect.status, amount)

                status_name = state.status_name(effect.status)
                state.log.append(
                    f"{relic.name} applies {amount} {status_name} to all enemies."
                )
                continue

            if effect.type in {
                "heal_on_pickup",
                "increase_card_reward_count",
            }:
                continue

            raise NotImplementedError(
                f"Relic effect not implemented: {effect.type}"
            )


def apply_relic_pickup_effects(
    *,
    current_hp: int,
    max_hp: int,
    relic: RelicDefinition,
) -> tuple[int, list[str]]:
    new_hp = current_hp
    messages: list[str] = []

    for effect in relic.effects:
        if effect.type != "heal_on_pickup":
            continue

        amount = require_amount(effect.amount, relic.name)
        old_hp = new_hp
        new_hp = min(max_hp, new_hp + amount)
        healed = new_hp - old_hp
        messages.append(f"{relic.name} restores {healed} HP.")

    return new_hp, messages


def card_reward_count_bonus(relics: list[RelicDefinition]) -> int:
    bonus = 0

    for relic in relics:
        for effect in relic.effects:
            if effect.type == "increase_card_reward_count":
                bonus += require_amount(effect.amount, relic.name)

    return bonus


def require_amount(amount: int | None, relic_name: str) -> int:
    if amount is None:
        raise ValueError(f"{relic_name} relic effect requires an amount.")

    return amount