from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.cwd()

EVENT_FILES = sorted((ROOT / "data/events").glob("*.json"))
ACT_FILES = sorted((ROOT / "data/acts").glob("*.json"))

EVENT_HANDLER_FILE = ROOT / "src/bab/console/event_effect_handlers.py"
EVENT_FLOW_FILE = ROOT / "src/bab/console/event_flow.py"
SHOP_FILE = ROOT / "src/bab/systems/shop.py"


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def print_file(path: Path, max_lines: int = 120) -> None:
    print(f"## {path}")
    if not path.exists():
        print("MISSING")
        print()
        return

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for index, line in enumerate(lines[:max_lines], start=1):
        print(f"{index:04d}: {line}")
    if len(lines) > max_lines:
        print(f"... truncated after {max_lines} lines; total lines={len(lines)}")
    print()


def main() -> None:
    print("# Event and Shop Audit")
    print()

    print("## Act manifests and event files")
    for act_file in ACT_FILES:
        act = load_json(act_file)
        print(f"{act_file.relative_to(ROOT)}")
        print(f"  id={act.get('id')}")
        print(f"  event_files={act.get('event_files')}")
        print()

    print("## Event files")
    for event_file in EVENT_FILES:
        events = load_json(event_file)
        print(f"{event_file.relative_to(ROOT)}: {len(events)} events")

        option_counts = []
        effect_types = Counter()
        reward_types = Counter()
        by_tag = Counter()

        for event in events:
            for tag in event.get("tags", []):
                by_tag[tag] += 1

            options = event.get("options", [])
            option_counts.append(len(options))

            for option in options:
                for effect in option.get("effects", []):
                    effect_types[effect.get("type", "<missing>")] += 1
                for reward in option.get("rewards", []):
                    reward_types[reward.get("type", "<missing>")] += 1

        print(f"  option_counts={dict(Counter(option_counts))}")
        print(f"  effect_types={dict(effect_types)}")
        print(f"  reward_types={dict(reward_types)}")
        print(f"  tags={dict(by_tag)}")
        print()

    print("## Current Act-2 event file sample")
    act2_event_file = ROOT / "data/events/act_2_archives_events.json"
    if act2_event_file.exists():
        events = load_json(act2_event_file)
        for event in events[:3]:
            print(json.dumps(event, indent=2))
            print()
    else:
        print("No data/events/act_2_archives_events.json found.")
        print()

    print("## Event handlers")
    print_file(EVENT_HANDLER_FILE, max_lines=240)

    print("## Event flow")
    print_file(EVENT_FLOW_FILE, max_lines=220)

    print("## Shop system")
    print_file(SHOP_FILE, max_lines=260)


if __name__ == "__main__":
    main()
