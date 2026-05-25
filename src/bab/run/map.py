from dataclasses import dataclass, replace
from random import Random
from typing import Literal

from bab.models import EncounterDifficulty, EventType

MapNodeType = Literal[
    "combat",
    "elite",
    "event",
    "waiting_room",
    "treasure",
    "boss",
]

FIRST_ELITE_DEPTH = 6


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
    if depth <= 3:
        return "easy"

    return "normal"


def _choose_event_type(rng: Random) -> EventType:
    return rng.choice(
        [
            "narrative",
            "risk_reward",
            "deck",
        ]
    )


def _choose_start_lanes(
    rng: Random,
    *,
    width: int,
) -> list[int]:
    maximum_start_width = min(width, 4)
    start_width = rng.choice(list(range(2, maximum_start_width + 1)))
    return sorted(rng.sample(range(width), k=start_width))


def _weighted_node_choice(
    *,
    rng: Random,
    population: list[MapNodeType],
    weights: list[float],
) -> MapNodeType:
    return rng.choices(
        population=population,
        weights=weights,
        k=1,
    )[0]


def _choose_node_type(
    *,
    rng: Random,
    depth: int,
    lane_rank: int,
    steps_before_boss: int,
    first_elite_depth: int,
    elite_weight_multiplier: float,
) -> MapNodeType:
    if depth == 1:
        return "combat"

    if depth == 2 and lane_rank == 0:
        return "event"

    if depth == 3 and lane_rank == 0:
        return "treasure"

    if depth == 6 and lane_rank == 0:
        return "waiting_room"

    if depth == steps_before_boss:
        population: list[MapNodeType] = [
            "combat",
            "treasure",
            "event",
            "waiting_room",
        ]
        weights = [6, 2, 1, 1]

        if depth >= first_elite_depth:
            population.insert(1, "elite")
            weights.insert(1, elite_weight_multiplier)

        return _weighted_node_choice(
            rng=rng,
            population=population,
            weights=weights,
        )

    population = [
        "combat",
        "event",
        "treasure",
        "waiting_room",
    ]
    weights = [7, 2, 1.5, 0.7]

    if depth >= first_elite_depth:
        population.insert(3, "elite")
        weights.insert(3, elite_weight_multiplier)

    return _weighted_node_choice(
        rng=rng,
        population=population,
        weights=weights,
    )


def _make_node(
    *,
    rng: Random,
    act: int,
    depth: int,
    lane: int,
    lane_rank: int,
    steps_before_boss: int,
    first_elite_depth: int,
    elite_weight_multiplier: float,
) -> MapNode:
    node_type = _choose_node_type(
        rng=rng,
        depth=depth,
        lane_rank=lane_rank,
        steps_before_boss=steps_before_boss,
        first_elite_depth=first_elite_depth,
        elite_weight_multiplier=elite_weight_multiplier,
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


def _adjacent_lanes(
    *,
    lane: int,
    width: int,
) -> list[int]:
    return [
        candidate
        for candidate in [lane - 1, lane + 1]
        if 0 <= candidate < width
    ]


def _choose_outgoing_lanes(
    *,
    rng: Random,
    lane: int,
    width: int,
    no_split_streak: int,
) -> set[int]:
    split_chance = min(0.35 + 0.20 * no_split_streak, 0.85)
    outgoing_lanes = {lane}
    adjacent_lanes = _adjacent_lanes(
        lane=lane,
        width=width,
    )

    if adjacent_lanes and rng.random() < split_chance:
        outgoing_lanes.add(rng.choice(adjacent_lanes))

    return outgoing_lanes


def _ensure_at_least_two_lanes(
    *,
    rng: Random,
    lanes: set[int],
    width: int,
) -> set[int]:
    if len(lanes) >= 2:
        return lanes

    only_lane = next(iter(lanes))
    adjacent_lanes = _adjacent_lanes(
        lane=only_lane,
        width=width,
    )

    if adjacent_lanes:
        lanes.add(rng.choice(adjacent_lanes))

    return lanes


def generate_act_map(
    rng: Random,
    *,
    act: int = 1,
    steps_before_boss: int = 9,
    width: int = 4,
    first_elite_depth: int = FIRST_ELITE_DEPTH,
    elite_weight_multiplier: float = 1.0,
) -> RunMap:
    if act < 1:
        raise ValueError("Act must be at least 1.")

    if steps_before_boss < 6:
        raise ValueError("Map needs at least 6 steps before the boss.")

    if width < 2:
        raise ValueError("Map width must be at least 2.")
    if first_elite_depth < 1:
        raise ValueError("First elite depth must be at least 1.")
    if elite_weight_multiplier <= 0:
        raise ValueError("Elite weight multiplier must be positive.")

    nodes: dict[str, MapNode] = {}
    layers: list[list[int]] = []

    current_lanes = _choose_start_lanes(
        rng,
        width=width,
    )
    layers.append(current_lanes)

    no_split_streak_by_lane: dict[int, int] = {
        lane: 0
        for lane in current_lanes
    }

    for rank, lane in enumerate(current_lanes):
        node = _make_node(
            rng=rng,
            act=act,
            depth=1,
            lane=lane,
            lane_rank=rank,
            steps_before_boss=steps_before_boss,
            first_elite_depth=first_elite_depth,
            elite_weight_multiplier=elite_weight_multiplier,
        )
        nodes[node.id] = node

    for depth in range(2, steps_before_boss + 1):
        previous_lanes = current_lanes
        outgoing_by_previous_lane: dict[int, set[int]] = {}

        for previous_lane in previous_lanes:
            outgoing_lanes = _choose_outgoing_lanes(
                rng=rng,
                lane=previous_lane,
                width=width,
                no_split_streak=no_split_streak_by_lane.get(previous_lane, 0),
            )
            outgoing_by_previous_lane[previous_lane] = outgoing_lanes

        next_lanes = set().union(*outgoing_by_previous_lane.values())
        next_lanes = _ensure_at_least_two_lanes(
            rng=rng,
            lanes=next_lanes,
            width=width,
        )
        current_lanes = sorted(next_lanes)
        layers.append(current_lanes)

        for rank, lane in enumerate(current_lanes):
            node = _make_node(
                rng=rng,
                act=act,
                depth=depth,
                lane=lane,
                lane_rank=rank,
                steps_before_boss=steps_before_boss,
                first_elite_depth=first_elite_depth,
                elite_weight_multiplier=elite_weight_multiplier,
            )
            nodes[node.id] = node

        for previous_lane, outgoing_lanes in outgoing_by_previous_lane.items():
            previous_node_id = f"act_{act}_d{depth - 1:02d}_n{previous_lane:02d}"
            next_node_ids = tuple(
                f"act_{act}_d{depth:02d}_n{lane:02d}"
                for lane in sorted(outgoing_lanes)
                if lane in current_lanes
            )
            nodes[previous_node_id] = replace(
                nodes[previous_node_id],
                next_node_ids=next_node_ids,
            )

        new_no_split_streak_by_lane: dict[int, int] = {}

        for lane in current_lanes:
            predecessors = [
                previous_lane
                for previous_lane, outgoing_lanes in outgoing_by_previous_lane.items()
                if lane in outgoing_lanes
            ]

            if len(predecessors) == 1:
                predecessor = predecessors[0]
                predecessor_outgoing_count = len(outgoing_by_previous_lane[predecessor])

                if predecessor_outgoing_count == 1:
                    new_no_split_streak_by_lane[lane] = (
                        no_split_streak_by_lane.get(predecessor, 0) + 1
                    )
                else:
                    new_no_split_streak_by_lane[lane] = 0
            else:
                new_no_split_streak_by_lane[lane] = 0

        no_split_streak_by_lane = new_no_split_streak_by_lane

    boss_depth = steps_before_boss + 1
    boss_node = MapNode(
        id=f"act_{act}_boss",
        act=act,
        depth=boss_depth,
        node_type="boss",
        encounter_difficulty="boss",
    )
    nodes[boss_node.id] = boss_node

    for lane in layers[-1]:
        node_id = f"act_{act}_d{steps_before_boss:02d}_n{lane:02d}"
        nodes[node_id] = replace(
            nodes[node_id],
            next_node_ids=(boss_node.id,),
        )

    start_node_ids = tuple(
        f"act_{act}_d01_n{lane:02d}"
        for lane in layers[0]
    )

    return RunMap(
        act=act,
        nodes=nodes,
        start_node_ids=start_node_ids,
        boss_node_id=boss_node.id,
    )
