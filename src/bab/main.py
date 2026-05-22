from random import Random

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bab.combat_state import CombatState, Combatant
from bab.data_loader import (
    load_card_database,
    load_character_class,
    load_encounter_database,
    load_enemy_database,
    load_status_database,
)
from bab.deck import play_card_from_hand
from bab.rewards import add_card_reward_to_deck, choose_card_rewards
from bab.run_state import (
    RunState,
    create_combat_state_for_next_encounter,
    create_new_run,
    finish_victorious_combat,
)
from bab.models import Card

console = Console()


def print_run_state(run_state: RunState) -> None:
    text = (
        f"Act: {run_state.act}\n"
        f"Fight: {run_state.fight_number}/{run_state.max_fights}\n"
        f"HP: {run_state.current_hp}/{run_state.character_class.max_hp}\n"
        f"Deck size: {len(run_state.run_deck)}"
    )
    console.print(Panel(text, title="Run State"))


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
            intent = combatant.current_intent()
            if intent is not None:
                if intent.intent_type == "attack":
                    intent_text = f"{intent.name}: {intent.damage} damage"
                elif intent.intent_type == "block":
                    intent_text = f"{intent.name}: {intent.block} Block"
                else:
                    intent_text = intent.name

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


def choose_target(state: CombatState) -> Combatant | None:
    living_enemies = state.living_enemies()
    if not living_enemies:
        return None

    if len(living_enemies) == 1:
        return living_enemies[0]

    table = Table(title="Choose Target")
    table.add_column("#", justify="right")
    table.add_column("Enemy", style="red")
    table.add_column("HP", justify="right")
    table.add_column("Block", justify="right")
    table.add_column("Statuses")
    table.add_column("Intent")

    for index, enemy in enumerate(state.enemies):
        if not enemy.is_alive():
            continue

        statuses = ", ".join(
            f"{state.status_name(status.id)}: {status.amount}"
            for status in enemy.statuses.values()
        )
        if not statuses:
            statuses = "-"

        intent_text = "-"
        intent = enemy.current_intent()
        if intent is not None:
            if intent.intent_type == "attack":
                intent_text = f"{intent.name}: {intent.damage} damage"
            elif intent.intent_type == "block":
                intent_text = f"{intent.name}: {intent.block} Block"
            else:
                intent_text = intent.name

        table.add_row(
            str(index),
            enemy.name,
            f"{enemy.hp}/{enemy.max_hp}",
            str(enemy.block),
            statuses,
            intent_text,
        )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose target number or 'cancel': [/bold yellow]"
        ).strip().lower()

        if command == "cancel":
            return None

        if not command.isdigit():
            console.print("[red]Invalid target.[/red]")
            continue

        target_index = int(command)

        if target_index < 0 or target_index >= len(state.enemies):
            console.print("[red]Invalid target number.[/red]")
            continue

        target = state.enemies[target_index]
        if not target.is_alive():
            console.print("[red]That target is already defeated.[/red]")
            continue

        return target


def offer_card_reward(run_state: RunState) -> None:
    rewards = choose_card_rewards(
        run_state.card_database,
        run_state.rng,
        count=3,
    )

    console.print()
    print_card_rewards(rewards)

    while True:
        command = console.input(
            "[bold yellow]Choose a reward number or 'skip': [/bold yellow]"
        ).strip().lower()

        if command == "skip":
            console.print("[yellow]No reward chosen.[/yellow]")
            return

        if not command.isdigit():
            console.print("[red]Invalid reward choice.[/red]")
            continue

        reward_index = int(command)

        if reward_index < 0 or reward_index >= len(rewards):
            console.print("[red]Invalid reward number.[/red]")
            continue

        selected_reward = rewards[reward_index]
        add_card_reward_to_deck(run_state.run_deck, selected_reward)
        console.print(
            f"[green]Added {selected_reward.name} to deck. "
            f"Current deck size: {len(run_state.run_deck)}.[/green]"
        )
        return


def create_run_state() -> RunState:
    rng = Random()

    card_database = load_card_database(
        [
            "data/cards/bureaucrat_starter.json",
            "data/cards/bureaucrat_rewards.json",
        ]
    )
    character_class = load_character_class("data/classes/bureaucrat.json")
    enemy_database = load_enemy_database(
        [
            "data/enemies/city_enemies.json",
        ]
    )
    encounter_database = load_encounter_database(
        [
            "data/encounters/act_1_city.json",
        ]
    )
    status_database = load_status_database(
        [
            "data/statuses/statuses.json",
        ]
    )

    return create_new_run(
        character_class=character_class,
        card_database=card_database,
        enemy_database=enemy_database,
        encounter_database=encounter_database,
        status_database=status_database,
        rng=rng,
        act=1,
        max_fights=3,
    )


def player_action_loop(state: CombatState) -> None:
    while True:
        if state.is_victory() or state.is_defeat():
            return

        console.print()
        print_combat_state(state)
        print_hand(state)
        print_piles(state)
        print_recent_log(state, lines=5)

        command = console.input(
            "\n[bold yellow]Choose a card number, 'end', 'log', or 'quit': [/bold yellow]"
        ).strip().lower()

        if command == "end":
            from bab.turns import end_player_turn

            end_player_turn(state)
            return

        if command == "log":
            print_full_log(state)
            continue

        if command == "quit":
            raise SystemExit("Game quit.")

        if not command.isdigit():
            console.print("[red]Invalid command.[/red]")
            continue

        hand_index = int(command)

        if hand_index < 0 or hand_index >= len(state.hand):
            console.print("[red]Invalid card number.[/red]")
            continue

        selected_card = state.hand[hand_index]
        if selected_card.cost > state.energy:
            message = (
                f"Not enough Energy to play {selected_card.name}. "
                f"Needed {selected_card.cost}, had {state.energy}."
            )
            state.log.append(message)
            console.print(f"[red]{message}[/red]")
            continue

        target = choose_target(state)
        if target is None:
            console.print("[yellow]Card play cancelled.[/yellow]")
            continue

        play_card_from_hand(state, hand_index=hand_index, target=target)
        print_recent_log(state, lines=5)

        if state.is_victory():
            return


def run_single_combat(run_state: RunState) -> CombatState:
    from bab.turns import run_enemy_turn, start_player_turn

    state = create_combat_state_for_next_encounter(
        run_state,
        difficulty="normal",
    )

    while not state.is_victory() and not state.is_defeat():
        start_player_turn(state, run_state.rng)
        player_action_loop(state)

        if state.is_victory() or state.is_defeat():
            break

        run_enemy_turn(state)

    return state


def main() -> None:
    console.print("[bold green]Bureaucrats and Broomsticks[/bold green]")
    console.print("Interactive run prototype started.\n")

    run_state = create_run_state()

    while not run_state.is_complete() and not run_state.is_defeated():
        console.print()
        print_run_state(run_state)

        state = run_single_combat(run_state)

        console.print()
        print_combat_state(state)
        print_full_log(state)

        if state.is_defeat():
            run_state.current_hp = 0
            console.print("[bold red]Defeat. The bureaucracy was insufficient.[/bold red]")
            return

        finish_victorious_combat(run_state, state)
        console.print("[bold green]Victory! The paperwork has prevailed.[/bold green]")

        if not run_state.is_complete():
            offer_card_reward(run_state)

    console.print()
    print_run_state(run_state)
    console.print("[bold green]Run complete! The office survives another day.[/bold green]")


if __name__ == "__main__":
    main()