from bab.content.catalog import load_default_content_catalog


EXPECTED_NEW_EFFECT_RELICS = {
    "emergency_inkwell",
    "borrowed_authority",
    "warm_waiting_room_bench",
    "forbidden_rubber_stamp",
    "counterfeit_priority_pass",
    "official_break_room_key",
    "overtime_chit",
    "junior_deputy_sash",
    "overfilled_inbox",
    "clerical_second_wind",
}


def test_relics_using_new_effects_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_NEW_EFFECT_RELICS <= set(catalog.relic_database)


def test_act_1_relic_content_uses_each_new_relic_effect_type() -> None:
    catalog = load_default_content_catalog()

    used_effect_types = {
        effect.type
        for relic in catalog.relic_database.values()
        for effect in relic.effects
    }

    assert "gain_energy_at_combat_start" in used_effect_types
    assert "gain_strength_at_combat_start" in used_effect_types
    assert "heal_at_combat_start" in used_effect_types
    assert "apply_status_to_player_at_combat_start" in used_effect_types


def test_risk_reward_relics_apply_status_to_player() -> None:
    catalog = load_default_content_catalog()

    risk_reward_relics = [
        relic
        for relic in catalog.relic_database.values()
        if "risk_reward" in relic.tags
    ]

    assert risk_reward_relics

    assert any(
        effect.type == "apply_status_to_player_at_combat_start"
        for relic in risk_reward_relics
        for effect in relic.effects
    )


def test_new_relic_effect_relics_have_player_facing_text() -> None:
    catalog = load_default_content_catalog()

    for relic_id in EXPECTED_NEW_EFFECT_RELICS:
        relic = catalog.relic_database[relic_id]

        assert relic.name
        assert relic.description
        assert relic.effects
