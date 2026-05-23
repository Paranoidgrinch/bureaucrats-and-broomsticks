from rich.table import Table

import bab.console.waiting_room_flow as waiting_room_flow


def test_waiting_room_flow_imports_table() -> None:
    assert waiting_room_flow.Table is Table
