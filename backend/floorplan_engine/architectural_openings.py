from typing import Any


EPSILON = 0.05


def _round(value: float) -> float:
    return round(float(value), 3)


def _overlap_1d(
    a1: float,
    a2: float,
    b1: float,
    b2: float,
) -> tuple[float, float, float]:
    start = max(a1, b1)
    end = min(a2, b2)

    return (
        start,
        end,
        max(0.0, end - start),
    )


def _room_edges(
    room: dict[str, Any],
) -> dict[str, float]:
    x = float(room["x"])
    y = float(room["y"])
    width = float(room["width"])
    height = float(room["height"])

    return {
        "left": x,
        "right": x + width,
        "top": y,
        "bottom": y + height,
    }


def find_shared_wall(
    room_a: dict[str, Any],
    room_b: dict[str, Any],
) -> dict[str, Any] | None:
    a = _room_edges(room_a)
    b = _room_edges(room_b)

    # A right touches B left
    if abs(a["right"] - b["left"]) <= EPSILON:
        start, end, length = _overlap_1d(
            a["top"],
            a["bottom"],
            b["top"],
            b["bottom"],
        )

        if length > 1.5:
            return {
                "orientation": "vertical",
                "x": a["right"],
                "y1": start,
                "y2": end,
                "length": length,
            }

    # A left touches B right
    if abs(a["left"] - b["right"]) <= EPSILON:
        start, end, length = _overlap_1d(
            a["top"],
            a["bottom"],
            b["top"],
            b["bottom"],
        )

        if length > 1.5:
            return {
                "orientation": "vertical",
                "x": a["left"],
                "y1": start,
                "y2": end,
                "length": length,
            }

    # A bottom touches B top
    if abs(a["bottom"] - b["top"]) <= EPSILON:
        start, end, length = _overlap_1d(
            a["left"],
            a["right"],
            b["left"],
            b["right"],
        )

        if length > 1.5:
            return {
                "orientation": "horizontal",
                "y": a["bottom"],
                "x1": start,
                "x2": end,
                "length": length,
            }

    # A top touches B bottom
    if abs(a["top"] - b["bottom"]) <= EPSILON:
        start, end, length = _overlap_1d(
            a["left"],
            a["right"],
            b["left"],
            b["right"],
        )

        if length > 1.5:
            return {
                "orientation": "horizontal",
                "y": a["top"],
                "x1": start,
                "x2": end,
                "length": length,
            }

    return None


def build_adjacency_graph(
    rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    adjacency: list[dict[str, Any]] = []

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            room_a = rooms[i]
            room_b = rooms[j]

            shared = find_shared_wall(
                room_a,
                room_b,
            )

            if not shared:
                continue

            adjacency.append(
                {
                    "room_a_id": room_a["id"],
                    "room_b_id": room_b["id"],
                    "room_a_type": room_a.get("type"),
                    "room_b_type": room_b.get("type"),
                    "shared_wall": shared,
                }
            )

    return adjacency


def _door_width(
    room_a: dict[str, Any],
    room_b: dict[str, Any],
) -> float:
    types = {
        str(room_a.get("type")),
        str(room_b.get("type")),
    }

    if "passage" in types:
        return 3.2

    if "living" in types:
        return 3.5

    if "bedroom" in types:
        return 3.0

    if "bathroom" in types:
        return 2.8

    if "kitchen" in types:
        return 3.0

    if "stairs" in types:
        return 3.2

    return 3.0


def _should_connect(
    room_a: dict[str, Any],
    room_b: dict[str, Any],
) -> bool:
    type_a = str(room_a.get("type"))
    type_b = str(room_b.get("type"))

    pair = frozenset(
        {
            type_a,
            type_b,
        }
    )

    allowed_pairs = {
        frozenset({"living", "dining"}),
        frozenset({"living", "passage"}),
        frozenset({"dining", "kitchen"}),
        frozenset({"dining", "passage"}),
        frozenset({"kitchen", "passage"}),
        frozenset({"bedroom", "passage"}),
        frozenset({"bathroom", "passage"}),
        frozenset({"stairs", "passage"}),
        frozenset({"living", "stairs"}),
        frozenset({"living", "balcony"}),
        frozenset({"passage", "balcony"}),
    }

    # Allow bedroom-bathroom only when there is no passage
    # and they directly share a useful wall.
    if pair == frozenset(
        {
            "bedroom",
            "bathroom",
        }
    ):
        return True

    return pair in allowed_pairs


def generate_internal_doors(
    floor: dict[str, Any],
) -> list[dict[str, Any]]:
    rooms = list(
        floor.get(
            "rooms",
            [],
        )
    )

    adjacency = build_adjacency_graph(
        rooms
    )

    room_map = {
        room["id"]: room
        for room in rooms
    }

    doors: list[dict[str, Any]] = []

    door_index = 1

    for edge in adjacency:
        room_a = room_map[
            edge["room_a_id"]
        ]

        room_b = room_map[
            edge["room_b_id"]
        ]

        if not _should_connect(
            room_a,
            room_b,
        ):
            continue

        wall = edge["shared_wall"]

        width = _door_width(
            room_a,
            room_b,
        )

        # Keep some solid wall on both sides.
        usable = (
            wall["length"] - 1.2
        )

        if usable < 2.4:
            continue

        width = min(
            width,
            usable,
        )

        if (
            wall["orientation"]
            == "vertical"
        ):
            centre = (
                wall["y1"]
                + wall["y2"]
            ) / 2

            door = {
                "id": (
                    f"door-{floor['level']}-"
                    f"{door_index}"
                ),
                "type": "internal",
                "x": _round(
                    wall["x"] - 0.15
                ),
                "y": _round(
                    centre - width / 2
                ),
                "width": 0.3,
                "height": _round(width),
                "orientation": "vertical",
                "floor_level": floor["level"],
                "from_room_id": room_a["id"],
                "to_room_id": room_b["id"],
            }

        else:
            centre = (
                wall["x1"]
                + wall["x2"]
            ) / 2

            door = {
                "id": (
                    f"door-{floor['level']}-"
                    f"{door_index}"
                ),
                "type": "internal",
                "x": _round(
                    centre - width / 2
                ),
                "y": _round(
                    wall["y"] - 0.15
                ),
                "width": _round(width),
                "height": 0.3,
                "orientation": "horizontal",
                "floor_level": floor["level"],
                "from_room_id": room_a["id"],
                "to_room_id": room_b["id"],
            }

        doors.append(
            door
        )

        door_index += 1

    return doors


def _room_touches_boundary(
    room: dict[str, Any],
    width: float,
    height: float,
) -> list[str]:
    edges = _room_edges(
        room
    )

    sides: list[str] = []

    if abs(edges["left"]) <= EPSILON:
        sides.append("left")

    if abs(edges["right"] - width) <= EPSILON:
        sides.append("right")

    if abs(edges["top"]) <= EPSILON:
        sides.append("top")

    if abs(edges["bottom"] - height) <= EPSILON:
        sides.append("bottom")

    return sides


def generate_windows(
    floor: dict[str, Any],
    width: float,
    height: float,
) -> list[dict[str, Any]]:
    windows: list[
        dict[str, Any]
    ] = []

    window_index = 1

    habitable_types = {
        "living",
        "dining",
        "kitchen",
        "bedroom",
        "office",
    }

    for room in floor.get(
        "rooms",
        [],
    ):
        room_type = str(
            room.get(
                "type",
                "",
            )
        )

        if room_type not in habitable_types:
            continue

        sides = _room_touches_boundary(
            room,
            width,
            height,
        )

        if not sides:
            continue

        room_x = float(room["x"])
        room_y = float(room["y"])
        room_w = float(room["width"])
        room_h = float(room["height"])

        # Prefer only one main window per room for now.
        side = max(
            sides,
            key=lambda item: (
                room_w
                if item in {"top", "bottom"}
                else room_h
            ),
        )

        if side in {
            "top",
            "bottom",
        }:
            win_w = min(
                6.0,
                max(
                    3.0,
                    room_w * 0.32,
                ),
            )

            x = (
                room_x
                + room_w / 2
                - win_w / 2
            )

            y = (
                0
                if side == "top"
                else height - 0.2
            )

            windows.append(
                {
                    "id": (
                        f"window-{floor['level']}-"
                        f"{window_index}"
                    ),
                    "x": _round(x),
                    "y": _round(y),
                    "width": _round(win_w),
                    "height": 0.2,
                    "orientation": "horizontal",
                    "floor_level": floor["level"],
                    "room_id": room["id"],
                }
            )

        else:
            win_h = min(
                6.0,
                max(
                    3.0,
                    room_h * 0.32,
                ),
            )

            x = (
                0
                if side == "left"
                else width - 0.2
            )

            y = (
                room_y
                + room_h / 2
                - win_h / 2
            )

            windows.append(
                {
                    "id": (
                        f"window-{floor['level']}-"
                        f"{window_index}"
                    ),
                    "x": _round(x),
                    "y": _round(y),
                    "width": 0.2,
                    "height": _round(win_h),
                    "orientation": "vertical",
                    "floor_level": floor["level"],
                    "room_id": room["id"],
                }
            )

        window_index += 1

    return windows


def generate_main_entrance(
    floor: dict[str, Any],
    width: float,
    height: float,
    road_facing: str | None,
) -> dict[str, Any] | None:
    if floor.get("level") != 0:
        return None

    facing = str(
        road_facing or "North"
    ).lower()

    entrance_width = min(
        4.0,
        width * 0.12,
    )

    # In the current coordinate system:
    # top = North
    # right = East
    # bottom = South
    # left = West

    if facing == "south":
        return {
            "id": "main-entry-door",
            "type": "main",
            "x": _round(
                width / 2
                - entrance_width / 2
            ),
            "y": _round(
                height - 0.3
            ),
            "width": _round(
                entrance_width
            ),
            "height": 0.3,
            "orientation": "horizontal",
            "floor_level": 0,
        }

    if facing == "east":
        return {
            "id": "main-entry-door",
            "type": "main",
            "x": _round(
                width - 0.3
            ),
            "y": _round(
                height / 2
                - entrance_width / 2
            ),
            "width": 0.3,
            "height": _round(
                entrance_width
            ),
            "orientation": "vertical",
            "floor_level": 0,
        }

    if facing == "west":
        return {
            "id": "main-entry-door",
            "type": "main",
            "x": 0,
            "y": _round(
                height / 2
                - entrance_width / 2
            ),
            "width": 0.3,
            "height": _round(
                entrance_width
            ),
            "orientation": "vertical",
            "floor_level": 0,
        }

    # Default North.
    return {
        "id": "main-entry-door",
        "type": "main",
        "x": _round(
            width / 2
            - entrance_width / 2
        ),
        "y": 0,
        "width": _round(
            entrance_width
        ),
        "height": 0.3,
        "orientation": "horizontal",
        "floor_level": 0,
    }


def apply_architectural_openings(
    plan: dict[str, Any],
) -> dict[str, Any]:
    width = float(
        plan.get(
            "width",
            0,
        )
    )

    height = float(
        plan.get(
            "height",
            0,
        )
    )

    requirements = plan.get(
        "requirements",
        {},
    )

    road_facing = (
        requirements.get(
            "site",
            {},
        ).get(
            "road_facing"
        )
    )

    all_doors: list[
        dict[str, Any]
    ] = []

    all_windows: list[
        dict[str, Any]
    ] = []

    for floor in plan.get(
        "floor_plans",
        [],
    ):
        doors = generate_internal_doors(
            floor
        )

        if floor.get("level") == 0:
            entrance = generate_main_entrance(
                floor,
                width,
                height,
                road_facing,
            )

            if entrance:
                doors.insert(
                    0,
                    entrance,
                )

        windows = generate_windows(
            floor,
            width,
            height,
        )

        floor["doors"] = doors
        floor["windows"] = windows

        all_doors.extend(
            doors
        )

        all_windows.extend(
            windows
        )

    plan["doors"] = all_doors
    plan["windows"] = all_windows

    plan[
        "opening_generation_version"
    ] = "architectural-openings-v1"

    return plan