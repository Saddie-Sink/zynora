from typing import Any


TOLERANCE = 0.05


def get_room_bounds(
    room: dict[str, Any],
) -> tuple[float, float, float, float]:
    left = float(room.get("x", 0))
    top = float(room.get("y", 0))

    width = float(room.get("width", 0))
    height = float(room.get("height", 0))

    right = left + width
    bottom = top + height

    return left, top, right, bottom


def rooms_overlap(
    room_a: dict[str, Any],
    room_b: dict[str, Any],
) -> bool:
    (
        a_left,
        a_top,
        a_right,
        a_bottom,
    ) = get_room_bounds(room_a)

    (
        b_left,
        b_top,
        b_right,
        b_bottom,
    ) = get_room_bounds(room_b)

    return (
        a_left < b_right - TOLERANCE
        and a_right > b_left + TOLERANCE
        and a_top < b_bottom - TOLERANCE
        and a_bottom > b_top + TOLERANCE
    )


def validate_plan(
    plan: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    try:
        building_width = float(
            plan.get("width", 0)
        )

        building_height = float(
            plan.get("height", 0)
        )
    except (TypeError, ValueError):
        return [
            "The building dimensions are invalid."
        ]

    if building_width <= 0:
        errors.append(
            "Building width must be greater "
            "than zero."
        )

    if building_height <= 0:
        errors.append(
            "Building height must be greater "
            "than zero."
        )

    rooms = plan.get("rooms", [])

    if not isinstance(rooms, list):
        errors.append(
            "Rooms must be provided as a list."
        )
        return errors

    if not rooms:
        errors.append(
            "The floor plan does not contain "
            "any rooms."
        )

    for room in rooms:
        if not isinstance(room, dict):
            errors.append(
                "A room entry is invalid."
            )
            continue

        room_id = str(
            room.get(
                "id",
                "unknown-room",
            )
        )

        try:
            x = float(room.get("x", 0))
            y = float(room.get("y", 0))
            width = float(
                room.get("width", 0)
            )
            height = float(
                room.get("height", 0)
            )
        except (TypeError, ValueError):
            errors.append(
                f"{room_id} has invalid coordinates."
            )
            continue

        if width <= 0:
            errors.append(
                f"{room_id} has an invalid width."
            )

        if height <= 0:
            errors.append(
                f"{room_id} has an invalid height."
            )

        if x < -TOLERANCE:
            errors.append(
                f"{room_id} starts outside "
                "the building width."
            )

        if y < -TOLERANCE:
            errors.append(
                f"{room_id} starts outside "
                "the building height."
            )

        if (
            x + width
            > building_width + TOLERANCE
        ):
            errors.append(
                f"{room_id} extends past "
                "the building width."
            )

        if (
            y + height
            > building_height + TOLERANCE
        ):
            errors.append(
                f"{room_id} extends past "
                "the building height."
            )

    source = str(
        plan.get("source", "")
    ).lower()

    # HouseExpo uses semantic bounding boxes.
    # Some categories can overlap, so strict room
    # overlap validation is disabled for this source.
    if source != "houseexpo":
        for index, room_a in enumerate(rooms):
            if not isinstance(room_a, dict):
                continue

            for room_b in rooms[index + 1:]:
                if not isinstance(room_b, dict):
                    continue

                floor_a = int(
                    room_a.get("floor_level", 0)
                )

                floor_b = int(
                    room_b.get("floor_level", 0)
                )

                # Rooms on different floors may occupy
                # the same X/Y coordinates.
                if floor_a != floor_b:
                    continue

                if rooms_overlap(
                    room_a,
                    room_b,
                ):
                    errors.append(
                        f"{room_a.get('id')} overlaps "
                        f"{room_b.get('id')}."
                    )

    return errors

def validate_requirements(
    plan: dict[str, Any],
    requested_bedrooms: int,
    requested_bathrooms: int,
    requested_floors: int,
) -> list[str]:
    errors: list[str] = []

    try:
        actual_bedrooms = int(
            plan.get("bedrooms", 0)
        )
        actual_bathrooms = int(
            plan.get("bathrooms", 0)
        )
        actual_floors = int(
            plan.get("floors", 1)
        )
    except (TypeError, ValueError):
        return [
            "The plan contains invalid requirement metadata."
        ]

    if actual_bedrooms != requested_bedrooms:
        errors.append(
            "Bedroom requirement mismatch: "
            f"requested {requested_bedrooms}, "
            f"plan contains {actual_bedrooms}."
        )

    if actual_bathrooms != requested_bathrooms:
        errors.append(
            "Bathroom requirement mismatch: "
            f"requested {requested_bathrooms}, "
            f"plan contains {actual_bathrooms}."
        )

    if actual_floors != requested_floors:
        errors.append(
            "Floor requirement mismatch: "
            f"requested {requested_floors}, "
            f"plan contains {actual_floors}."
        )

    return errors