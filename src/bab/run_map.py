from dataclasses import dataclass, replace
from random import Random
from typing import Literal

from bab.models import EncounterDifficulty, EventType

MapNodeType = Literal[
    "combat",
    "elite",
    "event",
    "waiting_room",
    "boss",
]


@dataclass(frozen=True)
class MapNode:
    id: str
    act: int
    depth: int
    node_type: MapNodeType
    encounter_difficulty: EncounterDifficulty | None = None
    event_type: EventType | None = None
    next_node_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunMap:
    act: int
    nodes: dict[str, MapNode]
    start_node_ids: tuple[str, ...]
    boss_node_id: str

    def get_node(self, node_id: str) -> MapNode:
        try:
            return self.nodes[node_id]
        except KeyError as error:
            raise KeyError(f"Unknown map node id: {node_id}") from error

    def available_next_nodes(self, node_id: str) -> list[MapNode]:
        node = self.get_node(node_id)
        return [
            self.get_node(next_node_id)
            for next_node_id in node.next_node_ids
        ]


def combat_difficulty_for_depth(
    depth: int,
    steps_before_boss: int,
) -> EncounterDifficulty:
    if depth <= 1:
        return "easy"

    if depth >= steps_before_boss:
        return "normal"

    return "normal"


def _choose_event_type(rng: Random) -> EventType:
    return rng.choice(
        [
            "narrative",
            "risk_reward",
            "deck",
        ]
    )


def _choose_node_type(
    *,
    rng: Random,
    depth: int,
    lane: int,
    steps_before_boss: int,
) -> MapNodeType:
    if depth == 1:
        return "combat"

    if depth == steps_before_boss:
        if lane == 0:
            return "waiting_room"
        if lane == 1:
            return "elite"
        return "combat"

    forced_types_by_depth: dict[int, MapNodeType] = {
        2: "event",
        3: "elite",
        4: "waiting_room",
    }

    if lane == 0 and depth in forced_types_by_depth:
        return forced_types_by_depth[depth]

    return rng.choices(
        population=[
            "combat",
            "event",
            "waiting_room",
            "elite",
        ],
        weights=[
            5,
            2,
            2,
            1,
        ],
        k=1,
    )[0]


def _make_node(
    *,
    rng: Random,
    act: int,
    depth: int,
    lane: int,
    steps_before_boss: int,
) -> MapNode:
    node_type = _choose_node_type(
        rng=rng,
        depth=depth,
        lane=lane,
        steps_before_boss=steps_before_boss,
    )

    node_id = f"act_{act}_d{depth:02d}_n{lane:02d}"

    if node_type == "combat":
        return MapNode(
            id=node_id,
            act=act,
            depth=depth,
            node_type=node_type,
            encounter_difficulty=combat_difficulty_for_depth(
                depth,
                steps_before_boss,
            ),
        )

    if node_type == "elite":
        return MapNode(
            id=node_id,
            act=act,
            depth=depth,
            node_type=node_type,
            encounter_difficulty="elite",
        )

    if node_type == "event":
        return MapNode(
            id=node_id,
            act=act,
            depth=depth,
            node_type=node_type,
            event_type=_choose_event_type(rng),
        )

    return MapNode(
        id=node_id,
        act=act,
        depth=depth,
        node_type=node_type,
    )


def _next_layer_candidates(
    *,
    current_lane: int,
    next_layer_ids: list[str],
) -> list[str]:
    candidate_lanes = [
        current_lane - 1,
        current_lane,
        current_lane + 1,
    ]

    return [
        next_layer_ids[lane]
        for lane in candidate_lanes
        if 0 <= lane < len(next_layer_ids)
    ]


def generate_act_map(
    rng: Random,
    *,
    act: int = 1,
    steps_before_boss: int = 6,
    width: int = 3,
) -> RunMap:
    if act < 1:
        raise ValueError("Act must be at least 1.")

    if steps_before_boss < 4:
        raise ValueError("Map needs at least 4 steps before the boss.")

    if width < 2:
        raise ValueError("Map width must be at least 2.")

    nodes: dict[str, MapNode] = {}
    layers: list[list[str]] = []

    for depth in range(1, steps_before_boss + 1):
        layer_ids: list[str] = []

        for lane in range(width):
            node = _make_node(
                rng=rng,
                act=act,
                depth=depth,
                lane=lane,
                steps_before_boss=steps_before_boss,
            )
            nodes[node.id] = node
            layer_ids.append(node.id)

        layers.append(layer_ids)

    boss_depth = steps_before_boss + 1
    boss_node = MapNode(
        id=f"act_{act}_boss",
        act=act,
        depth=boss_depth,
        node_type="boss",
        encounter_difficulty="boss",
    )
    nodes[boss_node.id] = boss_node

    for layer_index, layer_ids in enumerate(layers):
        is_last_regular_layer = layer_index == len(layers) - 1

        if is_last_regular_layer:
            for node_id in layer_ids:
                nodes[node_id] = replace(
                    nodes[node_id],
                    next_node_ids=(boss_node.id,),
                )
            continue

        next_layer_ids = layers[layer_index + 1]

        for lane, node_id in enumerate(layer_ids):
            candidates = _next_layer_candidates(
                current_lane=lane,
                next_layer_ids=next_layer_ids,
            )

            if len(candidates) <= 2:
                next_node_ids = tuple(candidates)
            else:
                next_node_ids = tuple(sorted(rng.sample(candidates, k=2)))

            nodes[node_id] = replace(
                nodes[node_id],
                next_node_ids=next_node_ids,
            )

    return RunMap(
        act=act,
        nodes=nodes,
        start_node_ids=tuple(layers[0]),
        boss_node_id=boss_node.id,
    )