from random import Random

from bab.models import EventDefinition, EventType


def choose_random_event(
    event_database: dict[str, EventDefinition],
    rng: Random,
    *,
    act: int | None = None,
    event_type: EventType | None = None,
    excluded_event_ids: set[str] | None = None,
) -> EventDefinition:
    events = list(event_database.values())

    if act is not None:
        events = [
            event
            for event in events
            if event.act == act
        ]

    if event_type is not None:
        events = [
            event
            for event in events
            if event.event_type == event_type
        ]

    if not events:
        raise ValueError("No events available for the requested filters.")

    weights = [event.weight for event in events]
    return rng.choices(events, weights=weights, k=1)[0]