from typing import Any


# ============================================================
# BASIC ROOM OBJECT
# ============================================================


def room(
    room_id: str,
    room_type: str,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    level: int,
    accessible: bool = False,
) -> dict[str, Any]:

    return {
        "id": room_id,
        "type": room_type,
        "name": name,
        "x": round(x, 3),
        "y": round(y, 3),
        "width": round(width, 3),
        "height": round(height, 3),
        "area": round(
            width * height,
            3,
        ),
        "floor_level": level,
        "accessible": accessible,
    }


# ============================================================
# GROUND FLOOR
# ============================================================


def build_ground_floor(
    width: float,
    height: float,
    bedrooms: int,
    bathrooms: int,
    strategy: str,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[
        dict[str, Any]
    ] = []

    accessibility = requirements.get(
        "accessibility",
        {},
    )

    required_spaces = requirements.get(
        "required_spaces",
        {},
    )

    accessible_bedroom = bool(
        accessibility.get(
            "ground_floor_bedroom",
            False,
        )
    )

    accessible_bath = bool(
        accessibility.get(
            "accessible_bathroom",
            False,
        )
    )

    wants_office = bool(
        required_spaces.get(
            "home_office",
            False,
        )
    )

    wants_prayer = bool(
        required_spaces.get(
            "prayer_room",
            False,
        )
    )

    # --------------------------------------------------------
    # A — BALANCED
    # --------------------------------------------------------

    if strategy == "balanced":

        left = width * 0.56
        right = width - left

        public_h = height * 0.46
        private_h = height - public_h

        # Living

        rooms.append(
            room(
                "a-g-living",
                "living",
                "Living Room",
                0,
                0,
                left,
                public_h,
                0,
            )
        )

        # Kitchen

        kitchen_h = (
            public_h * 0.50
        )

        rooms.append(
            room(
                "a-g-kitchen",
                "kitchen",
                "Kitchen",
                left,
                0,
                right,
                kitchen_h,
                0,
            )
        )

        # Dining

        rooms.append(
            room(
                "a-g-dining",
                "dining",
                "Dining Area",
                left,
                kitchen_h,
                right,
                public_h
                - kitchen_h,
                0,
            )
        )

        # Bedroom

        bedroom_w = width * 0.47

        rooms.append(
            room(
                "a-g-bedroom",
                "bedroom",
                (
                    "Accessible Bedroom"
                    if accessible_bedroom
                    else "Bedroom 1"
                ),
                0,
                public_h,
                bedroom_w,
                private_h,
                0,
                accessible_bedroom,
            )
        )

        remaining_w = (
            width - bedroom_w
        )

        service_w = (
            remaining_w * 0.43
        )

        circulation_w = (
            remaining_w
            - service_w
        )

        bath_h = (
            private_h * 0.42
        )

        rooms.append(
            room(
                "a-g-bath",
                "bathroom",
                (
                    "Accessible Bathroom"
                    if accessible_bath
                    else "Bathroom 1"
                ),
                bedroom_w,
                public_h,
                service_w,
                bath_h,
                0,
                accessible_bath,
            )
        )

        rooms.append(
            room(
                "a-g-lobby",
                "passage",
                "Lobby",
                bedroom_w,
                public_h + bath_h,
                service_w,
                private_h - bath_h,
                0,
                accessible_bedroom,
            )
        )

        rooms.append(
            room(
                "a-g-stairs",
                "stairs",
                "Staircase",
                bedroom_w
                + service_w,
                public_h,
                circulation_w,
                private_h,
                0,
            )
        )

    # --------------------------------------------------------
    # B — OPEN LIVING
    # --------------------------------------------------------

    elif strategy == "open_living":

        open_h = height * 0.58

        kitchen_w = width * 0.31

        rooms.append(
            room(
                "b-g-open",
                "living",
                "Open Living & Dining",
                0,
                0,
                width - kitchen_w,
                open_h,
                0,
            )
        )

        rooms.append(
            room(
                "b-g-kitchen",
                "kitchen",
                "Kitchen",
                width - kitchen_w,
                0,
                kitchen_w,
                open_h,
                0,
            )
        )

        lower_h = (
            height - open_h
        )

        bedroom_w = width * 0.50
        bath_w = width * 0.18

        rooms.append(
            room(
                "b-g-bedroom",
                "bedroom",
                (
                    "Accessible Bedroom"
                    if accessible_bedroom
                    else "Bedroom 1"
                ),
                0,
                open_h,
                bedroom_w,
                lower_h,
                0,
                accessible_bedroom,
            )
        )

        rooms.append(
            room(
                "b-g-bath",
                "bathroom",
                (
                    "Accessible Bathroom"
                    if accessible_bath
                    else "Bathroom 1"
                ),
                bedroom_w,
                open_h,
                bath_w,
                lower_h * 0.48,
                0,
                accessible_bath,
            )
        )

        rooms.append(
            room(
                "b-g-lobby",
                "passage",
                "Lobby",
                bedroom_w,
                open_h
                + lower_h * 0.48,
                bath_w,
                lower_h * 0.52,
                0,
                accessible_bedroom,
            )
        )

        rooms.append(
            room(
                "b-g-stairs",
                "stairs",
                "Staircase",
                bedroom_w + bath_w,
                open_h,
                width
                - bedroom_w
                - bath_w,
                lower_h,
                0,
            )
        )

    # --------------------------------------------------------
    # C — PRIVACY
    # --------------------------------------------------------

    else:

        top_h = height * 0.41

        living_w = width * 0.53

        rooms.append(
            room(
                "c-g-living",
                "living",
                "Living Room",
                0,
                0,
                living_w,
                top_h,
                0,
            )
        )

        rooms.append(
            room(
                "c-g-kitchen",
                "kitchen",
                "Kitchen",
                living_w,
                0,
                width - living_w,
                top_h * 0.52,
                0,
            )
        )

        rooms.append(
            room(
                "c-g-dining",
                "dining",
                "Dining Area",
                living_w,
                top_h * 0.52,
                width - living_w,
                top_h * 0.48,
                0,
            )
        )

        lower_y = top_h
        lower_h = height - top_h

        bedroom_w = width * 0.45
        passage_w = width * 0.16
        service_w = (
            width
            - bedroom_w
            - passage_w
        )

        rooms.append(
            room(
                "c-g-bedroom",
                "bedroom",
                (
                    "Private Accessible Bedroom"
                    if accessible_bedroom
                    else "Private Bedroom 1"
                ),
                0,
                lower_y,
                bedroom_w,
                lower_h,
                0,
                accessible_bedroom,
            )
        )

        rooms.append(
            room(
                "c-g-passage",
                "passage",
                "Private Passage",
                bedroom_w,
                lower_y,
                passage_w,
                lower_h,
                0,
                accessible_bedroom,
            )
        )

        bath_h = lower_h * 0.40

        rooms.append(
            room(
                "c-g-bath",
                "bathroom",
                (
                    "Accessible Bathroom"
                    if accessible_bath
                    else "Bathroom 1"
                ),
                bedroom_w
                + passage_w,
                lower_y,
                service_w,
                bath_h,
                0,
                accessible_bath,
            )
        )

        rooms.append(
            room(
                "c-g-stairs",
                "stairs",
                "Staircase",
                bedroom_w
                + passage_w,
                lower_y + bath_h,
                service_w,
                lower_h - bath_h,
                0,
            )
        )

    # --------------------------------------------------------
    # OPTIONAL SMALL ROOMS
    #
    # These are inserted only when the user
    # explicitly asks for them.
    # --------------------------------------------------------

    if wants_prayer:

        available = [
            r
            for r in rooms
            if r["type"]
            == "living"
        ]

        if available:
            host = available[0]

            prayer_w = min(
                host["width"] * 0.27,
                width * 0.16,
            )

            prayer_h = min(
                host["height"] * 0.35,
                height * 0.16,
            )

            rooms.append(
                room(
                    f"{strategy}-g-prayer",
                    "prayer",
                    "Prayer Room",
                    host["x"],
                    host["y"]
                    + host["height"]
                    - prayer_h,
                    prayer_w,
                    prayer_h,
                    0,
                )
            )

    if wants_office:

        rooms.append(
            room(
                f"{strategy}-g-office",
                "office",
                "Home Office",
                width * 0.05,
                height * 0.05,
                width * 0.22,
                height * 0.18,
                0,
            )
        )

    return rooms


# ============================================================
# UPPER FLOOR
# ============================================================


def build_upper_floor(
    width: float,
    height: float,
    bedrooms: int,
    bathrooms: int,
    strategy: str,
    requirements: dict[str, Any],
    level: int = 1,
) -> list[dict[str, Any]]:

    rooms: list[
        dict[str, Any]
    ] = []

    bedrooms_up = max(
        bedrooms - 1,
        1,
    )

    bathrooms_up = max(
        bathrooms - 1,
        1,
    )

    required_spaces = requirements.get(
        "required_spaces",
        {},
    )

    wants_balcony = bool(
        required_spaces.get(
            "balcony",
            False,
        )
    )

    # Main bedroom band.

    bedroom_h = (
        height * 0.50
    )

    bedroom_w = (
        width / bedrooms_up
    )

    for index in range(
        bedrooms_up
    ):
        rooms.append(
            room(
                (
                    f"{strategy}-"
                    f"{level}-bed-{index + 2}"
                ),
                "bedroom",
                f"Bedroom {index + 2}",
                bedroom_w * index,
                0,
                bedroom_w,
                bedroom_h,
                level,
            )
        )

    # Bathroom band.

    bath_h = (
        height * 0.18
    )

    bath_count = min(
        bathrooms_up,
        max(
            bedrooms_up,
            1,
        ),
    )

    bath_w = (
        width / bath_count
    )

    for index in range(
        bath_count
    ):
        rooms.append(
            room(
                (
                    f"{strategy}-"
                    f"{level}-bath-{index + 2}"
                ),
                "bathroom",
                f"Bathroom {index + 2}",
                bath_w * index,
                bedroom_h,
                bath_w,
                bath_h,
                level,
            )
        )

    lower_y = (
        bedroom_h + bath_h
    )

    lower_h = (
        height - lower_y
    )

    if strategy == "privacy":

        lounge_w = width * 0.55
        stairs_w = width * 0.27
        passage_w = (
            width
            - lounge_w
            - stairs_w
        )

        rooms.append(
            room(
                f"{strategy}-{level}-lounge",
                "living",
                "Quiet Family Lounge",
                0,
                lower_y,
                lounge_w,
                lower_h,
                level,
            )
        )

        rooms.append(
            room(
                f"{strategy}-{level}-passage",
                "passage",
                "Private Lobby",
                lounge_w,
                lower_y,
                passage_w,
                lower_h,
                level,
            )
        )

        rooms.append(
            room(
                f"{strategy}-{level}-stairs",
                "stairs",
                "Staircase",
                lounge_w
                + passage_w,
                lower_y,
                stairs_w,
                lower_h,
                level,
            )
        )

    elif strategy == "open_living":

        lounge_w = width * 0.73

        rooms.append(
            room(
                f"{strategy}-{level}-lounge",
                "living",
                "Large Family Lounge",
                0,
                lower_y,
                lounge_w,
                lower_h,
                level,
            )
        )

        rooms.append(
            room(
                f"{strategy}-{level}-stairs",
                "stairs",
                "Staircase",
                lounge_w,
                lower_y,
                width - lounge_w,
                lower_h,
                level,
            )
        )

    else:

        lounge_w = width * 0.66

        rooms.append(
            room(
                f"{strategy}-{level}-lounge",
                "living",
                "Family Lounge",
                0,
                lower_y,
                lounge_w,
                lower_h,
                level,
            )
        )

        rooms.append(
            room(
                f"{strategy}-{level}-stairs",
                "stairs",
                "Staircase",
                lounge_w,
                lower_y,
                width - lounge_w,
                lower_h,
                level,
            )
        )

    # Balcony.

    if wants_balcony:

        balcony_h = min(
            height * 0.10,
            4.0,
        )

        rooms.append(
            room(
                f"{strategy}-{level}-balcony",
                "balcony",
                "Balcony",
                0,
                height - balcony_h,
                width * 0.55,
                balcony_h,
                level,
            )
        )

    return rooms


# ============================================================
# COMPLETE ARCHITECTURAL CANDIDATE
# ============================================================


def generate_architectural_candidate(
    candidate_id: str,
    title: str,
    strategy: str,
    width: float,
    height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
    requirements: dict[str, Any],
) -> dict[str, Any]:

    floor_plans: list[
        dict[str, Any]
    ] = []

    ground_rooms = (
        build_ground_floor(
            width=width,
            height=height,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            strategy=strategy,
            requirements=requirements,
        )
    )

    floor_plans.append(
        {
            "level": 0,
            "name": "Ground Floor",
            "rooms": ground_rooms,
            "doors": [],
            "windows": [],
            "stairs": [
                room_item
                for room_item
                in ground_rooms
                if room_item[
                    "type"
                ]
                == "stairs"
            ],
        }
    )

    # Upper floors.

    for level in range(
        1,
        floors,
    ):

        upper_rooms = (
            build_upper_floor(
                width=width,
                height=height,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                strategy=strategy,
                requirements=requirements,
                level=level,
            )
        )

        floor_plans.append(
            {
                "level": level,
                "name": (
                    "First Floor"
                    if level == 1
                    else f"Floor {level + 1}"
                ),
                "rooms": (
                    upper_rooms
                ),
                "doors": [],
                "windows": [],
                "stairs": [
                    room_item
                    for room_item
                    in upper_rooms
                    if room_item[
                        "type"
                    ]
                    == "stairs"
                ],
            }
        )

    all_rooms = [
        item
        for floor in floor_plans
        for item in floor[
            "rooms"
        ]
    ]

    return {
        "id": candidate_id,
        "title": title,
        "strategy": strategy,

        "source": (
            "ZYNORA Architectural "
            "Generator V3"
        ),

        "name": project.get(
            "name",
            "Generated Home",
        ),

        "width": width,
        "height": height,

        "aspect_ratio": round(
            width / height,
            3,
        ),

        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "floors": floors,

        "rooms": all_rooms,

        "floor_plans": (
            floor_plans
        ),

        "doors": [],
        "windows": [],
        "furniture": [],

        "room_count": len(
            all_rooms
        ),

        "boundary": [
            [0, 0],
            [width, 0],
            [width, height],
            [0, height],
        ],

        "requirements": (
            requirements
        ),

        "generation_version": (
            "architectural-v3"
        ),

        "generated_from_requirements": (
            True
        ),

        "requires_structural_generation": (
            False
        ),
    }