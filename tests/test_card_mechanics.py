from bab.combat.deck import play_card_from_hand
from bab.combat.state import CombatState, Combatant
from bab.models import Card, Effect


def make_card(card_id, *, cost=0, effects=None, tags=None, card_type="action"):
    return Card(
        id=card_id,
        name=card_id.replace("_", " ").title(),
        **{"class": "bureaucrat"},
        type=card_type,
        cost=cost,
        rarity="common",
        text="test",
        effects=effects or [],
        tags=tags or [],
    )


def make_state(hand, *, card_database=None):
    return CombatState(
        player=Combatant(id="bureaucrat", name="Bureaucrat", max_hp=70, hp=70),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        max_energy=3,
        energy=3,
        hand=list(hand),
        card_database=card_database or {},
    )


def test_exhaust_tag_sends_played_card_to_exhaust_pile():
    card = make_card(
        "temporary_authorization",
        effects=[Effect(type="gain_block", target="self", amount=4)],
        tags=["exhaust"],
    )
    state = make_state([card])

    play_card_from_hand(state, 0)

    assert card in state.exhaust_pile
    assert card not in state.discard_pile
    assert state.player.block == 4


def test_unplayable_card_cannot_be_played():
    card = make_card("red_tape", tags=["unplayable"], card_type="curse")
    state = make_state([card])

    play_card_from_hand(state, 0)

    assert state.hand == [card]
    assert not state.discard_pile
    assert not state.exhaust_pile


def test_create_card_adds_known_card_to_discard_pile_by_default():
    junk = make_card("duplicate_copy", tags=["junk", "exhaust"])
    creator = make_card(
        "expedited_stamp",
        effects=[Effect(type="create_card", card_id="duplicate_copy")],
        tags=["exhaust"],
    )
    state = make_state([creator], card_database={junk.id: junk, creator.id: creator})

    play_card_from_hand(state, 0)

    assert junk in state.discard_pile


def test_create_card_can_add_card_to_hand():
    junk = make_card("duplicate_copy", tags=["junk", "exhaust"])
    creator = make_card(
        "internal_memo",
        effects=[
            Effect(
                type="create_card",
                card_id="duplicate_copy",
                destination="hand",
            )
        ],
        tags=["exhaust"],
    )
    state = make_state([creator], card_database={junk.id: junk, creator.id: creator})

    play_card_from_hand(state, 0)

    assert junk in state.hand


def test_exhaust_cards_by_tag_removes_matching_cards_from_hand():
    junk = make_card("duplicate_copy", tags=["junk", "exhaust"])
    other = make_card("paper_cut")
    shredder = make_card(
        "shredder_drawer",
        effects=[Effect(type="exhaust_cards_by_tag", tag="junk")],
    )
    state = make_state([shredder, junk, other])

    play_card_from_hand(state, 0)

    assert junk in state.exhaust_pile
    assert other in state.hand


def test_draw_cards_effect_draws_from_draw_pile():
    drawn = make_card("paper_cut")
    drawer = make_card("internal_memo", effects=[Effect(type="draw_cards", amount=1)])
    state = make_state([drawer])
    state.draw_pile.append(drawn)

    play_card_from_hand(state, 0)

    assert drawn in state.hand


def test_gain_resource_energy_effect_increases_current_energy():
    card = make_card(
        "provisional_approval",
        effects=[Effect(type="gain_resource", resource="energy", amount=1)],
    )
    state = make_state([card])
    state.energy = 1

    play_card_from_hand(state, 0)

    assert state.energy == 2
