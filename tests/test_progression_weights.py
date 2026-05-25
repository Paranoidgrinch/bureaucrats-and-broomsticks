from bab.systems.progression_weights import content_progression_weight
from bab.systems.rewards import card_progression_weight
from bab.systems.shop import shop_progression_weight


class TaggedThing:
    def __init__(self, tags):
        self.tags = tags


def test_content_progression_weight_keeps_act_2_behavior() -> None:
    assert content_progression_weight(["act_2"], act=2) == 4
    assert content_progression_weight(["act_1"], act=2) == 1
    assert content_progression_weight([], act=2) == 1


def test_content_progression_weight_generalizes_for_late_acts() -> None:
    assert content_progression_weight(["act_3"], act=3) == 6
    assert content_progression_weight(["act_2"], act=3) == 2
    assert content_progression_weight(["act_1"], act=3) == 1

    assert content_progression_weight(["act_4"], act=4) == 6
    assert content_progression_weight(["act_3"], act=4) == 2
    assert content_progression_weight(["act_2"], act=4) == 1
    assert content_progression_weight(["act_1"], act=4) == 1

    assert content_progression_weight(["act_5"], act=5) == 6
    assert content_progression_weight(["act_4"], act=5) == 2
    assert content_progression_weight(["act_3"], act=5) == 1
    assert content_progression_weight(["act_2"], act=5) == 1
    assert content_progression_weight(["act_1"], act=5) == 1


def test_reward_and_shop_weight_wrappers_use_shared_progression_logic() -> None:
    act_4_item = TaggedThing(["act_4"])
    act_3_item = TaggedThing(["act_3"])
    older_item = TaggedThing(["act_2"])

    assert card_progression_weight(act_4_item, act=4) == 6
    assert card_progression_weight(act_3_item, act=4) == 2
    assert card_progression_weight(older_item, act=4) == 1

    assert shop_progression_weight(act_4_item, act=4) == 6
    assert shop_progression_weight(act_3_item, act=4) == 2
    assert shop_progression_weight(older_item, act=4) == 1
