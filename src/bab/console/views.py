from rich.panel import Panel
from rich.table import Table

from bab.combat_state import CombatState, Combatant
from bab.console.io import console
from bab.models import Card, EventDefinition
from bab.run_map import MapNode
from bab.run_state import RunState


def format_map_node(node: MapNode) -> str:
    node_type = node.node_type.replace("_", " ").title()

    if node.encounter_difficulty is not None:
        return f"{node_type} ({node.encounter_difficulty.title()})"

    if node.event_type is not None:
        return f"{node_type} ({node.event_type.replace('_', ' ').title()})"

    return node_type


def format_enemy_intent(combatant: Combatant) -> str:
    intent = combatant.current_intent()

    if intent is None:
        return "intends to attack for 6 damage"

    if intent.intent_type == "attack":
        if intent.damage is None:
            return "intends to attack"

        strength = combatant.get_status_amount("strength")
        shown_damage = intent.damage + strength
        return f"intends to attack for {shown_damage} damage"

    if intent.intent_type == "buff":
        strength_amount = next(
            (
                effect.amount
                for effect in intent.effects
                if effect.type == "gain_strength"
            ),
            None,
        )

        if strength_amount is not None:
            return f"intends to buff itself (+{strength_amount} Strength)"

        return "intends to buff itself"

    if intent.intent_type == "debuff":
        return "intends to apply a debuff"

    if intent.intent_type == "block":
        return "intends to defend"

    return "intends to do something suspicious"


def print_run_state(run_state: RunState) -> None:
    current_node = run_state.current_node()
    if current_node is None:
        current_node_text = "No node selected."
    else:
        current_node_text = format_map_node(current_node)

    relic_text = ", ".join(relic.name for relic in run_state.relics)
    if not relic_text:
        relic_text = "-"

    text = (
        f"Act: {run_state.act}\n"
        f"Fights won: {run_state.fight_number - 1}\n"
        f"HP: {run_state.current_hp}/{run_state.character_class.max_hp}\n"
        f"Deck size: {len(run_state.run_deck)}\n"
        f"Relics: {relic_text}\n"
        f"Current node: {current_node_text}\n"
        f"Completed nodes: {len(run_state.completed_node_ids)}"
    )
    console.print(Panel(text, title="Run State"))


def print_available_map_nodes(run_state: RunState) -> None:
    available_nodes = run_state.available_map_nodes()

    table = Table(title="Available Map Nodes")
    table.add_column("#", justify="right")
    table.add_column("Node")
    table.add_column("Depth", justify="right")
    table.add_column("ID")

    for index, node in enumerate(available_nodes):
        table.add_row(
            str(index),
            format_map_node(node),
            str(node.depth),
            node.id,
        )

    console.print(table)


def print_combat_state(state: CombatState) -> None:
    table = Table(title="Combat State")
    table.add_column("Side")
    table.add_column("Name")
    table.add_column("HP", justify="right")
    table.add_column("Block", justify="right")
    table.add_column("Statuses")
    table.add_column("Intent")

    combatants: list[tuple[str, Combatant]] = [("Player", state.player)]
    combatants.extend(
        (f"Enemy {index}", enemy)
        for index, enemy in enumerate(state.enemies)
    )

    for side, combatant in combatants:
        statuses = ", ".join(
            f"{state.status_name(status.id)}: {status.amount}"
            for status in combatant.statuses.values()
        )
        if not statuses:
            statuses = "-"

        intent_text = "-"
        if side.startswith("Enemy") and combatant.is_alive():
            intent_text = format_enemy_intent(combatant)

        table.add_row(
            side,
            combatant.name,
            f"{combatant.hp}/{combatant.max_hp}",
            str(combatant.block),
            statuses,
            intent_text,
        )

    console.print(table)


def print_hand(state: CombatState) -> None:
    table = Table(title="Hand")
    table.add_column("#", justify="right")
    table.add_column("Card", style="cyan")
    table.add_column("Cost", justify="right")
    table.add_column("Type")
    table.add_column("Text")

    for index, card in enumerate(state.hand):
        table.add_row(
            str(index),
            card.name,
            str(card.cost),
            card.type,
            card.text,
        )

    console.print(table)


def print_card_rewards(rewards: list[Card]) -> None:
    table = Table(title="Card Rewards")
    table.add_column("#", justify="right")
    table.add_column("Card", style="cyan")
    table.add_column("Rarity")
    table.add_column("Cost", justify="right")
    table.add_column("Type")
    table.add_column("Text")

    for index, card in enumerate(rewards):
        table.add_row(
            str(index),
            card.name,
            card.rarity,
            str(card.cost),
            card.type,
            card.text,
        )

    console.print(table)


def print_piles(state: CombatState) -> None:
    text = (
        f"Turn: {state.turn}\n"
        f"Energy: {state.energy}/{state.max_energy}\n"
        f"Draw pile: {len(state.draw_pile)}\n"
        f"Hand: {len(state.hand)}\n"
        f"Discard pile: {len(state.discard_pile)}\n"
        f"Exhaust pile: {len(state.exhaust_pile)}"
    )
    console.print(Panel(text, title="Piles"))


def print_recent_log(state: CombatState, lines: int = 10) -> None:
    recent_log = state.log[-lines:]
    log_text = "\n".join(recent_log)
    if not log_text:
        log_text = "No combat events yet."
    console.print(Panel(log_text, title="Recent Combat Log"))


def print_full_log(state: CombatState) -> None:
    log_text = "\n".join(state.log)
    if not log_text:
        log_text = "No combat events yet."
    console.print(Panel(log_text, title="Full Combat Log"))


def print_event(event: EventDefinition) -> None:
    console.print()
    console.print(Panel(event.text, title=event.name))

    table = Table(title="Event Choices")
    table.add_column("#", justify="right")
    table.add_column("Choice")
    table.add_column("Result Preview")

    for index, choice in enumerate(event.choices):
        table.add_row(
            str(index),
            choice.text,
            choice.result_text,
        )

    console.print(table)
