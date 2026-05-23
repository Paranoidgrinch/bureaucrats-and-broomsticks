from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.rules.card_effect_handlers import CARD_EFFECT_HANDLERS


def test_all_enemy_intent_actions_have_effect_handlers() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        used_effect_types = {
            effect.type
            for enemy in catalog.enemy_database.values()
            for intent in enemy.intents
            for effect in intent.actions
        }

        missing = sorted(set(used_effect_types) - set(CARD_EFFECT_HANDLERS))
        assert not missing, (
            f"{catalog.act_manifest.id} has enemy intent actions without handlers: "
            f"{missing}"
        )
