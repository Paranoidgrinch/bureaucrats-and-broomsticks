from bab.console.event_effect_handlers import CONSOLE_EVENT_EFFECT_HANDLERS
from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.rules.card_effect_handlers import CARD_EFFECT_HANDLERS
from bab.rules.relic_effect_handlers import SUPPORTED_RELIC_EFFECT_TYPES


def test_all_content_card_and_enemy_effects_have_card_handlers() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        used_effect_types = {
            effect.type
            for card in catalog.card_database.values()
            for effect in card.effects
        }

        used_effect_types.update(
            effect.type
            for enemy in catalog.enemy_database.values()
            for intent in enemy.intents
            for effect in intent.effects
        )

        missing = sorted(set(used_effect_types) - set(CARD_EFFECT_HANDLERS))
        assert not missing, f"{catalog.act_manifest.id} has card/enemy effects without handlers: {missing}"


def test_all_content_relic_effects_have_relic_handlers() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        used_effect_types = {
            effect.type
            for relic in catalog.relic_database.values()
            for effect in relic.effects
        }

        missing = sorted(used_effect_types - SUPPORTED_RELIC_EFFECT_TYPES)
        assert not missing, f"{catalog.act_manifest.id} has relic effects without handlers: {missing}"


def test_all_content_event_effects_have_console_handlers() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        used_effect_types = {
            effect.type
            for event in catalog.event_database.values()
            for choice in event.choices
            for effect in choice.effects
        }

        missing = sorted(set(used_effect_types) - set(CONSOLE_EVENT_EFFECT_HANDLERS))
        assert not missing, f"{catalog.act_manifest.id} has event effects without handlers: {missing}"
