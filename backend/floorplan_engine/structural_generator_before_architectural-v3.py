from math import ceil
from typing import Any

from floorplan_engine.requirement_engine import (
    build_requirements,
)
from floorplan_engine.room_program import (
    build_room_program,
)


# ============================================================
# BASIC OBJECT BUILDERS
# ============================================================


def _room(
    room_id: str,
    room_type: str,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    floor_level: int = 0,
    accessible: bool = False,
    priority: str = "required",
) -> dict[str, Any]:
    return {
        "id": room_id,
        "type": room_type,
        "name": name,
        "x": round(x, 3),
        "y": round(y, 3),
        "width": round(width, 3),
        "height": round(height, 3),
        "area": round(width * height, 3),
        "floor_level": floor_level,
        "accessible": accessible,
        "priority": priority,
    }


def _door(
    door_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    orientation: str,
    floor_level: int,
    door_type: str = "internal",
) -> dict[str, Any]:
    return {
        "id": door_id,
        "type": door_type,
        "x": round(x, 3),
        "y": round(y, 3),
        "width": round(width, 3),
        "height": round(height, 3),
        "orientation": orientation,
        "floor_level": floor_level,
    }


def _window(
    window_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    orientation: str,
    floor_level: int,
) -> dict[str, Any]:
    return {
        "id": window_id,
        "x": round(x, 3),
        "y": round(y, 3),
        "width": round(width, 3),
        "height": round(height, 3),
        "orientation": orientation,
        "floor_level": floor_level,
    }


# ============================================================
# ROOM WEIGHTS
#
# These are layout weights, not fixed dimensions.
# They allow the same engine to work for different plot sizes.
# ============================================================


BASE_WEIGHTS = {
    "living": 1.55,
    "dining": 1.00,
    "kitchen": 1.00,
    "bedroom": 1.30,
    "bathroom": 0.60,
    "stairs": 0.75,
    "passage": 0.55,
    "office": 0.90,
    "prayer": 0.65,
    "balcony": 0.75,
    "utility": 0.70,
    "storage": 0.55,
}


def _space_weight(
    space: dict[str, Any],
    strategy: str,
) -> float:

    room_type = str(
        space.get("type", "room")
    )

    weight = BASE_WEIGHTS.get(
        room_type,
        1.0,
    )

    # Balanced option:
    # keep weights close to defaults.

    if strategy == "balanced":
        return weight

    # Open Living:
    # increase social/common spaces.

    if strategy == "open_living":
        if room_type == "living":
            weight *= 1.35

        elif room_type == "dining":
            weight *= 1.20

        elif room_type == "kitchen":
            weight *= 1.10

        elif room_type == "bedroom":
            weight *= 0.92

        elif room_type == "passage":
            weight *= 0.85

    # Privacy:
    # increase bedrooms/circulation.

    elif strategy == "privacy":
        if room_type == "bedroom":
            weight *= 1.18

        elif room_type == "bathroom":
            weight *= 1.08

        elif room_type == "passage":
            weight *= 1.25

        elif room_type == "living":
            weight *= 0.92

    return max(weight, 0.25)


# ============================================================
# SPACE ORDERING
# ============================================================


def _sort_spaces(
    spaces: list[dict[str, Any]],
    strategy: str,
) -> list[dict[str, Any]]:

    if strategy == "balanced":
        order = {
            "living": 1,
            "dining": 2,
            "kitchen": 3,
            "bedroom": 4,
            "bathroom": 5,
            "office": 6,
            "prayer": 7,
            "passage": 8,
            "stairs": 9,
            "balcony": 10,
        }

    elif strategy == "open_living":
        order = {
            "living": 1,
            "dining": 2,
            "kitchen": 3,
            "stairs": 4,
            "bedroom": 5,
            "bathroom": 6,
            "office": 7,
            "prayer": 8,
            "passage": 9,
            "balcony": 10,
        }

    else:
        order = {
            "bedroom": 1,
            "bathroom": 2,
            "passage": 3,
            "stairs": 4,
            "office": 5,
            "prayer": 6,
            "living": 7,
            "dining": 8,
            "kitchen": 9,
            "balcony": 10,
        }

    return sorted(
        spaces,
        key=lambda item: (
            order.get(
                str(item.get("type")),
                50,
            ),
            str(item.get("id")),
        ),
    )


# ============================================================
# FLOOR ALLOCATION
# ============================================================


def _allocate_spaces_to_floors(
    room_program: dict[str, Any],
    floors: int,
    strategy: str,
) -> list[list[dict[str, Any]]]:

    floor_spaces: list[
        list[dict[str, Any]]
    ] = [
        []
        for _ in range(floors)
    ]

    spaces = list(
        room_program.get(
            "spaces",
            [],
        )
    )

    # Circulation is handled separately
    # so every floor can receive one.

    circulation_spaces = [
        space
        for space in spaces
        if space.get("type") == "passage"
    ]

    spaces = [
        space
        for space in spaces
        if space.get("type") != "passage"
    ]

    upper_index = 1

    for space in spaces:
        preference = str(
            space.get(
                "floor_preference",
                "any",
            )
        )

        if preference == "ground":
            floor_spaces[0].append(
                dict(space)
            )

        elif (
            preference == "upper"
            and floors > 1
        ):
            floor_spaces[
                min(
                    upper_index,
                    floors - 1,
                )
            ].append(
                dict(space)
            )

            if floors > 2:
                upper_index += 1

                if upper_index >= floors:
                    upper_index = 1

        else:
            # Flexible rooms are placed according
            # to strategy and current floor load.

            if floors == 1:
                selected_floor = 0

            elif (
                strategy == "privacy"
                and space.get("type")
                in {
                    "bedroom",
                    "bathroom",
                    "office",
                }
            ):
                selected_floor = 1

            else:
                selected_floor = min(
                    range(floors),
                    key=lambda level: len(
                        floor_spaces[level]
                    ),
                )

            floor_spaces[
                selected_floor
            ].append(
                dict(space)
            )

    # Add circulation to every floor.

    for level in range(floors):
        floor_spaces[level].append(
            {
                "id": (
                    f"circulation-floor-{level}"
                ),
                "type": "passage",
                "name": "Circulation",
                "floor_preference": (
                    "ground"
                    if level == 0
                    else "upper"
                ),
                "priority": "required",
                "accessible": bool(
                    room_program.get(
                        "rules",
                        {},
                    ).get(
                        "wheelchair_friendly",
                        False,
                    )
                ),
                "min_area": None,
            }
        )

    # A staircase must exist on all levels
    # involved in a multi-floor building.

    if floors > 1:
        for level in range(floors):
            already_has_stairs = any(
                space.get("type")
                == "stairs"
                for space in floor_spaces[
                    level
                ]
            )

            if not already_has_stairs:
                floor_spaces[level].append(
                    {
                        "id": (
                            f"stairs-floor-{level}"
                        ),
                        "type": "stairs",
                        "name": "Staircase",
                        "floor_preference": (
                            "ground"
                            if level == 0
                            else "upper"
                        ),
                        "priority": "required",
                        "accessible": False,
                        "min_area": 55,
                    }
                )

    return floor_spaces


# ============================================================
# GRID / RECTANGLE PACKING
#
# This creates non-overlapping room rectangles.
# Different strategies use different row/column behaviour.
# ============================================================


def _recommended_columns(
    room_count: int,
    strategy: str,
) -> int:

    if room_count <= 3:
        return 1

    if strategy == "privacy":
        return min(
            3,
            max(
                2,
                ceil(room_count / 3),
            ),
        )

    return 2


def _pack_floor(
    spaces: list[dict[str, Any]],
    width: float,
    height: float,
    floor_level: int,
    strategy: str,
    prefix: str,
) -> list[dict[str, Any]]:

    spaces = _sort_spaces(
        spaces,
        strategy,
    )

    if not spaces:
        return []

    columns = _recommended_columns(
        len(spaces),
        strategy,
    )

    rows: list[
        list[dict[str, Any]]
    ] = []

    for start in range(
        0,
        len(spaces),
        columns,
    ):
        rows.append(
            spaces[
                start:
                start + columns
            ]
        )

    row_weights: list[float] = []

    for row in rows:
        row_weight = max(
            _space_weight(
                space,
                strategy,
            )
            for space in row
        )

        row_weights.append(
            row_weight
        )

    total_row_weight = sum(
        row_weights
    )

    if total_row_weight <= 0:
        total_row_weight = 1.0

    y = 0.0

    rooms: list[
        dict[str, Any]
    ] = []

    room_counter = 1

    for row_index, row in enumerate(rows):

        if row_index == len(rows) - 1:
            row_height = height - y
        else:
            row_height = (
                height
                * (
                    row_weights[
                        row_index
                    ]
                    / total_row_weight
                )
            )

        weights = [
            _space_weight(
                space,
                strategy,
            )
            for space in row
        ]

        total_weight = sum(weights)

        if total_weight <= 0:
            total_weight = 1.0

        x = 0.0

        for index, space in enumerate(row):

            if index == len(row) - 1:
                room_width = width - x
            else:
                room_width = (
                    width
                    * (
                        weights[index]
                        / total_weight
                    )
                )

            room_id = (
                f"{prefix}-"
                f"{floor_level}-"
                f"{space.get('id', room_counter)}"
            )

            rooms.append(
                _room(
                    room_id=room_id,
                    room_type=str(
                        space.get(
                            "type",
                            "room",
                        )
                    ),
                    name=str(
                        space.get(
                            "name",
                            "Room",
                        )
                    ),
                    x=x,
                    y=y,
                    width=room_width,
                    height=row_height,
                    floor_level=(
                        floor_level
                    ),
                    accessible=bool(
                        space.get(
                            "accessible",
                            False,
                        )
                    ),
                    priority=str(
                        space.get(
                            "priority",
                            "required",
                        )
                    ),
                )
            )

            x += room_width
            room_counter += 1

        y += row_height

    return rooms


# ============================================================
# OPENING GENERATION
# ============================================================


def _generate_openings_for_floor(
    floor: dict[str, Any],
    building_width: float,
    building_height: float,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:

    level = int(
        floor.get("level", 0)
    )

    rooms = floor.get(
        "rooms",
        [],
    )

    doors: list[
        dict[str, Any]
    ] = []

    windows: list[
        dict[str, Any]
    ] = []

    door_index = 1
    window_index = 1

    for room in rooms:

        room_type = str(
            room.get("type", "")
        )

        if room_type == "stairs":
            continue

        x = float(room["x"])
        y = float(room["y"])
        w = float(room["width"])
        h = float(room["height"])

        # Internal room door.

        door_width = min(
            3.5,
            max(
                2.8,
                w * 0.18,
            ),
        )

        door_x = (
            x
            + w / 2
            - door_width / 2
        )

        doors.append(
            _door(
                door_id=(
                    f"door-{level}-"
                    f"{door_index}"
                ),
                x=door_x,
                y=max(
                    y,
                    y + h - 0.25,
                ),
                width=door_width,
                height=0.25,
                orientation="horizontal",
                floor_level=level,
            )
        )

        door_index += 1

        # Top exterior wall.

        if abs(y) < 0.05:
            win_width = min(
                6.0,
                max(
                    3.0,
                    w * 0.32,
                ),
            )

            windows.append(
                _window(
                    (
                        f"window-{level}-"
                        f"{window_index}"
                    ),
                    (
                        x
                        + w / 2
                        - win_width / 2
                    ),
                    0,
                    win_width,
                    0.20,
                    "horizontal",
                    level,
                )
            )

            window_index += 1

        # Bottom exterior wall.

        if abs(
            (y + h)
            - building_height
        ) < 0.05:

            win_width = min(
                6.0,
                max(
                    3.0,
                    w * 0.32,
                ),
            )

            windows.append(
                _window(
                    (
                        f"window-{level}-"
                        f"{window_index}"
                    ),
                    (
                        x
                        + w / 2
                        - win_width / 2
                    ),
                    (
                        building_height
                        - 0.20
                    ),
                    win_width,
                    0.20,
                    "horizontal",
                    level,
                )
            )

            window_index += 1

        # Left exterior wall.

        if abs(x) < 0.05:
            win_height = min(
                6.0,
                max(
                    3.0,
                    h * 0.32,
                ),
            )

            windows.append(
                _window(
                    (
                        f"window-{level}-"
                        f"{window_index}"
                    ),
                    0,
                    (
                        y
                        + h / 2
                        - win_height / 2
                    ),
                    0.20,
                    win_height,
                    "vertical",
                    level,
                )
            )

            window_index += 1

        # Right exterior wall.

        if abs(
            (x + w)
            - building_width
        ) < 0.05:

            win_height = min(
                6.0,
                max(
                    3.0,
                    h * 0.32,
                ),
            )

            windows.append(
                _window(
                    (
                        f"window-{level}-"
                        f"{window_index}"
                    ),
                    (
                        building_width
                        - 0.20
                    ),
                    (
                        y
                        + h / 2
                        - win_height / 2
                    ),
                    0.20,
                    win_height,
                    "vertical",
                    level,
                )
            )

            window_index += 1

    # Main entrance only on Ground Floor.

    if level == 0:
        entrance_width = min(
            4.0,
            building_width * 0.15,
        )

        doors.append(
            _door(
                "main-entry-door",
                (
                    building_width / 2
                    - entrance_width / 2
                ),
                (
                    building_height
                    - 0.25
                ),
                entrance_width,
                0.25,
                "horizontal",
                0,
                door_type="main",
            )
        )

    return doors, windows


# ============================================================
# OUTDOOR / SITE FEATURE METADATA
# ============================================================


def _build_site_features(
    room_program: dict[str, Any],
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    output: list[
        dict[str, Any]
    ] = []

    site = requirements.get(
        "site",
        {},
    )

    road_facing = site.get(
        "road_facing"
    )

    for feature in room_program.get(
        "outdoor_spaces",
        [],
    ):
        item = dict(feature)

        item["road_facing"] = (
            road_facing
        )

        output.append(item)

    return output


# ============================================================
# ONE CANDIDATE
# ============================================================


def _build_candidate(
    candidate_id: str,
    title: str,
    strategy: str,
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
    requirements: dict[str, Any],
    room_program: dict[str, Any],
) -> dict[str, Any]:

    allocated = (
        _allocate_spaces_to_floors(
            room_program=room_program,
            floors=floors,
            strategy=strategy,
        )
    )

    floor_plans: list[
        dict[str, Any]
    ] = []

    all_rooms: list[
        dict[str, Any]
    ] = []

    all_doors: list[
        dict[str, Any]
    ] = []

    all_windows: list[
        dict[str, Any]
    ] = []

    for level in range(floors):

        rooms = _pack_floor(
            spaces=allocated[level],
            width=target_width,
            height=target_height,
            floor_level=level,
            strategy=strategy,
            prefix=candidate_id,
        )

        floor = {
            "level": level,
            "name": (
                "Ground Floor"
                if level == 0
                else (
                    "First Floor"
                    if level == 1
                    else f"Floor {level + 1}"
                )
            ),
            "rooms": rooms,
            "doors": [],
            "windows": [],
            "stairs": [
                room
                for room in rooms
                if room.get("type")
                == "stairs"
            ],
        }

        doors, windows = (
            _generate_openings_for_floor(
                floor=floor,
                building_width=target_width,
                building_height=(
                    target_height
                ),
            )
        )

        floor["doors"] = doors
        floor["windows"] = windows

        floor_plans.append(
            floor
        )

        all_rooms.extend(
            rooms
        )

        all_doors.extend(
            doors
        )

        all_windows.extend(
            windows
        )

    return {
        "id": candidate_id,
        "title": title,
        "strategy": strategy,

        "source": (
            "ZYNORA Personalized "
            "Structural Generator"
        ),

        "name": project.get(
            "name",
            "Generated Home",
        ),

        "width": round(
            target_width,
            3,
        ),

        "height": round(
            target_height,
            3,
        ),

        "aspect_ratio": round(
            target_width
            / target_height,
            3,
        ),

        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "floors": floors,

        "room_count": len(
            all_rooms
        ),

        "rooms": all_rooms,

        "floor_plans": (
            floor_plans
        ),

        "doors": all_doors,

        "windows": (
            all_windows
        ),

        "furniture": [],

        "boundary": [
            [0, 0],
            [target_width, 0],
            [
                target_width,
                target_height,
            ],
            [0, target_height],
        ],

        "site_features": (
            _build_site_features(
                room_program,
                requirements,
            )
        ),

        "requirements": (
            requirements
        ),

        "room_program": (
            room_program
        ),

        "match_type": (
            "generated"
        ),

        "requires_structural_generation": (
            False
        ),

        "generated_from_requirements": (
            True
        ),

        "personalized": True,

        "generation_version": (
            "zynora-personalized-v2"
        ),
    }


# ============================================================
# PUBLIC API — THREE CANDIDATES
# ============================================================


def generate_structural_candidates(
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> list[dict[str, Any]]:

    if (
        target_width <= 0
        or target_height <= 0
    ):
        raise ValueError(
            "Building dimensions must "
            "be positive."
        )

    if bedrooms < 1:
        raise ValueError(
            "Bedrooms must be at least 1."
        )

    if bathrooms < 1:
        raise ValueError(
            "Bathrooms must be at least 1."
        )

    if floors < 1:
        raise ValueError(
            "Floors must be at least 1."
        )

    # ---------------------------------
    # UNDERSTAND USER REQUIREMENTS
    # ---------------------------------

    requirements = build_requirements(
        project=project,
        building_width=(
            target_width
        ),
        building_height=(
            target_height
        ),
    )

    # Keep explicit API values as
    # authoritative hard constraints.

    requirements[
        "hard_constraints"
    ]["bedrooms"] = bedrooms

    requirements[
        "hard_constraints"
    ]["bathrooms"] = bathrooms

    requirements[
        "hard_constraints"
    ]["floors"] = floors

    # ---------------------------------
    # CREATE ARCHITECTURAL ROOM PROGRAM
    # ---------------------------------

    room_program = build_room_program(
        requirements
    )

    # ---------------------------------
    # GENERATE THREE DIFFERENT OPTIONS
    # ---------------------------------

    balanced = _build_candidate(
        candidate_id="candidate-a",
        title="Balanced Family Plan",
        strategy="balanced",
        target_width=target_width,
        target_height=target_height,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floors=floors,
        project=project,
        requirements=requirements,
        room_program=room_program,
    )

    open_living = _build_candidate(
        candidate_id="candidate-b",
        title="Open Living Plan",
        strategy="open_living",
        target_width=target_width,
        target_height=target_height,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floors=floors,
        project=project,
        requirements=requirements,
        room_program=room_program,
    )

    privacy = _build_candidate(
        candidate_id="candidate-c",
        title="Privacy Focused Plan",
        strategy="privacy",
        target_width=target_width,
        target_height=target_height,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floors=floors,
        project=project,
        requirements=requirements,
        room_program=room_program,
    )

    return [
        balanced,
        open_living,
        privacy,
    ]


# ============================================================
# BACKWARD COMPATIBILITY
#
# Existing floorplan_routes.py currently expects one plan.
# Keep returning Candidate A until we introduce the new
# three-plan API and frontend selection screen.
# ============================================================


def generate_structural_plan(
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> dict[str, Any]:

    candidates = (
        generate_structural_candidates(
            target_width=(
                target_width
            ),
            target_height=(
                target_height
            ),
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            floors=floors,
            project=project,
        )
    )

    return candidates[0]
