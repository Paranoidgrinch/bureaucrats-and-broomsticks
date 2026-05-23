from bab.console_app import run_console_app as console_entry
from bab.run_flow import create_run_state, run_console_app as run_flow_entry


def test_console_app_exposes_run_flow_entry_point() -> None:
    assert console_entry is run_flow_entry


def test_create_run_state_builds_playable_run() -> None:
    run_state = create_run_state()

    assert run_state.current_hp > 0
    assert run_state.run_deck
    assert run_state.card_database
    assert run_state.enemy_database
    assert run_state.encounter_database
    assert run_state.status_database
    assert run_state.event_database
    assert run_state.relic_database
    assert run_state.available_map_nodes()
