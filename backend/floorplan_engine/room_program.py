from typing import Any


def _space(
    space_id: str,
    space_type: str,
    name: str,
    floor_preference: str = "any",
    priority: str = "required",
    accessible: bool = False,
    min_area: float | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """
    Create one normalized space requirement.

    floor_preference:
        ground  -> should be on ground floor
        upper   -> should be above ground floor
        any     -> generator may decide

    priority:
        required
        preferred
        optional
    """

    return {
        "id": space_id,
        "type": space_type,
        "name": name,
        "floor_preference": floor_preference,
        "priority": priority,
        "accessible": accessible,
        "min_area": min_area,
        "notes": notes,
    }


def build_room_program(
    requirements: dict[str, Any],
) -> dict[str, Any]:

    hard = requirements.get(
        "hard_constraints",
        {},
    )

    family = requirements.get(
        "family",
        {},
    )

    required = requirements.get(
        "required_spaces",
        {},
    )

    accessibility = requirements.get(
        "accessibility",
        {},
    )

    outdoor = requirements.get(
        "outdoor",
        {},
    )

    preferences = requirements.get(
        "preferences",
        {},
    )

    # ---------------------------------
    # BASIC COUNTS
    # ---------------------------------

    bedrooms = int(
        hard.get("bedrooms", 1)
    )

    bathrooms = int(
        hard.get("bathrooms", 1)
    )

    floors = int(
        hard.get("floors", 1)
    )

    family_size = int(
        family.get("size", bedrooms)
    )

    children = int(
        family.get("children", 0)
    )

    seniors = int(
        family.get(
            "senior_citizens",
            0,
        )
    )

    # ---------------------------------
    # ACCESSIBILITY DECISIONS
    # ---------------------------------

    ground_bedroom_required = bool(
        accessibility.get(
            "ground_floor_bedroom",
            False,
        )
    )

    accessible_bathroom_required = bool(
        accessibility.get(
            "accessible_bathroom",
            False,
        )
    )

    wheelchair_friendly = bool(
        accessibility.get(
            "wheelchair_friendly",
            False,
        )
    )

    entrance_ramp = bool(
        accessibility.get(
            "entrance_ramp",
            False,
        )
    )

    # ---------------------------------
    # INTERNAL SPACES
    # ---------------------------------

    spaces: list[dict[str, Any]] = []

    # Living room
    spaces.append(
        _space(
            "living-1",
            "living",
            "Living Room",
            floor_preference="ground",
            min_area=180,
        )
    )

    # Dining
    spaces.append(
        _space(
            "dining-1",
            "dining",
            "Dining Area",
            floor_preference="ground",
            min_area=100,
        )
    )

    # Kitchen
    spaces.append(
        _space(
            "kitchen-1",
            "kitchen",
            "Kitchen",
            floor_preference="ground",
            min_area=100,
        )
    )

    # ---------------------------------
    # BEDROOMS
    # ---------------------------------

    for index in range(bedrooms):

        bedroom_number = index + 1

        if (
            bedroom_number == 1
            and ground_bedroom_required
        ):
            floor_preference = "ground"

            if seniors > 0:
                bedroom_name = (
                    "Senior Bedroom"
                )
            else:
                bedroom_name = (
                    "Ground Floor Bedroom"
                )

            accessible = True

        elif (
            floors > 1
            and bedroom_number > 1
        ):
            floor_preference = "upper"
            accessible = False

            bedroom_name = (
                f"Bedroom {bedroom_number}"
            )

        else:
            floor_preference = "any"
            accessible = False

            bedroom_name = (
                f"Bedroom {bedroom_number}"
            )

        # Master / first bedroom gets
        # slightly more minimum space.
        if bedroom_number == 1:
            minimum_area = 140
        else:
            minimum_area = 110

        spaces.append(
            _space(
                f"bedroom-{bedroom_number}",
                "bedroom",
                bedroom_name,
                floor_preference=(
                    floor_preference
                ),
                accessible=accessible,
                min_area=minimum_area,
            )
        )

    # ---------------------------------
    # BATHROOMS
    # ---------------------------------

    for index in range(bathrooms):

        bathroom_number = index + 1

        if (
            bathroom_number == 1
            and accessible_bathroom_required
        ):
            floor_preference = "ground"
            accessible = True
            bathroom_name = (
                "Accessible Bathroom"
            )
            minimum_area = 55

        elif (
            floors > 1
            and bathroom_number > 2
        ):
            floor_preference = "upper"
            accessible = False
            bathroom_name = (
                f"Bathroom {bathroom_number}"
            )
            minimum_area = 40

        else:
            floor_preference = "any"
            accessible = False
            bathroom_name = (
                f"Bathroom {bathroom_number}"
            )
            minimum_area = 40

        spaces.append(
            _space(
                f"bathroom-{bathroom_number}",
                "bathroom",
                bathroom_name,
                floor_preference=(
                    floor_preference
                ),
                accessible=accessible,
                min_area=minimum_area,
            )
        )

    # ---------------------------------
    # STAIRS
    # ---------------------------------

    if floors > 1:
        spaces.append(
            _space(
                "stairs-1",
                "stairs",
                "Staircase",
                floor_preference="ground",
                min_area=55,
            )
        )

    # ---------------------------------
    # FAMILY LOUNGE
    # ---------------------------------

    family_space_score = float(
        preferences.get(
            "family_space",
            0.5,
        )
    )

    if (
        floors > 1
        and (
            family_size >= 4
            or family_space_score >= 0.65
        )
    ):
        spaces.append(
            _space(
                "family-lounge-1",
                "living",
                "Family Lounge",
                floor_preference="upper",
                priority="preferred",
                min_area=120,
            )
        )

    # ---------------------------------
    # HOME OFFICE
    # ---------------------------------

    if required.get(
        "home_office",
        False,
    ):
        spaces.append(
            _space(
                "home-office-1",
                "office",
                "Home Office",
                floor_preference="any",
                priority="required",
                min_area=80,
                notes=(
                    "Place away from noisy "
                    "social areas when possible."
                ),
            )
        )

    # ---------------------------------
    # PRAYER ROOM
    # ---------------------------------

    if required.get(
        "prayer_room",
        False,
    ):
        spaces.append(
            _space(
                "prayer-room-1",
                "prayer",
                "Prayer Room",
                floor_preference="ground",
                priority="required",
                min_area=45,
            )
        )

    # ---------------------------------
    # BALCONY
    # ---------------------------------

    if required.get(
        "balcony",
        False,
    ):
        balcony_floor = (
            "upper"
            if floors > 1
            else "ground"
        )

        spaces.append(
            _space(
                "balcony-1",
                "balcony",
                "Balcony",
                floor_preference=(
                    balcony_floor
                ),
                priority="required",
                min_area=60,
            )
        )

    # ---------------------------------
    # CIRCULATION
    # ---------------------------------

    circulation_notes = (
        "Provide connected circulation "
        "between rooms without requiring "
        "movement through private bedrooms."
    )

    if wheelchair_friendly:
        circulation_notes += (
            " Maintain wider accessible "
            "circulation where practical."
        )

    spaces.append(
        _space(
            "circulation-1",
            "passage",
            "Circulation",
            floor_preference="any",
            priority="required",
            min_area=None,
            accessible=wheelchair_friendly,
            notes=circulation_notes,
        )
    )

    # ---------------------------------
    # OUTDOOR / SITE SPACES
    # ---------------------------------

    outdoor_spaces: list[
        dict[str, Any]
    ] = []

    parking_spaces = int(
        outdoor.get(
            "parking_spaces",
            0,
        )
    )

    if parking_spaces > 0:
        outdoor_spaces.append(
            {
                "id": "parking-1",
                "type": "parking",
                "name": "Parking",
                "count": parking_spaces,
                "priority": "required",
            }
        )

    if outdoor.get(
        "garden",
        False,
    ):
        outdoor_spaces.append(
            {
                "id": "garden-1",
                "type": "garden",
                "name": "Garden",
                "priority": "required",
            }
        )

    if outdoor.get(
        "swimming_pool",
        False,
    ):
        outdoor_spaces.append(
            {
                "id": "pool-1",
                "type": "swimming_pool",
                "name": "Swimming Pool",
                "priority": "required",
            }
        )

    if entrance_ramp:
        outdoor_spaces.append(
            {
                "id": "entrance-ramp-1",
                "type": "ramp",
                "name": "Entrance Ramp",
                "priority": "required",
                "accessible": True,
            }
        )

    # ---------------------------------
    # FLOOR GROUPING
    # ---------------------------------

    ground_spaces = [
        space
        for space in spaces
        if space["floor_preference"]
        == "ground"
    ]

    upper_spaces = [
        space
        for space in spaces
        if space["floor_preference"]
        == "upper"
    ]

    flexible_spaces = [
        space
        for space in spaces
        if space["floor_preference"]
        == "any"
    ]

    # ---------------------------------
    # SUMMARY
    # ---------------------------------

    return {
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "floors": floors,

        "spaces": spaces,

        "ground_floor_spaces": (
            ground_spaces
        ),

        "upper_floor_spaces": (
            upper_spaces
        ),

        "flexible_spaces": (
            flexible_spaces
        ),

        "outdoor_spaces": (
            outdoor_spaces
        ),

        "rules": {
            "ground_floor_bedroom_required": (
                ground_bedroom_required
            ),
            "accessible_bathroom_required": (
                accessible_bathroom_required
            ),
            "wheelchair_friendly": (
                wheelchair_friendly
            ),
            "entrance_ramp_required": (
                entrance_ramp
            ),
            "avoid_bedroom_through_traffic": (
                True
            ),
            "connect_living_dining": (
                True
            ),
            "connect_kitchen_dining": (
                True
            ),
        },

        "statistics": {
            "total_internal_spaces": len(
                spaces
            ),
            "total_outdoor_spaces": len(
                outdoor_spaces
            ),
            "children": children,
            "senior_citizens": seniors,
            "family_size": family_size,
        },
    }