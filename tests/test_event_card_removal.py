from bab.console import event_effect_handlers
from bab.models import EventEffect


def test_remove_card_event_handler_calls_card_removal_once(monkeypatch) -> None:
    calls = []

    def fake_offer_card_removal(run_state, *, card_id=None, tag=None):
        calls.append((run_state, card_id, tag))

    monkeypatch.setattr(
        event_effect_handlers,
        "offer_card_removal",
        fake_offer_card_removal,
    )

    run_state = object()
    effect = EventEffect.model_validate(
        {
            "type": "remove_card",
            "amount": 1,
        }
    )

    event_effect_handlers.handle_remove_card(run_state, effect)

    assert calls == [(run_state, None, None)]


def test_remove_card_event_handler_respects_amount_and_filters(monkeypatch) -> None:
    calls = []

    def fake_offer_card_removal(run_state, *, card_id=None, tag=None):
        calls.append((run_state, card_id, tag))

    monkeypatch.setattr(
        event_effect_handlers,
        "offer_card_removal",
        fake_offer_card_removal,
    )

    run_state = object()
    effect = EventEffect.model_validate(
        {
            "type": "remove_card",
            "amount": 2,
            "card_id": "paper_cut",
            "tag": "starter",
        }
    )

    event_effect_handlers.handle_remove_card(run_state, effect)

    assert calls == [
        (run_state, "paper_cut", "starter"),
        (run_state, "paper_cut", "starter"),
    ]
