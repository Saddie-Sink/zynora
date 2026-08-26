from typing import Any


def _room(
    room_id: str,
    room_type: str,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    floor_level: int = 0,
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


def _generate_openings_for_floor(
    floor: dict[str, Any],
    building_width: float,
    building_height: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:

    level = int(floor["level"])
    rooms = floor["rooms"]

    doors: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []

    door_index = 1
    window_index = 1

    for room in rooms:
        room_type = room.get("type")

        if room_type == "stairs":
            continue

        x = float(room["x"])
        y = float(room["y"])
        w = float(room["width"])
        h = float(room["height"])

        # -------------------------
        # BASIC INTERNAL DOOR
        # -------------------------

        door_width = min(
            3.0,
            max(2.5, w * 0.22),
        )

        doors.append(
            _door(
                f"door-{level}-{door_index}",
                x + w / 2 - door_width / 2,
                y + h - 0.25,
                door_width,
                0.25,
                "horizontal",
                level,
            )
        )

        door_index += 1

        # -------------------------
        # EXTERIOR WINDOWS
        # -------------------------

        # Top exterior wall
        if abs(y) < 0.05:
            window_width = min(
                6.0,
                max(3.0, w * 0.35),
            )

            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    x + w / 2 - window_width / 2,
                    0,
                    window_width,
                    0.2,
                    "horizontal",
                    level,
                )
            )

            window_index += 1

        # Bottom exterior wall
        if abs((y + h) - building_height) < 0.05:
            window_width = min(
                6.0,
                max(3.0, w * 0.35),
            )

            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    x + w / 2 - window_width / 2,
                    building_height - 0.2,
                    window_width,
                    0.2,
                    "horizontal",
                    level,
                )
            )

            window_index += 1

        # Left exterior wall
        if abs(x) < 0.05:
            window_height = min(
                6.0,
                max(3.0, h * 0.35),
            )

            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    0,
                    y + h / 2 - window_height / 2,
                    0.2,
                    window_height,
                    "vertical",
                    level,
                )
            )

            window_index += 1

        # Right exterior wall
        if abs((x + w) - building_width) < 0.05:
            window_height = min(
                6.0,
                max(3.0, h * 0.35),
            )

            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    building_width - 0.2,
                    y + h / 2 - window_height / 2,
                    0.2,
                    window_height,
                    "vertical",
                    level,
                )
            )

            window_index += 1

    # -------------------------
    # MAIN ENTRANCE
    # -------------------------

    if level == 0:
        doors.append(
            _door(
                "main-entry-door",
                building_width * 0.45,
                building_height - 0.25,
                4.0,
                0.25,
                "horizontal",
                0,
                door_type="main",
            )
        )

    return doors, windows


def _base_plan(
    candidate_id: str,
    title: str,
    strategy: str,
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
    floor_plans: list[dict[str, Any]],
) -> dict[str, Any]:

    # Generate doors and windows for every floor
    for floor in floor_plans:
        doors, windows = _generate_openings_for_floor(
            floor,
            target_width,
            target_height,
        )

        floor["doors"] = doors
        floor["windows"] = windows

    rooms = [
        room
        for floor in floor_plans
        for room in floor["rooms"]
    ]

    doors = [
        door
        for floor in floor_plans
        for door in floor["doors"]
    ]

    windows = [
        window
        for floor in floor_plans
        for window in floor["windows"]
    ]

    return {
        "id": candidate_id,
        "title": title,
        "strategy": strategy,
        "source": "ZYNORA Structural Generator",
        "name": project.get(
            "name",
            "Generated Home",
        ),
        "width": round(target_width, 3),
        "height": round(target_height, 3),
        "aspect_ratio": round(
            target_width / target_height,
            3,
        ),
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "floors": floors,
        "room_count": len(rooms),
        "rooms": rooms,
        "floor_plans": floor_plans,
        "doors": doors,
        "windows": windows,
        "furniture": [],
        "boundary": [
            [0, 0],
            [target_width, 0],
            [target_width, target_height],
            [0, target_height],
        ],
        "match_type": "generated",
        "requires_structural_generation": False,
        "generated_from_requirements": True,
    }


def _balanced_plan(
    w: float,
    h: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> dict[str, Any]:

    left = w * 0.52
    right = w - left

    top = h * 0.50
    bottom = h - top

    ground = [
        _room(
            "a-living",
            "living",
            "Living Room",
            0,
            0,
            left,
            top,
        ),
        _room(
            "a-kitchen",
            "kitchen",
            "Kitchen",
            left,
            0,
            right,
            top * 0.45,
        ),
        _room(
            "a-dining",
            "dining",
            "Dining Room",
            left,
            top * 0.45,
            right,
            top * 0.55,
        ),
        _room(
            "a-bedroom-1",
            "bedroom",
            "Bedroom 1",
            0,
            top,
            left,
            bottom,
        ),
        _room(
            "a-bath-1",
            "bathroom",
            "Bathroom 1",
            left,
            top,
            right / 2,
            bottom * 0.42,
        ),
        _room(
            "a-bath-2",
            "bathroom",
            "Bathroom 2",
            left + right / 2,
            top,
            right / 2,
            bottom * 0.42,
        ),
        _room(
            "a-stairs",
            "stairs",
            "Staircase",
            left,
            top + bottom * 0.42,
            right,
            bottom * 0.58,
        ),
    ]

    floor_plans = [
        {
            "level": 0,
            "name": "Ground Floor",
            "rooms": ground,
            "doors": [],
            "windows": [],
            "stairs": [],
        }
    ]

    if floors > 1:
        upper_top = h * 0.52
        bath_h = h * 0.18
        lower_h = h - upper_top - bath_h

        upper = [
            _room(
                "a-bedroom-2",
                "bedroom",
                "Bedroom 2",
                0,
                0,
                w / 2,
                upper_top,
                1,
            ),
            _room(
                "a-bedroom-3",
                "bedroom",
                "Bedroom 3",
                w / 2,
                0,
                w / 2,
                upper_top,
                1,
            ),
            _room(
                "a-bath-3",
                "bathroom",
                "Bathroom 3",
                0,
                upper_top,
                w / 2,
                bath_h,
                1,
            ),
            _room(
                "a-bath-4",
                "bathroom",
                "Bathroom 4",
                w / 2,
                upper_top,
                w / 2,
                bath_h,
                1,
            ),
            _room(
                "a-family",
                "living",
                "Family Lounge",
                0,
                upper_top + bath_h,
                w * 0.68,
                lower_h,
                1,
            ),
            _room(
                "a-stairs-upper",
                "stairs",
                "Staircase",
                w * 0.68,
                upper_top + bath_h,
                w * 0.32,
                lower_h,
                1,
            ),
        ]

        floor_plans.append(
            {
                "level": 1,
                "name": "First Floor",
                "rooms": upper,
                "doors": [],
                "windows": [],
                "stairs": [],
            }
        )

    return _base_plan(
        "candidate-a",
        "Balanced Family Plan",
        "balanced",
        w,
        h,
        bedrooms,
        bathrooms,
        floors,
        project,
        floor_plans,
    )


def _open_living_plan(
    w: float,
    h: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> dict[str, Any]:

    top = h * 0.60
    bottom = h - top

    open_w = w * 0.68
    kitchen_w = w - open_w

    bedroom_w = w * 0.52
    service_w = w - bedroom_w

    ground = [
        _room(
            "b-open-living",
            "living",
            "Open Living & Dining",
            0,
            0,
            open_w,
            top,
        ),
        _room(
            "b-kitchen",
            "kitchen",
            "Kitchen",
            open_w,
            0,
            kitchen_w,
            top,
        ),
        _room(
            "b-bedroom-1",
            "bedroom",
            "Bedroom 1",
            0,
            top,
            bedroom_w,
            bottom,
        ),
        _room(
            "b-bath-1",
            "bathroom",
            "Bathroom 1",
            bedroom_w,
            top,
            service_w / 2,
            bottom * 0.45,
        ),
        _room(
            "b-bath-2",
            "bathroom",
            "Bathroom 2",
            bedroom_w + service_w / 2,
            top,
            service_w / 2,
            bottom * 0.45,
        ),
        _room(
            "b-stairs",
            "stairs",
            "Staircase",
            bedroom_w,
            top + bottom * 0.45,
            service_w,
            bottom * 0.55,
        ),
    ]

    floor_plans = [
        {
            "level": 0,
            "name": "Ground Floor",
            "rooms": ground,
            "doors": [],
            "windows": [],
            "stairs": [],
        }
    ]

    if floors > 1:
        bed_h = h * 0.50
        bath_h = h * 0.18
        lounge_h = h - bed_h - bath_h

        upper = [
            _room(
                "b-bedroom-2",
                "bedroom",
                "Bedroom 2",
                0,
                0,
                w / 2,
                bed_h,
                1,
            ),
            _room(
                "b-bedroom-3",
                "bedroom",
                "Bedroom 3",
                w / 2,
                0,
                w / 2,
                bed_h,
                1,
            ),
            _room(
                "b-bath-3",
                "bathroom",
                "Bathroom 3",
                0,
                bed_h,
                w / 2,
                bath_h,
                1,
            ),
            _room(
                "b-bath-4",
                "bathroom",
                "Bathroom 4",
                w / 2,
                bed_h,
                w / 2,
                bath_h,
                1,
            ),
            _room(
                "b-family",
                "living",
                "Large Family Lounge",
                0,
                bed_h + bath_h,
                w * 0.72,
                lounge_h,
                1,
            ),
            _room(
                "b-stairs-upper",
                "stairs",
                "Staircase",
                w * 0.72,
                bed_h + bath_h,
                w * 0.28,
                lounge_h,
                1,
            ),
        ]

        floor_plans.append(
            {
                "level": 1,
                "name": "First Floor",
                "rooms": upper,
                "doors": [],
                "windows": [],
                "stairs": [],
            }
        )

    return _base_plan(
        "candidate-b",
        "Open Living Plan",
        "open_living",
        w,
        h,
        bedrooms,
        bathrooms,
        floors,
        project,
        floor_plans,
    )


def _privacy_plan(
    w: float,
    h: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> dict[str, Any]:

    top = h * 0.46
    bottom = h - top

    living_w = w * 0.52
    right_w = w - living_w

    ground = [
        _room(
            "c-living",
            "living",
            "Living Room",
            0,
            0,
            living_w,
            top,
        ),
        _room(
            "c-kitchen",
            "kitchen",
            "Kitchen",
            living_w,
            0,
            right_w,
            top * 0.50,
        ),
        _room(
            "c-dining",
            "dining",
            "Dining Room",
            living_w,
            top * 0.50,
            right_w,
            top * 0.50,
        ),
        _room(
            "c-bedroom-1",
            "bedroom",
            "Private Bedroom 1",
            0,
            top,
            w * 0.48,
            bottom,
        ),
        _room(
            "c-bath-1",
            "bathroom",
            "Bathroom 1",
            w * 0.48,
            top,
            w * 0.13,
            bottom * 0.42,
        ),
        _room(
            "c-bath-2",
            "bathroom",
            "Bathroom 2",
            w * 0.61,
            top,
            w * 0.13,
            bottom * 0.42,
        ),
        _room(
            "c-passage",
            "passage",
            "Passage",
            w * 0.48,
            top + bottom * 0.42,
            w * 0.26,
            bottom * 0.58,
        ),
        _room(
            "c-stairs",
            "stairs",
            "Staircase",
            w * 0.74,
            top,
            w * 0.26,
            bottom,
        ),
    ]

    floor_plans = [
        {
            "level": 0,
            "name": "Ground Floor",
            "rooms": ground,
            "doors": [],
            "windows": [],
            "stairs": [],
        }
    ]

    if floors > 1:
        upper_top = h * 0.52
        middle_w = w * 0.16
        bedroom_w = (w - middle_w) / 2
        lower_h = h - upper_top

        upper = [
            _room(
                "c-bedroom-2",
                "bedroom",
                "Bedroom 2",
                0,
                0,
                bedroom_w,
                upper_top,
                1,
            ),
            _room(
                "c-bath-3",
                "bathroom",
                "Bathroom 3",
                bedroom_w,
                0,
                middle_w,
                upper_top / 2,
                1,
            ),
            _room(
                "c-bath-4",
                "bathroom",
                "Bathroom 4",
                bedroom_w,
                upper_top / 2,
                middle_w,
                upper_top / 2,
                1,
            ),
            _room(
                "c-bedroom-3",
                "bedroom",
                "Bedroom 3",
                bedroom_w + middle_w,
                0,
                bedroom_w,
                upper_top,
                1,
            ),
            _room(
                "c-family",
                "living",
                "Quiet Family Lounge",
                0,
                upper_top,
                w * 0.68,
                lower_h,
                1,
            ),
            _room(
                "c-stairs-upper",
                "stairs",
                "Staircase",
                w * 0.68,
                upper_top,
                w * 0.32,
                lower_h,
                1,
            ),
        ]

        floor_plans.append(
            {
                "level": 1,
                "name": "First Floor",
                "rooms": upper,
                "doors": [],
                "windows": [],
                "stairs": [],
            }
        )

    return _base_plan(
        "candidate-c",
        "Privacy Focused Plan",
        "privacy",
        w,
        h,
        bedrooms,
        bathrooms,
        floors,
        project,
        floor_plans,
    )


def generate_structural_candidates(
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> list[dict[str, Any]]:

    if target_width <= 0 or target_height <= 0:
        raise ValueError(
            "Building dimensions must be positive."
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

    return [
        _balanced_plan(
            target_width,
            target_height,
            bedrooms,
            bathrooms,
            floors,
            project,
        ),
        _open_living_plan(
            target_width,
            target_height,
            bedrooms,
            bathrooms,
            floors,
            project,
        ),
        _privacy_plan(
            target_width,
            target_height,
            bedrooms,
            bathrooms,
            floors,
            project,
        ),
    ]


def generate_structural_plan(
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> dict[str, Any]:

    candidates = generate_structural_candidates(
        target_width,
        target_height,
        bedrooms,
        bathrooms,
        floors,
        project,
    )

    # Existing API still receives Candidate A
    # until we add the 3-plan selection endpoint.
    return candidates[0]