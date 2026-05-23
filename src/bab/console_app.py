from math import ceil
from random import Random
from bab.console_io import console
from bab.console_views import (
    format_enemy_intent,
    format_map_node,
    print_available_map_nodes,
    print_card_rewards,
    print_combat_state,
    print_event,
    print_full_log,
    print_hand,
    print_piles,
    print_recent_log,
    print_run_state,
)

from rich.panel import Panel
from rich.table import Table

from bab.combat_state import CombatState, Combatant
from bab.data_loader import (
    load_card_database,
    load_character_class,
    load_encounter_database,
    load_enemy_database,
    load_event_database,
    load_status_database,
    load_relic_database,
)
from bab.deck import play_card_from_hand, shuffle_draw_pile
from bab.events import choose_random_event
from bab.models import Card, EventChoice, EventDefinition, EventEffect
from bab.rewards import add_card_reward_to_deck, choose_card_rewards
from bab.run_map import MapNode
from bab.run_state import (
    RunState,
    complete_current_map_node,
    create_combat_state_for_next_encounter,
    create_new_run,
    enter_map_node,
    finish_victorious_combat,
)
from bab.upgrades import upgrade_card_in_deck, upgradeable_card_indices
from bab.encounters import choose_random_encounter
from bab.enemies import create_enemies_for_encounter
from bab.relics import (
    apply_combat_start_relics,
    apply_relic_pickup_effects,
    card_reward_count_bonus,
    choose_random_unowned_relic,
)

from bab.game_config import (
    CARD_DATA_FILES,
    CHARACTER_CLASS_DATA_FILE,
    DEFAULT_ACT,
    DEFAULT_MAP_STEPS_BEFORE_BOSS,
    DEFAULT_MAP_WIDTH,
    DEFAULT_MAX_FIGHTS,
    ENCOUNTER_DATA_FILES,
    ENEMY_DATA_FILES,
    EVENT_DATA_FILES,
    MIMIC_CHANCE,
    RELIC_DATA_FILES,
    STATUS_DATA_FILES,
    TREASURE_MIMIC_ENCOUNTER_ID,
    WAITING_ROOM_HEAL_PERCENT,
)


def choose_next_map_node(run_state: RunState) -> MapNode:
    available_nodes = run_state.available_map_nodes()

    while True:
        print_available_map_nodes(run_state)

        command = console.input(
            "[bold yellow]Choose a map node number or 'quit': [/bold yellow]"
        ).strip().lower()

        if command == "quit":
            raise SystemExit("Game quit.")

        if not command.isdigit():
            console.print("[red]Invalid map choice.[/red]")
            continue

        node_index = int(command)

        if node_index < 0 or node_index >= len(available_nodes):
            console.print("[red]Invalid map node number.[/red]")
            continue

        selected_node = available_nodes[node_index]
        enter_map_node(run_state, selected_node.id)
        return selected_node


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

        intent_text = format_enemy_intent(enemy)

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
    reward_count = 3 + card_reward_count_bonus(run_state.relics)
    rewards = choose_card_rewards(
        run_state.card_database,
        run_state.rng,
        count=reward_count,
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


def offer_card_upgrade(run_state: RunState) -> None:
    upgradeable_indices = upgradeable_card_indices(run_state.run_deck)

    if not upgradeable_indices:
        console.print("[yellow]There are no cards that can be upgraded.[/yellow]")
        return

    table = Table(title="Upgradeable Cards")
    table.add_column("#", justify="right")
    table.add_column("Current Card", style="cyan")
    table.add_column("Upgrade")
    table.add_column("Current Text")
    table.add_column("Upgraded Text")

    visible_options: list[int] = []

    for visible_index, deck_index in enumerate(upgradeable_indices):
        card = run_state.run_deck[deck_index]

        if card.upgrades_to is None:
            continue

        upgraded_card = run_state.card_database[card.upgrades_to]
        visible_options.append(deck_index)

        table.add_row(
            str(visible_index),
            card.name,
            upgraded_card.name,
            card.text,
            upgraded_card.text,
        )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose a card to upgrade or 'skip': [/bold yellow]"
        ).strip().lower()

        if command == "skip":
            console.print("[yellow]No card upgraded.[/yellow]")
            return

        if not command.isdigit():
            console.print("[red]Invalid upgrade choice.[/red]")
            continue

        visible_index = int(command)

        if visible_index < 0 or visible_index >= len(visible_options):
            console.print("[red]Invalid upgrade number.[/red]")
            continue

        deck_index = visible_options[visible_index]
        old_card = run_state.run_deck[deck_index]
        upgraded_card = upgrade_card_in_deck(
            run_state.run_deck,
            run_state.card_database,
            deck_index,
        )

        console.print(
            f"[green]Upgraded {old_card.name} into {upgraded_card.name}.[/green]"
        )
        return


def create_run_state() -> RunState:
    rng = Random()

    card_database = load_card_database(CARD_DATA_FILES)
    character_class = load_character_class(CHARACTER_CLASS_DATA_FILE)
    enemy_database = load_enemy_database(ENEMY_DATA_FILES)
    encounter_database = load_encounter_database(ENCOUNTER_DATA_FILES)
    status_database = load_status_database(STATUS_DATA_FILES)
    event_database = load_event_database(EVENT_DATA_FILES)
    relic_database = load_relic_database(RELIC_DATA_FILES)

    return create_new_run(
        character_class=character_class,
        card_database=card_database,
        enemy_database=enemy_database,
        encounter_database=encounter_database,
        status_database=status_database,
        event_database=event_database,
        relic_database=relic_database,
        rng=rng,
        act=DEFAULT_ACT,
        max_fights=DEFAULT_MAX_FIGHTS,
        map_steps_before_boss=DEFAULT_MAP_STEPS_BEFORE_BOSS,
        map_width=DEFAULT_MAP_WIDTH,
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

    state = create_combat_state_for_next_encounter(run_state)

    while not state.is_victory() and not state.is_defeat():
        start_player_turn(state, run_state.rng)
        player_action_loop(state)

        if state.is_victory() or state.is_defeat():
            break

        run_enemy_turn(state)

    return state


def choose_event_choice(event: EventDefinition) -> EventChoice:
    while True:
        command = console.input(
            "[bold yellow]Choose an event option number: [/bold yellow]"
        ).strip().lower()

        if not command.isdigit():
            console.print("[red]Invalid event choice.[/red]")
            continue

        choice_index = int(command)

        if choice_index < 0 or choice_index >= len(event.choices):
            console.print("[red]Invalid event choice number.[/red]")
            continue

        return event.choices[choice_index]


def apply_event_effect(run_state: RunState, effect: EventEffect) -> None:
    if effect.type == "none":
        return

    if effect.type == "gain_card_reward":
        amount = effect.amount or 1
        for _ in range(amount):
            offer_card_reward(run_state)
        return

    if effect.type == "upgrade_card":
        amount = effect.amount or 1
        for _ in range(amount):
            offer_card_upgrade(run_state)
        return

    if effect.type == "lose_percent_max_hp":
        percent = effect.amount or 0
        loss = ceil(run_state.character_class.max_hp * percent / 100)
        run_state.current_hp = max(1, run_state.current_hp - loss)
        console.print(
            f"[red]Lost {loss} HP. Current HP: "
            f"{run_state.current_hp}/{run_state.character_class.max_hp}.[/red]"
        )
        return

    if effect.type == "gain_max_hp":
        console.print("[yellow]Max HP events are not implemented yet.[/yellow]")
        return

    if effect.type == "remove_card":
        console.print("[yellow]Card removal is not implemented yet.[/yellow]")
        return

    console.print(f"[yellow]Unhandled event effect: {effect.type}.[/yellow]")


def resolve_event_node(run_state: RunState, node: MapNode) -> None:
    if node.event_type is None:
        raise ValueError("Event node is missing an event type.")

    event = choose_random_event(
        run_state.event_database,
        run_state.rng,
        act=run_state.act,
        event_type=node.event_type,
    )

    print_event(event)
    choice = choose_event_choice(event)

    console.print()
    console.print(Panel(choice.result_text, title="Event Result"))

    for effect in choice.effects:
        apply_event_effect(run_state, effect)

    complete_current_map_node(run_state)


def resolve_waiting_room_node(run_state: RunState) -> None:
    console.print()
    console.print(
        Panel(
            "The Waiting Room smells faintly of dust, old coffee, and postponed decisions.",
            title="Waiting Room",
        )
    )

    table = Table(title="Waiting Room Choices")
    table.add_column("#", justify="right")
    table.add_column("Choice")
    table.add_column("Effect")

    table.add_row(
        "0",
        "Do something productive.",
        "Upgrade one card.",
    )
    table.add_row(
        "1",
        "Take a Nap.",
        f"Heal {WAITING_ROOM_HEAL_PERCENT}% of max HP.",
    )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose a Waiting Room option: [/bold yellow]"
        ).strip().lower()

        if command == "0":
            offer_card_upgrade(run_state)
            break

        if command == "1":
            heal_amount = ceil(
                run_state.character_class.max_hp
                * WAITING_ROOM_HEAL_PERCENT
                / 100
            )
            old_hp = run_state.current_hp
            run_state.current_hp = min(
                run_state.character_class.max_hp,
                run_state.current_hp + heal_amount,
            )
            healed = run_state.current_hp - old_hp
            console.print(
                f"[green]You take a nap and recover {healed} HP. "
                f"Current HP: {run_state.current_hp}/"
                f"{run_state.character_class.max_hp}.[/green]"
            )
            break

        console.print("[red]Invalid Waiting Room choice.[/red]")

    complete_current_map_node(run_state)


def resolve_combat_node(run_state: RunState, node: MapNode) -> None:
    state = run_single_combat(run_state)

    console.print()
    print_combat_state(state)
    print_full_log(state)

    if state.is_defeat():
        run_state.current_hp = 0
        console.print("[bold red]Defeat. The bureaucracy was insufficient.[/bold red]")
        return

    finish_victorious_combat(run_state, state)

    if node.node_type == "boss":
        console.print("[bold green]Boss defeated! The act is complete.[/bold green]")
        return

    console.print("[bold green]Victory! The paperwork has prevailed.[/bold green]")
    offer_card_reward(run_state)


def resolve_map_node(run_state: RunState, node: MapNode) -> None:
    console.print()
    console.print(Panel(format_map_node(node), title="Entering Map Node"))

    if node.node_type in {"combat", "elite", "boss"}:
        resolve_combat_node(run_state, node)
        return

    if node.node_type == "event":
        resolve_event_node(run_state, node)
        return

    if node.node_type == "waiting_room":
        resolve_waiting_room_node(run_state)
        return
    
    if node.node_type == "treasure":
        resolve_treasure_node(run_state)
        return

    raise ValueError(f"Unsupported map node type: {node.node_type}")

def grant_random_relic(run_state: RunState) -> None:
    try:
        relic = choose_random_unowned_relic(
            run_state.relic_database,
            run_state.relics,
            run_state.rng,
        )
    except ValueError:
        console.print("[yellow]No unowned relics remain.[/yellow]")
        return

    run_state.relics.append(relic)

    console.print(f"[green]Found relic: {relic.name}.[/green]")
    console.print(f"[cyan]{relic.description}[/cyan]")

    new_hp, messages = apply_relic_pickup_effects(
        current_hp=run_state.current_hp,
        max_hp=run_state.character_class.max_hp,
        relic=relic,
    )
    run_state.current_hp = new_hp

    for message in messages:
        console.print(f"[green]{message}[/green]")

def create_treasure_mimic_combat_state(run_state: RunState) -> CombatState:
    mimic_encounter_id = TREASURE_MIMIC_ENCOUNTER_ID

    if mimic_encounter_id in run_state.encounter_database:
        encounter = run_state.encounter_database[mimic_encounter_id]
    else:
        encounter = choose_random_encounter(
            run_state.encounter_database,
            run_state.rng,
            act=run_state.act,
            difficulty="elite",
        )

    enemies = create_enemies_for_encounter(
        encounter.id,
        run_state.encounter_database,
        run_state.enemy_database,
    )

    player = Combatant(
        id=run_state.character_class.id,
        name=run_state.character_class.name,
        max_hp=run_state.character_class.max_hp,
        hp=run_state.current_hp,
    )

    state = CombatState(
        player=player,
        enemies=enemies,
        max_energy=run_state.character_class.starting_energy,
        energy=run_state.character_class.starting_energy,
        draw_pile=list(run_state.run_deck),
        status_database=run_state.status_database,
    )
    state.log.append(f"Treasure chest was a Mimic: {encounter.name}.")
    apply_combat_start_relics(state, run_state.relics)
    shuffle_draw_pile(state, run_state.rng)

    return state


def run_treasure_mimic_combat(run_state: RunState) -> CombatState:
    from bab.turns import run_enemy_turn, start_player_turn

    state = create_treasure_mimic_combat_state(run_state)

    while not state.is_victory() and not state.is_defeat():
        start_player_turn(state, run_state.rng)
        player_action_loop(state)

        if state.is_victory() or state.is_defeat():
            break

        run_enemy_turn(state)

    return state


def resolve_treasure_node(run_state: RunState) -> None:
    console.print()
    console.print(
        Panel(
            "A heavy chest sits in the corridor. It looks valuable, smug, and possibly employed.",
            title="Treasure Chest",
        )
    )

    if run_state.rng.random() < MIMIC_CHANCE:
        console.print("[bold red]The chest was a Mimic![/bold red]")

        state = run_treasure_mimic_combat(run_state)

        console.print()
        print_combat_state(state)
        print_full_log(state)

        if state.is_defeat():
            run_state.current_hp = 0
            console.print("[bold red]Defeat. The chest has filed you under snacks.[/bold red]")
            return

        finish_victorious_combat(run_state, state)
        console.print("[bold green]The Mimic is defeated.[/bold green]")
        grant_random_relic(run_state)
        return

    grant_random_relic(run_state)
    complete_current_map_node(run_state)

def run_console_app() -> None:
    console.print("[bold green]Bureaucrats and Broomsticks[/bold green]")
    console.print("Interactive map prototype started.\n")

    run_state = create_run_state()

    while not run_state.is_complete() and not run_state.is_defeated():
        console.print()
        print_run_state(run_state)

        node = choose_next_map_node(run_state)
        resolve_map_node(run_state, node)

    console.print()
    print_run_state(run_state)

    if run_state.is_complete():
        console.print("[bold green]Run complete! The office survives another day.[/bold green]")
    elif run_state.is_defeated():
        console.print("[bold red]Run failed. The paperwork remains unfinished.[/bold red]")


if __name__ == "__main__":
    run_console_app()
