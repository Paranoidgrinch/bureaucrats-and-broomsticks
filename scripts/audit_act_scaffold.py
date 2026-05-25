"""Audit configured act scaffolds without writing generated run artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from random import Random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.run.map import generate_act_map
from bab.systems.rewards import build_card_reward_pool, choose_card_rewards
from bab.systems.shop import choose_shop_card_offers, choose_shop_relic_offers


def audit_act(manifest_path: str, *, seeds: int) -> dict[str, object]:
    catalog = load_content_catalog_from_act_manifest(manifest_path)
    manifest = catalog.act_manifest
    map_config = manifest.map

    boss_depths: list[int] = []
    elite_counts: list[int] = []
    earliest_elite_depths: list[int] = []
    node_type_counts: Counter[str] = Counter()

    for seed in range(seeds):
        run_map = generate_act_map(
            Random(seed),
            act=manifest.act,
            steps_before_boss=map_config.steps_before_boss,
            width=map_config.width,
            first_elite_depth=map_config.first_elite_depth,
            elite_weight_multiplier=map_config.elite_weight_multiplier,
        )

        boss = run_map.get_node(run_map.boss_node_id)
        boss_depths.append(boss.depth)

        elites = [
            node
            for node in run_map.nodes.values()
            if node.node_type == "elite"
        ]
        elite_counts.append(len(elites))

        if elites:
            earliest_elite_depths.append(min(node.depth for node in elites))

        node_type_counts.update(node.node_type for node in run_map.nodes.values())

    reward_pool_counts: dict[str, int] = {}
    reward_offer_counts: dict[str, int] = {}
    shop_card_offer_counts: dict[str, int] = {}
    shop_relic_offer_counts: dict[str, int] = {}

    for index, character_id in enumerate(sorted(catalog.character_classes)):
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )
        rewards = choose_card_rewards(
            catalog.card_database,
            Random(10_000 + manifest.act * 100 + index),
            count=3,
            card_class=character_id,
            act=manifest.act,
        )
        shop_cards = choose_shop_card_offers(
            catalog.card_database,
            Random(20_000 + manifest.act * 100 + index),
            card_class=character_id,
            act=manifest.act,
            fight_number=max(1, map_config.steps_before_boss // 2),
            count=5,
        )
        shop_relics = choose_shop_relic_offers(
            catalog.relic_database,
            owned_relics=[],
            rng=Random(30_000 + manifest.act * 100 + index),
            act=manifest.act,
            fight_number=max(1, map_config.steps_before_boss // 2),
            card_class=character_id,
            count=3,
        )

        if any(card.rarity == "epic" for card in reward_pool):
            raise AssertionError(f"{manifest.id}: epic card leaked into normal reward pool.")
        if any("transition_reward" in card.tags for card in reward_pool):
            raise AssertionError(f"{manifest.id}: transition reward leaked into normal reward pool.")
        if any(offer.card.rarity == "epic" for offer in shop_cards):
            raise AssertionError(f"{manifest.id}: epic card leaked into shop card offers.")

        for offer in shop_relics:
            relic = offer.relic
            if relic.allowed_classes and character_id not in relic.allowed_classes:
                raise AssertionError(
                    f"{manifest.id}: wrong class-specific relic offered to {character_id}: {relic.id}"
                )

        reward_pool_counts[character_id] = len(reward_pool)
        reward_offer_counts[character_id] = len(rewards)
        shop_card_offer_counts[character_id] = len(shop_cards)
        shop_relic_offer_counts[character_id] = len(shop_relics)

    return {
        "manifest_id": manifest.id,
        "act": manifest.act,
        "name": manifest.name,
        "steps_before_boss": map_config.steps_before_boss,
        "width": map_config.width,
        "first_elite_depth": map_config.first_elite_depth,
        "elite_weight_multiplier": map_config.elite_weight_multiplier,
        "boss_depth_min": min(boss_depths),
        "boss_depth_max": max(boss_depths),
        "elite_count_min": min(elite_counts),
        "elite_count_avg": sum(elite_counts) / len(elite_counts),
        "elite_count_max": max(elite_counts),
        "earliest_elite_min": min(earliest_elite_depths) if earliest_elite_depths else None,
        "earliest_elite_max": max(earliest_elite_depths) if earliest_elite_depths else None,
        "node_type_counts": dict(sorted(node_type_counts.items())),
        "character_count": len(catalog.character_classes),
        "card_count": len(catalog.card_database),
        "relic_count": len(catalog.relic_database),
        "enemy_count": len(catalog.enemy_database),
        "encounter_count": len(catalog.encounter_database),
        "event_count": len(catalog.event_database),
        "reward_pool_min": min(reward_pool_counts.values()),
        "shop_card_offer_min": min(shop_card_offer_counts.values()),
        "shop_relic_offer_min": min(shop_relic_offer_counts.values()),
    }


def print_audit(result: dict[str, object]) -> None:
    print(f"Act {result['act']}: {result['name']} ({result['manifest_id']})")
    print("-" * 72)
    print(
        "map: "
        f"steps_before_boss={result['steps_before_boss']}, "
        f"width={result['width']}, "
        f"first_elite_depth={result['first_elite_depth']}, "
        f"elite_weight_multiplier={result['elite_weight_multiplier']}"
    )
    print(
        "boss depth: "
        f"min={result['boss_depth_min']}, max={result['boss_depth_max']}"
    )
    print(
        "elites per map: "
        f"min={result['elite_count_min']}, "
        f"avg={result['elite_count_avg']:.2f}, "
        f"max={result['elite_count_max']}"
    )
    print(
        "earliest elite depth: "
        f"min={result['earliest_elite_min']}, "
        f"max={result['earliest_elite_max']}"
    )
    print(
        "content: "
        f"characters={result['character_count']}, "
        f"cards={result['card_count']}, "
        f"relics={result['relic_count']}, "
        f"enemies={result['enemy_count']}, "
        f"encounters={result['encounter_count']}, "
        f"events={result['event_count']}"
    )
    print(
        "offers: "
        f"min_reward_pool={result['reward_pool_min']}, "
        f"min_shop_cards={result['shop_card_offer_min']}, "
        f"min_shop_relics={result['shop_relic_offer_min']}"
    )
    print("node type totals:")
    for node_type, count in result["node_type_counts"].items():
        print(f"  {node_type}: {count}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument(
        "--acts",
        nargs="*",
        type=int,
        default=[],
        help="Optional list of act numbers to audit.",
    )
    args = parser.parse_args()

    if args.seeds < 1:
        raise SystemExit("--seeds must be at least 1")

    selected_manifest_files = []
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        if not args.acts or catalog.act_manifest.act in args.acts:
            selected_manifest_files.append(manifest_path)

    print("Act scaffold audit")
    print("==================")
    print(f"seeds per act: {args.seeds}")
    print()

    for manifest_path in selected_manifest_files:
        print_audit(audit_act(manifest_path, seeds=args.seeds))


if __name__ == "__main__":
    main()
