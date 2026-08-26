from __future__ import annotations

from math import ceil
from typing import Any


# ============================================================
# ZYNORA STRUCTURAL FLOOR-PLAN GENERATOR V2
# ============================================================
#
# Goal:
#   Generate architectural-looking, deterministic residential
#   layouts instead of the old "seven rectangles" templates.
#
# Contract preserved:
#   generate_structural_candidates(...)
#   generate_structural_plan(...)
#
# Output remains compatible with the existing floor-plan API:
#   rooms, floor_plans, doors, windows, furniture, boundary, ...
#
# Design principles:
#   - exact requested bedroom / bathroom / floor counts
#   - no room overlap
#   - every room remains inside the building
#   - meaningful public/private zoning
#   - shared-wall doors instead of doors floating in room centers
#   - exterior windows on rooms that actually touch an exterior wall
#   - three visibly different design strategies
# ============================================================


EPS = 0.05
MIN_ROOM_WIDTH = 6.0
MIN_ROOM_HEIGHT = 5.5


def _round(value: float) -> float:
    return round(float(value), 3)


def _room(
    room_id: str,
    room_type: str,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    floor_level: int = 0,
    zone: str = "",
) -> dict[str, Any]:
    width = max(float(width), 0.1)
    height = max(float(height), 0.1)

    return {
        "id": room_id,
        "type": room_type,
        "name": name,
        "x": _round(x),
        "y": _round(y),
        "width": _round(width),
        "height": _round(height),
        "area": _round(width * height),
        "floor_level": int(floor_level),
        "zone": zone,
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
    room_id: str | None = None,
    from_room_id: str | None = None,
    to_room_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": door_id,
        "type": door_type,
        "x": _round(x),
        "y": _round(y),
        "width": _round(width),
        "height": _round(height),
        "orientation": orientation,
        "floor_level": int(floor_level),
        **({"room_id": room_id} if room_id else {}),
        **({"from_room_id": from_room_id} if from_room_id else {}),
        **({"to_room_id": to_room_id} if to_room_id else {}),
    }


def _window(
    window_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    orientation: str,
    floor_level: int,
    room_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": window_id,
        "type": "window",
        "x": _round(x),
        "y": _round(y),
        "width": _round(width),
        "height": _round(height),
        "orientation": orientation,
        "floor_level": int(floor_level),
        **({"room_id": room_id} if room_id else {}),
    }


def _split_horizontal(
    prefix: str,
    room_type: str,
    name_prefix: str,
    x: float,
    y: float,
    width: float,
    height: float,
    count: int,
    floor_level: int,
    zone: str,
) -> list[dict[str, Any]]:
    """Split a rectangle into equal left-to-right rooms."""
    if count <= 0:
        return []

    count = int(count)
    out: list[dict[str, Any]] = []
    base = width / count

    for index in range(count):
        room_x = x + index * base
        room_w = base if index < count - 1 else x + width - room_x

        if name_prefix.lower().startswith("bedroom"):
            if index == 0:
                name = "Master Bedroom" if count > 1 else "Bedroom 1"
            else:
                name = f"Bedroom {index + 1}"
        else:
            name = (
                name_prefix
                if count == 1
                else f"{name_prefix} {index + 1}"
            )

        out.append(
            _room(
                f"{prefix}-{index + 1}",
                room_type,
                name,
                room_x,
                y,
                room_w,
                height,
                floor_level,
                zone,
            )
        )

    return out


def _split_vertical(
    prefix: str,
    room_type: str,
    name_prefix: str,
    x: float,
    y: float,
    width: float,
    height: float,
    count: int,
    floor_level: int,
    zone: str,
) -> list[dict[str, Any]]:
    """Split a rectangle into equal top-to-bottom rooms."""
    if count <= 0:
        return []

    count = int(count)
    out: list[dict[str, Any]] = []
    base = height / count

    for index in range(count):
        room_y = y + index * base
        room_h = base if index < count - 1 else y + height - room_y

        if room_type == "bathroom":
            name = (
                name_prefix
                if count == 1
                else f"{name_prefix} {index + 1}"
            )
        else:
            name = (
                name_prefix
                if count == 1
                else f"{name_prefix} {index + 1}"
            )

        out.append(
            _room(
                f"{prefix}-{index + 1}",
                room_type,
                name,
                x,
                room_y,
                width,
                room_h,
                floor_level,
                zone,
            )
        )

    return out


def _floor(
    level: int,
    rooms: list[dict[str, Any]],
) -> dict[str, Any]:
    names = {
        0: "Ground Floor",
        1: "First Floor",
        2: "Second Floor",
    }

    return {
        "level": level,
        "name": names.get(level, f"Floor {level + 1}"),
        "rooms": rooms,
        "doors": [],
        "windows": [],
        "stairs": [],
    }


def _safe_integer(value: Any, default: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _distribute(total: int, floors: int) -> list[int]:
    """Balanced distribution, with the first floor receiving the extra item."""
    total = max(0, int(total))
    floors = max(1, int(floors))

    base = total // floors
    remainder = total % floors

    return [
        base + (1 if index < remainder else 0)
        for index in range(floors)
    ]


def _ensure_first_floor_bedroom(
    bedroom_distribution: list[int],
    requested_bedrooms: int,
) -> list[int]:
    """Prefer one ground-floor bedroom for normal multi-floor homes."""
    if len(bedroom_distribution) <= 1:
        return bedroom_distribution

    if requested_bedrooms >= 2 and bedroom_distribution[0] == 0:
        donor = next(
            (
                index
                for index in range(1, len(bedroom_distribution))
                if bedroom_distribution[index] > 1
            ),
            None,
        )

        if donor is None:
            donor = next(
                (
                    index
                    for index in range(1, len(bedroom_distribution))
                    if bedroom_distribution[index] > 0
                ),
                None,
            )

        if donor is not None:
            bedroom_distribution[0] += 1
            bedroom_distribution[donor] -= 1

    return bedroom_distribution


def _distribute_bathrooms(
    bathrooms: int,
    floors: int,
    bedroom_distribution: list[int],
) -> list[int]:
    """Keep bathrooms close to the bedroom distribution while guaranteeing
    at least one bathroom on the ground floor for multi-floor homes.
    """
    result = _distribute(bathrooms, floors)

    if floors > 1 and bathrooms > 0 and result[0] == 0:
        donor = next(
            (
                index
                for index in range(1, floors)
                if result[index] > 1
            ),
            None,
        )

        if donor is None:
            donor = next(
                (
                    index
                    for index in range(1, floors)
                    if result[index] > 0
                ),
                None,
            )

        if donor is not None:
            result[0] = 1
            result[donor] -= 1

    # A bathroom is more useful on floors containing bedrooms.
    for index in range(floors):
        if bedroom_distribution[index] > 0 and result[index] == 0:
            donor = next(
                (
                    donor_index
                    for donor_index in range(floors)
                    if donor_index != index
                    and result[donor_index] > 1
                ),
                None,
            )

            if donor is not None:
                result[index] += 1
                result[donor] -= 1

    return result


def _public_zone(
    level: int,
    w: float,
    h: float,
    strategy: str,
) -> tuple[list[dict[str, Any]], float]:
    """Create the front/public band on the ground floor."""
    public_h = max(13.5, min(h * 0.43, h - 15.0))

    if strategy == "open_living":
        living_ratio = 0.68
        living_name = "Open Living & Dining"
    elif strategy == "privacy":
        living_ratio = 0.52
        living_name = "Living Room"
    else:
        living_ratio = 0.58
        living_name = "Living Room"

    living_w = w * living_ratio
    service_w = w - living_w

    rooms = [
        _room(
            f"{strategy}-ground-living",
            "living",
            living_name,
            0,
            0,
            living_w,
            public_h,
            level,
            "public",
        ),
        _room(
            f"{strategy}-ground-kitchen",
            "kitchen",
            "Kitchen",
            living_w,
            0,
            service_w,
            public_h * 0.55,
            level,
            "service",
        ),
        _room(
            f"{strategy}-ground-dining",
            "dining",
            "Dining Room",
            living_w,
            public_h * 0.55,
            service_w,
            public_h * 0.45,
            level,
            "public",
        ),
    ]

    return rooms, public_h


def _ground_floor(
    w: float,
    h: float,
    bedroom_count: int,
    bathroom_count: int,
    strategy: str,
    floor_level: int = 0,
) -> dict[str, Any]:
    """Ground-floor plan.

    Public rooms occupy the front. Bedrooms are pushed toward the private
    rear zone. Bathrooms, foyer and staircase form a service core.
    """
    rooms, public_h = _public_zone(
        floor_level,
        w,
        h,
        strategy,
    )

    lower_y = public_h
    lower_h = h - public_h

    if bedroom_count <= 0:
        bedroom_zone_w = 0.0
    elif bedroom_count == 1:
        bedroom_zone_w = w * (
            0.55 if strategy != "open_living" else 0.50
        )
    else:
        bedroom_zone_w = w * (
            0.72 if strategy == "open_living" else 0.76
        )

    if bedroom_count:
        rooms.extend(
            _split_horizontal(
                f"{strategy}-ground-bedroom",
                "bedroom",
                "Bedroom",
                0,
                lower_y,
                bedroom_zone_w,
                lower_h,
                bedroom_count,
                floor_level,
                "private",
            )
        )

    service_x = bedroom_zone_w
    service_w = max(w - service_x, 1.0)

    # Bathrooms sit immediately beside the private zone.
    # This creates a realistic service spine instead of random rectangles.
    if bathroom_count:
        bathroom_band_h = min(
            lower_h * 0.31,
            max(6.5, bathroom_count * 6.5),
        )

        rooms.extend(
            _split_horizontal(
                f"{strategy}-ground-bathroom",
                "bathroom",
                "Bathroom",
                service_x,
                lower_y,
                service_w,
                bathroom_band_h,
                bathroom_count,
                floor_level,
                "service",
            )
        )
    else:
        bathroom_band_h = 0.0

    service_y = lower_y + bathroom_band_h
    remaining_h = max(h - service_y, 0.0)

    if remaining_h > 0:
        if floor_level == 0:
            # Put foyer and staircase side-by-side at the rear so the
            # main entrance can open directly into the foyer.
            foyer_w = service_w * 0.52
            stair_w = service_w - foyer_w

            if service_w >= 8.0:
                rooms.append(
                    _room(
                        f"{strategy}-ground-foyer",
                        "foyer",
                        "Central Foyer",
                        service_x,
                        service_y,
                        foyer_w,
                        remaining_h,
                        floor_level,
                        "circulation",
                    )
                )

                rooms.append(
                    _room(
                        f"{strategy}-ground-stairs",
                        "stairs",
                        "Staircase",
                        service_x + foyer_w,
                        service_y,
                        stair_w,
                        remaining_h,
                        floor_level,
                        "circulation",
                    )
                )
            else:
                rooms.append(
                    _room(
                        f"{strategy}-ground-stairs",
                        "stairs",
                        "Staircase",
                        service_x,
                        service_y,
                        service_w,
                        remaining_h,
                        floor_level,
                        "circulation",
                    )
                )
        else:
            rooms.append(
                _room(
                    f"{strategy}-ground-stairs",
                    "stairs",
                    "Staircase",
                    service_x,
                    service_y,
                    service_w,
                    remaining_h,
                    floor_level,
                    "circulation",
                )
            )

    return _floor(floor_level, rooms)


def _upper_floor(
    w: float,
    h: float,
    bedroom_count: int,
    bathroom_count: int,
    strategy: str,
    floor_level: int,
) -> dict[str, Any]:
    """Upper-floor plan with bedrooms above and family/circulation below."""
    rooms: list[dict[str, Any]] = []

    if bedroom_count <= 0:
        bed_h = 0.0
    else:
        bed_h = max(14.0, min(h * 0.48, h - 14.0))

    used_bathrooms = 0

    # Three or more bedrooms benefit from a central bathroom/service core.
    if bedroom_count >= 3:
        core_w = w * 0.17
        side_w = (w - core_w) / 2

        left_count = ceil(bedroom_count / 2)
        right_count = bedroom_count - left_count

        if left_count:
            rooms.extend(
                _split_horizontal(
                    f"upper-{floor_level}-left-bedroom",
                    "bedroom",
                    "Bedroom",
                    0,
                    0,
                    side_w,
                    bed_h,
                    left_count,
                    floor_level,
                    "private",
                )
            )

        if right_count:
            rooms.extend(
                _split_horizontal(
                    f"upper-{floor_level}-right-bedroom",
                    "bedroom",
                    "Bedroom",
                    side_w + core_w,
                    0,
                    side_w,
                    bed_h,
                    right_count,
                    floor_level,
                    "private",
                )
            )

        core_bath_count = min(
            bathroom_count,
            max(1, int(bed_h // 6.5)),
        )

        if core_bath_count:
            rooms.extend(
                _split_vertical(
                    f"upper-{floor_level}-core-bath",
                    "bathroom",
                    "Bathroom",
                    side_w,
                    0,
                    core_w,
                    bed_h,
                    core_bath_count,
                    floor_level,
                    "service",
                )
            )
            used_bathrooms = core_bath_count

    elif bedroom_count > 0:
        rooms.extend(
            _split_horizontal(
                f"upper-{floor_level}-bedroom",
                "bedroom",
                "Bedroom",
                0,
                0,
                w,
                bed_h,
                bedroom_count,
                floor_level,
                "private",
            )
        )

    service_y = bed_h
    remaining_h = max(h - service_y, 0.0)

    remaining_bathrooms = max(
        0,
        bathroom_count - used_bathrooms,
    )

    if remaining_bathrooms and remaining_h > 0:
        bath_h = min(
            remaining_h * 0.42,
            max(6.5, remaining_bathrooms * 6.5),
        )

        rooms.extend(
            _split_horizontal(
                f"upper-{floor_level}-bath",
                "bathroom",
                "Bathroom",
                0,
                service_y,
                w,
                bath_h,
                remaining_bathrooms,
                floor_level,
                "service",
            )
        )

        service_y += bath_h
        remaining_h = h - service_y

    if remaining_h > 0:
        lounge_ratio = (
            0.68
            if strategy == "privacy"
            else 0.72
        )

        rooms.append(
            _room(
                f"upper-{floor_level}-family",
                "living",
                (
                    "Quiet Family Lounge"
                    if strategy == "privacy"
                    else "Family Lounge"
                ),
                0,
                service_y,
                w * lounge_ratio,
                remaining_h,
                floor_level,
                "family",
            )
        )

        rooms.append(
            _room(
                f"upper-{floor_level}-stairs",
                "stairs",
                "Staircase",
                w * lounge_ratio,
                service_y,
                w * (1.0 - lounge_ratio),
                remaining_h,
                floor_level,
                "circulation",
            )
        )

    return _floor(floor_level, rooms)


def _single_floor_plan(
    w: float,
    h: float,
    bedrooms: int,
    bathrooms: int,
    strategy: str,
) -> dict[str, Any]:
    """Compact one-floor family house.

    The bottom private band contains the exact requested bedrooms.
    A service strip below/alongside it contains bathrooms and circulation.
    """
    public_h = max(13.0, min(h * 0.40, h - 14.0))

    if strategy == "open_living":
        living_ratio = 0.68
        living_name = "Open Living & Dining"
    elif strategy == "privacy":
        living_ratio = 0.50
        living_name = "Living Room"
    else:
        living_ratio = 0.58
        living_name = "Living Room"

    living_w = w * living_ratio
    service_w = w - living_w

    rooms = [
        _room(
            f"{strategy}-living",
            "living",
            living_name,
            0,
            0,
            living_w,
            public_h,
            0,
            "public",
        ),
        _room(
            f"{strategy}-kitchen",
            "kitchen",
            "Kitchen",
            living_w,
            0,
            service_w,
            public_h * 0.55,
            0,
            "service",
        ),
        _room(
            f"{strategy}-dining",
            "dining",
            "Dining Room",
            living_w,
            public_h * 0.55,
            service_w,
            public_h * 0.45,
            0,
            "public",
        ),
    ]

    private_y = public_h
    private_h = h - private_y

    # Bedroom band gets most of the rear area.
    bedroom_h = max(
        13.0,
        min(private_h * 0.68, private_h - 6.0),
    )

    rooms.extend(
        _split_horizontal(
            f"{strategy}-bedrooms",
            "bedroom",
            "Bedroom",
            0,
            private_y,
            w,
            bedroom_h,
            bedrooms,
            0,
            "private",
        )
    )

    service_y = private_y + bedroom_h
    service_h = h - service_y

    if bathrooms:
        rooms.extend(
            _split_horizontal(
                f"{strategy}-bathrooms",
                "bathroom",
                "Bathroom",
                0,
                service_y,
                w,
                service_h,
                bathrooms,
                0,
                "service",
            )
        )

    return _floor(0, rooms)


# ============================================================
# OPENING GENERATION
# ============================================================


def _touching(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, float, float] | None:
    """Return shared wall orientation and overlap interval.

    Result:
      ("horizontal", start, end) or ("vertical", start, end)
    """
    ax1 = float(a["x"])
    ay1 = float(a["y"])
    ax2 = ax1 + float(a["width"])
    ay2 = ay1 + float(a["height"])

    bx1 = float(b["x"])
    by1 = float(b["y"])
    bx2 = bx1 + float(b["width"])
    by2 = by1 + float(b["height"])

    # A bottom wall touches B top wall.
    if abs(ay2 - by1) <= EPS:
        start = max(ax1, bx1)
        end = min(ax2, bx2)
        if end - start > 2.5:
            return "horizontal", start, end

    # B bottom wall touches A top wall.
    if abs(by2 - ay1) <= EPS:
        start = max(ax1, bx1)
        end = min(ax2, bx2)
        if end - start > 2.5:
            return "horizontal", start, end

    # A right wall touches B left wall.
    if abs(ax2 - bx1) <= EPS:
        start = max(ay1, by1)
        end = min(ay2, by2)
        if end - start > 2.5:
            return "vertical", start, end

    # B right wall touches A left wall.
    if abs(bx2 - ax1) <= EPS:
        start = max(ay1, by1)
        end = min(ay2, by2)
        if end - start > 2.5:
            return "vertical", start, end

    return None


def _preferred_room(room: dict[str, Any]) -> bool:
    return room.get("type") in {
        "bedroom",
        "bathroom",
        "kitchen",
        "dining",
        "living",
        "foyer",
    }


def _generate_internal_doors(
    rooms: list[dict[str, Any]],
    level: int,
) -> list[dict[str, Any]]:
    doors: list[dict[str, Any]] = []
    connected: set[str] = set()
    door_index = 1

    # Prefer private/service rooms connecting to public/circulation rooms.
    priority_types = {
        "bedroom",
        "bathroom",
        "kitchen",
        "dining",
        "foyer",
        "living",
    }

    pairs: list[tuple[int, int, float, str, float, float]] = []

    for index, room_a in enumerate(rooms):
        for other_index in range(index + 1, len(rooms)):
            room_b = rooms[other_index]

            if room_a.get("floor_level") != level:
                continue
            if room_b.get("floor_level") != level:
                continue

            shared = _touching(room_a, room_b)
            if not shared:
                continue

            orientation, start, end = shared
            length = end - start

            score = length
            if room_a.get("type") in priority_types:
                score += 3
            if room_b.get("type") in priority_types:
                score += 3
            if room_a.get("type") == "stairs" or room_b.get("type") == "stairs":
                score -= 2

            pairs.append(
                (
                    index,
                    other_index,
                    score,
                    orientation,
                    start,
                    end,
                )
            )

    pairs.sort(key=lambda item: item[2], reverse=True)

    for (
        index,
        other_index,
        _score,
        orientation,
        start,
        end,
    ) in pairs:
        room_a = rooms[index]
        room_b = rooms[other_index]

        # Avoid putting many doors on the same small room.
        a_id = str(room_a["id"])
        b_id = str(room_b["id"])

        if (
            a_id in connected
            and b_id in connected
        ):
            continue

        # Large rooms may have multiple connections, but a bathroom or
        # bedroom only needs one primary entrance in this conceptual model.
        if room_a.get("type") in {"bedroom", "bathroom"} and a_id in connected:
            continue
        if room_b.get("type") in {"bedroom", "bathroom"} and b_id in connected:
            continue

        door_width = min(
            3.2,
            max(2.7, (end - start) * 0.28),
        )

        center = (start + end) / 2

        if orientation == "horizontal":
            # Find the actual shared y coordinate.
            ay_bottom = float(room_a["y"]) + float(room_a["height"])
            by_bottom = float(room_b["y"]) + float(room_b["height"])

            if abs(ay_bottom - float(room_b["y"])) <= EPS:
                wall_y = float(room_b["y"])
            else:
                wall_y = float(room_a["y"])

            door = _door(
                f"door-{level}-{door_index}",
                center - door_width / 2,
                wall_y - 0.15,
                door_width,
                0.30,
                "horizontal",
                level,
                room_id=a_id,
                from_room_id=a_id,
                to_room_id=b_id,
            )
        else:
            ax_right = float(room_a["x"]) + float(room_a["width"])

            if abs(ax_right - float(room_b["x"])) <= EPS:
                wall_x = float(room_b["x"])
            else:
                wall_x = float(room_a["x"])

            door = _door(
                f"door-{level}-{door_index}",
                wall_x - 0.15,
                center - door_width / 2,
                0.30,
                door_width,
                "vertical",
                level,
                room_id=a_id,
                from_room_id=a_id,
                to_room_id=b_id,
            )

        doors.append(door)
        door_index += 1

        # Mark only enclosed rooms as connected.
        if room_a.get("type") in {"bedroom", "bathroom"}:
            connected.add(a_id)
        if room_b.get("type") in {"bedroom", "bathroom"}:
            connected.add(b_id)

    return doors


def _generate_exterior_windows(
    rooms: list[dict[str, Any]],
    building_width: float,
    building_height: float,
    level: int,
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    window_index = 1

    for room in rooms:
        if room.get("floor_level") != level:
            continue

        room_type = room.get("type")
        if room_type in {"stairs", "foyer", "passage"}:
            continue

        x = float(room["x"])
        y = float(room["y"])
        width = float(room["width"])
        height = float(room["height"])

        # Bedrooms get generous windows.
        if room_type == "bedroom":
            factor = 0.42
        elif room_type == "living":
            factor = 0.34
        elif room_type in {"kitchen", "dining"}:
            factor = 0.28
        else:
            factor = 0.24

        # Top exterior wall.
        if abs(y) <= EPS and width >= MIN_ROOM_WIDTH:
            ww = min(6.5, max(3.0, width * factor))
            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    x + width / 2 - ww / 2,
                    0,
                    ww,
                    0.22,
                    "horizontal",
                    level,
                    room.get("id"),
                )
            )
            window_index += 1

        # Bottom exterior wall.
        if (
            abs((y + height) - building_height) <= EPS
            and width >= MIN_ROOM_WIDTH
        ):
            ww = min(6.5, max(3.0, width * factor))
            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    x + width / 2 - ww / 2,
                    building_height - 0.22,
                    ww,
                    0.22,
                    "horizontal",
                    level,
                    room.get("id"),
                )
            )
            window_index += 1

        # Left exterior wall.
        if abs(x) <= EPS and height >= MIN_ROOM_HEIGHT:
            wh = min(6.5, max(3.0, height * factor))
            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    0,
                    y + height / 2 - wh / 2,
                    0.22,
                    wh,
                    "vertical",
                    level,
                    room.get("id"),
                )
            )
            window_index += 1

        # Right exterior wall.
        if (
            abs((x + width) - building_width) <= EPS
            and height >= MIN_ROOM_HEIGHT
        ):
            wh = min(6.5, max(3.0, height * factor))
            windows.append(
                _window(
                    f"window-{level}-{window_index}",
                    building_width - 0.22,
                    y + height / 2 - wh / 2,
                    0.22,
                    wh,
                    "vertical",
                    level,
                    room.get("id"),
                )
            )
            window_index += 1

    return windows


def _generate_openings(
    floor: dict[str, Any],
    building_width: float,
    building_height: float,
) -> None:
    level = int(floor["level"])
    rooms = floor["rooms"]

    doors = _generate_internal_doors(
        rooms,
        level,
    )

    # Main entrance belongs to the public living/foyer side.
    if level == 0:
        foyer_rooms = [
            room
            for room in rooms
            if room.get("type") == "foyer"
        ]
        public_rooms = [
            room
            for room in rooms
            if room.get("type") in {"living", "foyer"}
        ]

        if foyer_rooms:
            entry_room = foyer_rooms[0]
        elif public_rooms:
            entry_room = public_rooms[0]
        else:
            entry_room = None

        if entry_room:
            ex = float(entry_room["x"])
            ew = float(entry_room["width"])

            entry_width = min(4.0, max(3.2, ew * 0.20))
            entry_x = ex + ew * 0.50 - entry_width / 2

            # Main entrance is placed on the bottom exterior edge if the
            # selected public room reaches the bottom; otherwise use the
            # closest public room's bottom edge.
            entry_y = (
                building_height - 0.30
                if abs(
                    float(entry_room["y"])
                    + float(entry_room["height"])
                    - building_height
                ) <= EPS
                else float(entry_room["y"])
                + float(entry_room["height"])
                - 0.15
            )

            doors.insert(
                0,
                _door(
                    "main-entry-door",
                    entry_x,
                    entry_y,
                    entry_width,
                    0.30,
                    "horizontal",
                    0,
                    door_type="main",
                    room_id=entry_room.get("id"),
                    to_room_id=entry_room.get("id"),
                ),
            )

    windows = _generate_exterior_windows(
        rooms,
        building_width,
        building_height,
        level,
    )

    floor["doors"] = doors
    floor["windows"] = windows


# ============================================================
# PLAN FINALIZATION
# ============================================================


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
    for floor in floor_plans:
        _generate_openings(
            floor,
            target_width,
            target_height,
        )

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
        "source": "ZYNORA Architectural Generator V2",
        "name": project.get("name", "Generated Home"),
        "width": _round(target_width),
        "height": _round(target_height),
        "aspect_ratio": _round(target_width / target_height),
        "bedrooms": int(bedrooms),
        "bathrooms": int(bathrooms),
        "floors": int(floors),
        "room_count": len(rooms),
        "rooms": rooms,
        "floor_plans": floor_plans,
        "floors_data": floor_plans,
        "doors": doors,
        "windows": windows,
        # Furniture is intentionally left to the existing
        # furniture_generator.py pipeline.
        "furniture": [],
        "boundary": [
            [0, 0],
            [_round(target_width), 0],
            [_round(target_width), _round(target_height)],
            [0, _round(target_height)],
        ],
        "match_type": "generated",
        "requires_structural_generation": False,
        "generated_from_requirements": True,
        "generator_version": "2.0",
    }


def _build_candidate(
    candidate_id: str,
    title: str,
    strategy: str,
    w: float,
    h: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> dict[str, Any]:
    floors = max(1, floors)

    bedroom_distribution = _distribute(
        bedrooms,
        floors,
    )
    bedroom_distribution = _ensure_first_floor_bedroom(
        bedroom_distribution,
        bedrooms,
    )

    bathroom_distribution = _distribute_bathrooms(
        bathrooms,
        floors,
        bedroom_distribution,
    )

    floor_plans: list[dict[str, Any]] = []

    if floors == 1:
        floor_plans.append(
            _single_floor_plan(
                w,
                h,
                bedrooms,
                bathrooms,
                strategy,
            )
        )
    else:
        # Ground floor.
        floor_plans.append(
            _ground_floor(
                w,
                h,
                bedroom_distribution[0],
                bathroom_distribution[0],
                strategy,
                0,
            )
        )

        # Upper floors.
        for level in range(1, floors):
            floor_plans.append(
                _upper_floor(
                    w,
                    h,
                    bedroom_distribution[level],
                    bathroom_distribution[level],
                    strategy,
                    level,
                )
            )

    return _base_plan(
        candidate_id,
        title,
        strategy,
        w,
        h,
        bedrooms,
        bathrooms,
        floors,
        project,
        floor_plans,
    )


# ============================================================
# PUBLIC API
# ============================================================


def generate_structural_candidates(
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate three architecturally distinct candidates.

    The old generator hard-coded one geometry for each option and ignored
    most requested counts. V2 keeps the three-option contract while making
    the room program adaptive to the actual project.
    """
    w = float(target_width)
    h = float(target_height)

    bedrooms = _safe_integer(bedrooms, 3)
    bathrooms = _safe_integer(bathrooms, 1)
    floors = _safe_integer(floors, 1)

    if w <= 0 or h <= 0:
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
        _build_candidate(
            "candidate-a",
            "Balanced Family Plan",
            "balanced",
            w,
            h,
            bedrooms,
            bathrooms,
            floors,
            project,
        ),
        _build_candidate(
            "candidate-b",
            "Open Living Plan",
            "open_living",
            w,
            h,
            bedrooms,
            bathrooms,
            floors,
            project,
        ),
        _build_candidate(
            "candidate-c",
            "Privacy Focused Plan",
            "privacy",
            w,
            h,
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
    """Backward-compatible single-plan API."""
    candidates = generate_structural_candidates(
        target_width=target_width,
        target_height=target_height,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floors=floors,
        project=project,
    )

    return candidates[0]


__all__ = [
    "generate_structural_candidates",
    "generate_structural_plan",
]
