from typing import Any


# ============================================================
# ZYNORA ARCHITECTURAL GENERATOR V3.2
# ============================================================


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
    floor_level: int,
    accessible: bool = False,
) -> dict[str, Any]:

    return {
        "id": room_id,
        "type": room_type,
        "name": name,
        "x": _round(x),
        "y": _round(y),
        "width": _round(width),
        "height": _round(height),
        "area": _round(width * height),
        "floor_level": floor_level,
        "accessible": accessible,
    }


def _floor(
    level: int,
    name: str,
    rooms: list[dict[str, Any]],
) -> dict[str, Any]:

    stairs = [
        room
        for room in rooms
        if room.get("type") == "stairs"
    ]

    return {
        "level": level,
        "name": name,
        "rooms": rooms,
        "doors": [],
        "windows": [],
        "stairs": stairs,
    }


# ============================================================
# REQUIREMENT HELPERS
# ============================================================


def _accessibility_flags(
    requirements: dict[str, Any],
) -> tuple[bool, bool]:

    accessibility = requirements.get(
        "accessibility",
        {},
    )

    return (
        bool(
            accessibility.get(
                "ground_floor_bedroom",
                False,
            )
        ),
        bool(
            accessibility.get(
                "accessible_bathroom",
                False,
            )
        ),
    )


def _wants_balcony(
    requirements: dict[str, Any],
) -> bool:

    spaces = requirements.get(
        "required_spaces",
        {},
    )

    return bool(
        spaces.get(
            "balcony",
            False,
        )
    )


# ============================================================
# STAIR CORES
# ============================================================


def _stair_core(
    strategy: str,
    width: float,
    height: float,
) -> dict[str, float]:

    if strategy == "balanced":

        stair_w = width * 0.24
        stair_h = height * 0.31

    elif strategy == "open_living":

        stair_w = width * 0.22
        stair_h = height * 0.34

    else:

        stair_w = width * 0.24
        stair_h = height * 0.32

    return {
        "x": width - stair_w,
        "y": height - stair_h,
        "width": stair_w,
        "height": stair_h,
    }


# ============================================================
# BALANCED GROUND FLOOR
# ============================================================


def _balanced_ground(
    width: float,
    height: float,
    bathrooms: int,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[dict[str, Any]] = []

    (
        accessible_bedroom,
        accessible_bathroom,
    ) = _accessibility_flags(
        requirements
    )

    stair = _stair_core(
        "balanced",
        width,
        height,
    )

    public_h = height * 0.43

    bedroom_w = width * 0.45

    kitchen_w = width * 0.37
    living_w = width - kitchen_w

    # --------------------------------------------------------
    # PUBLIC ZONE
    # --------------------------------------------------------

    rooms.append(
        _room(
            "balanced-g-living",
            "living",
            "Living Room",
            0,
            0,
            living_w,
            public_h,
            0,
        )
    )

    kitchen_h = public_h * 0.52

    rooms.append(
        _room(
            "balanced-g-kitchen",
            "kitchen",
            "Kitchen",
            living_w,
            0,
            kitchen_w,
            kitchen_h,
            0,
        )
    )

    rooms.append(
        _room(
            "balanced-g-dining",
            "dining",
            "Dining Area",
            living_w,
            kitchen_h,
            kitchen_w,
            public_h - kitchen_h,
            0,
        )
    )

    # --------------------------------------------------------
    # PRIVATE ZONE
    # --------------------------------------------------------

    lower_h = (
        height - public_h
    )

    rooms.append(
        _room(
            "balanced-g-bedroom-1",
            "bedroom",
            (
                "Accessible Bedroom"
                if accessible_bedroom
                else "Bedroom 1"
            ),
            0,
            public_h,
            bedroom_w,
            lower_h,
            0,
            accessible_bedroom,
        )
    )

    # --------------------------------------------------------
    # SERVICE CORE
    # --------------------------------------------------------

    middle_x = bedroom_w

    middle_w = (
        stair["x"]
        - middle_x
    )

    service_h = (
        stair["y"]
        - public_h
    )

    # --------------------------------------------------------
    # FOUR-BATHROOM CONFIGURATION
    #
    # Two ground-floor bathrooms are placed side-by-side.
    # This prevents the previous V3.1 problem where there
    # was insufficient vertical room for Bathroom 2.
    # --------------------------------------------------------

    if bathrooms >= 4:

        bathroom_band_h = (
            service_h * 0.58
        )

        bath_w = (
            middle_w / 2
        )

        rooms.append(
            _room(
                "balanced-g-bathroom-1",
                "bathroom",
                (
                    "Accessible Bathroom"
                    if accessible_bathroom
                    else "Bathroom 1"
                ),
                middle_x,
                public_h,
                bath_w,
                bathroom_band_h,
                0,
                accessible_bathroom,
            )
        )

        rooms.append(
            _room(
                "balanced-g-bathroom-2",
                "bathroom",
                "Common Bathroom",
                middle_x + bath_w,
                public_h,
                bath_w,
                bathroom_band_h,
                0,
            )
        )

        lobby_y = (
            public_h
            + bathroom_band_h
        )

        lobby_h = (
            stair["y"]
            - lobby_y
        )

    else:

        bathroom_band_h = (
            service_h * 0.48
        )

        rooms.append(
            _room(
                "balanced-g-bathroom-1",
                "bathroom",
                (
                    "Accessible Bathroom"
                    if accessible_bathroom
                    else "Bathroom 1"
                ),
                middle_x,
                public_h,
                middle_w,
                bathroom_band_h,
                0,
                accessible_bathroom,
            )
        )

        lobby_y = (
            public_h
            + bathroom_band_h
        )

        lobby_h = (
            stair["y"]
            - lobby_y
        )

    if lobby_h > 0:

        rooms.append(
            _room(
                "balanced-g-lobby",
                "passage",
                "Central Lobby",
                middle_x,
                lobby_y,
                middle_w,
                lobby_h,
                0,
                accessible_bedroom,
            )
        )

    # --------------------------------------------------------
    # STAIR LOBBY
    # --------------------------------------------------------

    landing_x = bedroom_w

    landing_w = (
        stair["x"]
        - landing_x
    )

    if landing_w > 0:

        rooms.append(
            _room(
                "balanced-g-stair-lobby",
                "passage",
                "Stair Lobby",
                landing_x,
                stair["y"],
                landing_w,
                stair["height"],
                0,
            )
        )

    rooms.append(
        _room(
            "balanced-g-stairs",
            "stairs",
            "Staircase",
            stair["x"],
            stair["y"],
            stair["width"],
            stair["height"],
            0,
        )
    )

    return rooms


# ============================================================
# OPEN-LIVING GROUND FLOOR
# ============================================================


def _open_ground(
    width: float,
    height: float,
    bathrooms: int,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[dict[str, Any]] = []

    (
        accessible_bedroom,
        accessible_bathroom,
    ) = _accessibility_flags(
        requirements
    )

    stair = _stair_core(
        "open_living",
        width,
        height,
    )

    public_h = height * 0.54

    kitchen_w = width * 0.29

    open_w = (
        width - kitchen_w
    )

    rooms.append(
        _room(
            "open-g-living-dining",
            "living",
            "Open Living & Dining",
            0,
            0,
            open_w,
            public_h,
            0,
        )
    )

    rooms.append(
        _room(
            "open-g-kitchen",
            "kitchen",
            "Open Kitchen",
            open_w,
            0,
            kitchen_w,
            public_h,
            0,
        )
    )

    lower_y = public_h

    lower_h = (
        height - public_h
    )

    bedroom_w = width * 0.48

    rooms.append(
        _room(
            "open-g-bedroom-1",
            "bedroom",
            (
                "Accessible Bedroom"
                if accessible_bedroom
                else "Bedroom 1"
            ),
            0,
            lower_y,
            bedroom_w,
            lower_h,
            0,
            accessible_bedroom,
        )
    )

    service_x = bedroom_w

    service_w = (
        stair["x"]
        - service_x
    )

    # Keep Bathroom 1 completely above the stair-lobby band.
    available_before_stair = max(
        stair["y"] - lower_y,
        0.0,
    )

    bath_h = min(
        lower_h * 0.34,
        available_before_stair,
    )

    rooms.append(
        _room(
            "open-g-bathroom-1",
            "bathroom",
            (
                "Accessible Bathroom"
                if accessible_bathroom
                else "Bathroom 1"
            ),
            service_x,
            lower_y,
            service_w,
            bath_h,
            0,
            accessible_bathroom,
        )
    )

    if bathrooms >= 4:

        second_bath_h = (
            lower_h * 0.27
        )

        rooms.append(
            _room(
                "open-g-bathroom-2",
                "bathroom",
                "Common Bathroom",
                service_x,
                lower_y + bath_h,
                service_w,
                second_bath_h,
                0,
            )
        )

        lobby_y = (
            lower_y
            + bath_h
            + second_bath_h
        )

    else:

        lobby_y = (
            lower_y
            + bath_h
        )

    lobby_h = (
        stair["y"]
        - lobby_y
    )

    if lobby_h > 0:

        rooms.append(
            _room(
                "open-g-lobby",
                "passage",
                "Open Lobby",
                service_x,
                lobby_y,
                service_w,
                lobby_h,
                0,
                accessible_bedroom,
            )
        )

    landing_w = (
        stair["x"]
        - bedroom_w
    )

    if landing_w > 0:

        rooms.append(
            _room(
                "open-g-stair-lobby",
                "passage",
                "Stair Lobby",
                bedroom_w,
                stair["y"],
                landing_w,
                stair["height"],
                0,
            )
        )

    rooms.append(
        _room(
            "open-g-stairs",
            "stairs",
            "Staircase",
            stair["x"],
            stair["y"],
            stair["width"],
            stair["height"],
            0,
        )
    )

    return rooms


# ============================================================
# PRIVACY GROUND FLOOR
# ============================================================


def _privacy_ground(
    width: float,
    height: float,
    bathrooms: int,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[dict[str, Any]] = []

    (
        accessible_bedroom,
        accessible_bathroom,
    ) = _accessibility_flags(
        requirements
    )

    stair = _stair_core(
        "privacy",
        width,
        height,
    )

    public_h = height * 0.39

    living_w = width * 0.52

    rooms.append(
        _room(
            "privacy-g-living",
            "living",
            "Formal Living Room",
            0,
            0,
            living_w,
            public_h,
            0,
        )
    )

    right_w = (
        width - living_w
    )

    kitchen_h = (
        public_h * 0.51
    )

    rooms.append(
        _room(
            "privacy-g-kitchen",
            "kitchen",
            "Kitchen",
            living_w,
            0,
            right_w,
            kitchen_h,
            0,
        )
    )

    rooms.append(
        _room(
            "privacy-g-dining",
            "dining",
            "Dining Room",
            living_w,
            kitchen_h,
            right_w,
            public_h - kitchen_h,
            0,
        )
    )

    lower_y = public_h

    lower_h = (
        height - public_h
    )

    bedroom_w = (
        width * 0.43
    )

    passage_w = (
        width * 0.14
    )

    rooms.append(
        _room(
            "privacy-g-bedroom-1",
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
        _room(
            "privacy-g-private-passage",
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

    service_x = (
        bedroom_w
        + passage_w
    )

    service_w = (
        stair["x"]
        - service_x
    )

    bath1_h = (
        lower_h * 0.34
    )

    rooms.append(
        _room(
            "privacy-g-bathroom-1",
            "bathroom",
            (
                "Accessible Bathroom"
                if accessible_bathroom
                else "Bathroom 1"
            ),
            service_x,
            lower_y,
            service_w,
            bath1_h,
            0,
            accessible_bathroom,
        )
    )

    if bathrooms >= 4:

        bath2_h = (
            lower_h * 0.25
        )

        rooms.append(
            _room(
                "privacy-g-bathroom-2",
                "bathroom",
                "Guest Bathroom",
                service_x,
                lower_y + bath1_h,
                service_w,
                bath2_h,
                0,
            )
        )

        service_lobby_y = (
            lower_y
            + bath1_h
            + bath2_h
        )

    else:

        service_lobby_y = (
            lower_y
            + bath1_h
        )

    service_lobby_h = (
        stair["y"]
        - service_lobby_y
    )

    if service_lobby_h > 0:

        rooms.append(
            _room(
                "privacy-g-service-lobby",
                "passage",
                "Service Lobby",
                service_x,
                service_lobby_y,
                service_w,
                service_lobby_h,
                0,
            )
        )

    landing_x = (
        bedroom_w
        + passage_w
    )

    landing_w = (
        stair["x"]
        - landing_x
    )

    if landing_w > 0:

        rooms.append(
            _room(
                "privacy-g-stair-lobby",
                "passage",
                "Stair Lobby",
                landing_x,
                stair["y"],
                landing_w,
                stair["height"],
                0,
            )
        )

    rooms.append(
        _room(
            "privacy-g-stairs",
            "stairs",
            "Staircase",
            stair["x"],
            stair["y"],
            stair["width"],
            stair["height"],
            0,
        )
    )

    return rooms


# ============================================================
# BALANCED FIRST FLOOR
# ============================================================


def _balanced_upper(
    width: float,
    height: float,
    level: int,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[dict[str, Any]] = []

    stair = _stair_core(
        "balanced",
        width,
        height,
    )

    balcony_h = (
        min(
            height * 0.09,
            4.0,
        )
        if _wants_balcony(
            requirements
        )
        else 0
    )

    indoor_h = (
        height - balcony_h
    )

    bedroom_h = (
        indoor_h * 0.52
    )

    bedroom_w = (
        width / 2
    )

    rooms.append(
        _room(
            "balanced-1-bedroom-2",
            "bedroom",
            "Bedroom 2",
            0,
            0,
            bedroom_w,
            bedroom_h,
            level,
        )
    )

    rooms.append(
        _room(
            "balanced-1-bedroom-3",
            "bedroom",
            "Bedroom 3",
            bedroom_w,
            0,
            bedroom_w,
            bedroom_h,
            level,
        )
    )

    lower_y = bedroom_h

    bath_h = (
        indoor_h * 0.20
    )

    rooms.append(
        _room(
            "balanced-1-bathroom-3",
            "bathroom",
            "Bathroom 3",
            0,
            lower_y,
            bedroom_w,
            bath_h,
            level,
        )
    )

    rooms.append(
        _room(
            "balanced-1-bathroom-4",
            "bathroom",
            "Bathroom 4",
            bedroom_w,
            lower_y,
            bedroom_w,
            bath_h,
            level,
        )
    )

    lounge_y = (
        lower_y + bath_h
    )

    lounge_h = (
        indoor_h - lounge_y
    )

    rooms.append(
        _room(
            "balanced-1-family",
            "living",
            "Family Lounge",
            0,
            lounge_y,
            stair["x"],
            lounge_h,
            level,
        )
    )

    stair_height = max(
        0,
        min(
            stair["height"],
            indoor_h - stair["y"],
        ),
    )

    if stair_height > 0:

        rooms.append(
            _room(
                "balanced-1-stairs",
                "stairs",
                "Staircase",
                stair["x"],
                stair["y"],
                stair["width"],
                stair_height,
                level,
            )
        )

    if balcony_h > 0:

        rooms.append(
            _room(
                "balanced-1-balcony",
                "balcony",
                "Front Balcony",
                0,
                indoor_h,
                width * 0.58,
                balcony_h,
                level,
            )
        )

    return rooms


# ============================================================
# OPEN-LIVING FIRST FLOOR
# ============================================================


def _open_upper(
    width: float,
    height: float,
    level: int,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[dict[str, Any]] = []

    stair = _stair_core(
        "open_living",
        width,
        height,
    )

    balcony_h = (
        min(
            height * 0.11,
            4.5,
        )
        if _wants_balcony(
            requirements
        )
        else 0
    )

    indoor_h = (
        height - balcony_h
    )

    bedroom_h = (
        indoor_h * 0.46
    )

    left_bed_w = (
        width * 0.48
    )

    right_bed_w = (
        width - left_bed_w
    )

    rooms.append(
        _room(
            "open-1-bedroom-2",
            "bedroom",
            "Bedroom 2",
            0,
            0,
            left_bed_w,
            bedroom_h,
            level,
        )
    )

    rooms.append(
        _room(
            "open-1-bedroom-3",
            "bedroom",
            "Bedroom 3",
            left_bed_w,
            0,
            right_bed_w,
            bedroom_h,
            level,
        )
    )

    bath_h = (
        indoor_h * 0.18
    )

    rooms.append(
        _room(
            "open-1-bathroom-3",
            "bathroom",
            "Bathroom 3",
            0,
            bedroom_h,
            width * 0.30,
            bath_h,
            level,
        )
    )

    rooms.append(
        _room(
            "open-1-bathroom-4",
            "bathroom",
            "Bathroom 4",
            width * 0.30,
            bedroom_h,
            width * 0.30,
            bath_h,
            level,
        )
    )

    rooms.append(
        _room(
            "open-1-landing",
            "passage",
            "Upper Landing",
            width * 0.60,
            bedroom_h,
            width * 0.40,
            bath_h,
            level,
        )
    )

    lounge_y = (
        bedroom_h + bath_h
    )

    lounge_h = (
        indoor_h - lounge_y
    )

    rooms.append(
        _room(
            "open-1-family",
            "living",
            "Open Family Lounge",
            0,
            lounge_y,
            stair["x"],
            lounge_h,
            level,
        )
    )

    stair_height = max(
        0,
        min(
            stair["height"],
            indoor_h - stair["y"],
        ),
    )

    if stair_height > 0:

        rooms.append(
            _room(
                "open-1-stairs",
                "stairs",
                "Staircase",
                stair["x"],
                stair["y"],
                stair["width"],
                stair_height,
                level,
            )
        )

    if balcony_h > 0:

        rooms.append(
            _room(
                "open-1-balcony",
                "balcony",
                "Wide Family Balcony",
                0,
                indoor_h,
                width * 0.72,
                balcony_h,
                level,
            )
        )

    return rooms


# ============================================================
# PRIVACY FIRST FLOOR
# ============================================================


def _privacy_upper(
    width: float,
    height: float,
    level: int,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[dict[str, Any]] = []

    stair = _stair_core(
        "privacy",
        width,
        height,
    )

    balcony_h = (
        min(
            height * 0.08,
            3.5,
        )
        if _wants_balcony(
            requirements
        )
        else 0
    )

    indoor_h = (
        height - balcony_h
    )

    passage_w = (
        width * 0.12
    )

    left_w = (
        width - passage_w
    ) * 0.50

    right_x = (
        left_w + passage_w
    )

    right_w = (
        width - right_x
    )

    bedroom_h = (
        indoor_h * 0.57
    )

    rooms.append(
        _room(
            "privacy-1-bedroom-2",
            "bedroom",
            "Private Bedroom 2",
            0,
            0,
            left_w,
            bedroom_h,
            level,
        )
    )

    rooms.append(
        _room(
            "privacy-1-passage",
            "passage",
            "Private Corridor",
            left_w,
            0,
            passage_w,
            bedroom_h,
            level,
        )
    )

    rooms.append(
        _room(
            "privacy-1-bedroom-3",
            "bedroom",
            "Private Bedroom 3",
            right_x,
            0,
            right_w,
            bedroom_h,
            level,
        )
    )

    # Keep Bathroom 4 and the bathroom band above the stair core.
    available_before_stair = max(
        stair["y"] - bedroom_h,
        0.0,
    )

    bath_h = min(
        indoor_h * 0.18,
        available_before_stair,
    )

    rooms.append(
        _room(
            "privacy-1-bathroom-3",
            "bathroom",
            "Bathroom 3",
            0,
            bedroom_h,
            left_w,
            bath_h,
            level,
        )
    )

    rooms.append(
        _room(
            "privacy-1-bathroom-4",
            "bathroom",
            "Bathroom 4",
            right_x,
            bedroom_h,
            right_w,
            bath_h,
            level,
        )
    )

    rooms.append(
        _room(
            "privacy-1-bath-lobby",
            "passage",
            "Private Lobby",
            left_w,
            bedroom_h,
            passage_w,
            bath_h,
            level,
        )
    )

    lounge_y = (
        bedroom_h + bath_h
    )

    lounge_h = (
        indoor_h - lounge_y
    )

    rooms.append(
        _room(
            "privacy-1-family",
            "living",
            "Quiet Family Lounge",
            0,
            lounge_y,
            stair["x"],
            lounge_h,
            level,
        )
    )

    stair_height = max(
        0,
        min(
            stair["height"],
            indoor_h - stair["y"],
        ),
    )

    if stair_height > 0:

        rooms.append(
            _room(
                "privacy-1-stairs",
                "stairs",
                "Staircase",
                stair["x"],
                stair["y"],
                stair["width"],
                stair_height,
                level,
            )
        )

    if balcony_h > 0:

        rooms.append(
            _room(
                "privacy-1-balcony",
                "balcony",
                "Private Balcony",
                0,
                indoor_h,
                width * 0.42,
                balcony_h,
                level,
            )
        )

    return rooms


# ============================================================
# SINGLE-FLOOR FALLBACK
# ============================================================


def _single_floor_plan(
    width: float,
    height: float,
    bedrooms: int,
    bathrooms: int,
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    rooms: list[dict[str, Any]] = []

    accessible_bedroom, accessible_bathroom = (
        _accessibility_flags(
            requirements
        )
    )

    public_h = (
        height * 0.40
    )

    living_w = (
        width * 0.60
    )

    rooms.append(
        _room(
            "single-living",
            "living",
            "Living & Dining",
            0,
            0,
            living_w,
            public_h,
            0,
        )
    )

    rooms.append(
        _room(
            "single-kitchen",
            "kitchen",
            "Kitchen",
            living_w,
            0,
            width - living_w,
            public_h,
            0,
        )
    )

    private_y = public_h

    private_h = (
        height - private_y
    )

    bedroom_band_h = (
        private_h * 0.68
    )

    bedroom_w = (
        width / max(
            bedrooms,
            1,
        )
    )

    for index in range(
        bedrooms
    ):

        rooms.append(
            _room(
                f"single-bedroom-{index + 1}",
                "bedroom",
                (
                    "Accessible Bedroom"
                    if index == 0
                    and accessible_bedroom
                    else f"Bedroom {index + 1}"
                ),
                bedroom_w * index,
                private_y,
                bedroom_w,
                bedroom_band_h,
                0,
                (
                    index == 0
                    and accessible_bedroom
                ),
            )
        )

    bathroom_y = (
        private_y
        + bedroom_band_h
    )

    bathroom_h = (
        height - bathroom_y
    )

    bathroom_w = (
        width / max(
            bathrooms,
            1,
        )
    )

    for index in range(
        bathrooms
    ):

        rooms.append(
            _room(
                f"single-bathroom-{index + 1}",
                "bathroom",
                (
                    "Accessible Bathroom"
                    if index == 0
                    and accessible_bathroom
                    else f"Bathroom {index + 1}"
                ),
                bathroom_w * index,
                bathroom_y,
                bathroom_w,
                bathroom_h,
                0,
                (
                    index == 0
                    and accessible_bathroom
                ),
            )
        )

    return rooms


# ============================================================
# GENERATE ONE ARCHITECTURAL CANDIDATE
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

    if width <= 0:
        raise ValueError(
            "Building width must be greater than zero."
        )

    if height <= 0:
        raise ValueError(
            "Building height must be greater than zero."
        )

    if bedrooms < 1:
        raise ValueError(
            "At least one bedroom is required."
        )

    if bathrooms < 1:
        raise ValueError(
            "At least one bathroom is required."
        )

    if floors < 1:
        raise ValueError(
            "At least one floor is required."
        )

    strategy = (
        strategy
        .lower()
        .strip()
    )

    valid_strategies = {
        "balanced",
        "open_living",
        "privacy",
    }

    if strategy not in valid_strategies:

        raise ValueError(
            "Unknown architectural strategy: "
            f"{strategy}"
        )

    floor_plans: list[
        dict[str, Any]
    ] = []

    # ========================================================
    # ONE-FLOOR HOME
    # ========================================================

    if floors == 1:

        rooms = _single_floor_plan(
            width,
            height,
            bedrooms,
            bathrooms,
            requirements,
        )

        floor_plans.append(
            _floor(
                0,
                "Ground Floor",
                rooms,
            )
        )

    # ========================================================
    # MULTI-FLOOR HOME
    # ========================================================

    else:

        if strategy == "balanced":

            ground_rooms = (
                _balanced_ground(
                    width,
                    height,
                    bathrooms,
                    requirements,
                )
            )

        elif strategy == "open_living":

            ground_rooms = (
                _open_ground(
                    width,
                    height,
                    bathrooms,
                    requirements,
                )
            )

        else:

            ground_rooms = (
                _privacy_ground(
                    width,
                    height,
                    bathrooms,
                    requirements,
                )
            )

        floor_plans.append(
            _floor(
                0,
                "Ground Floor",
                ground_rooms,
            )
        )

        for level in range(
            1,
            floors,
        ):

            if strategy == "balanced":

                upper_rooms = (
                    _balanced_upper(
                        width,
                        height,
                        level,
                        requirements,
                    )
                )

            elif strategy == "open_living":

                upper_rooms = (
                    _open_upper(
                        width,
                        height,
                        level,
                        requirements,
                    )
                )

            else:

                upper_rooms = (
                    _privacy_upper(
                        width,
                        height,
                        level,
                        requirements,
                    )
                )

            floor_name = (
                "First Floor"
                if level == 1
                else f"Floor {level + 1}"
            )

            floor_plans.append(
                _floor(
                    level,
                    floor_name,
                    upper_rooms,
                )
            )

    # ========================================================
    # FLATTEN ROOM LIST
    # ========================================================

    all_rooms = [
        room
        for floor in floor_plans
        for room in floor["rooms"]
    ]

    actual_bedrooms = len(
        [
            room
            for room in all_rooms
            if room.get("type")
            == "bedroom"
        ]
    )

    actual_bathrooms = len(
        [
            room
            for room in all_rooms
            if room.get("type")
            == "bathroom"
        ]
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {
        "id": candidate_id,

        "title": title,

        "strategy": strategy,

        "source": (
            "ZYNORA Architectural Generator V3.2"
        ),

        "name": project.get(
            "name",
            "Generated Home",
        ),

        "width": _round(
            width
        ),

        "height": _round(
            height
        ),

        "aspect_ratio": _round(
            width / height
        ),

        "bedrooms": bedrooms,

        "bathrooms": bathrooms,

        "floors": floors,

        "actual_bedrooms": (
            actual_bedrooms
        ),

        "actual_bathrooms": (
            actual_bathrooms
        ),

        "room_count": len(
            all_rooms
        ),

        "rooms": all_rooms,

        "floor_plans": (
            floor_plans
        ),

        "doors": [],

        "windows": [],

        "furniture": [],

        "boundary": [
            [
                0,
                0,
            ],
            [
                _round(width),
                0,
            ],
            [
                _round(width),
                _round(height),
            ],
            [
                0,
                _round(height),
            ],
        ],

        "requirements": (
            requirements
        ),

        "generation_version": (
            "architectural-v3.2"
        ),

        "generated_from_requirements": (
            True
        ),

        "requires_structural_generation": (
            False
        ),
    }


# ============================================================
# GENERATE THREE CANDIDATES
# ============================================================


def generate_architectural_candidates(
    width: float,
    height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
    requirements: dict[str, Any],
) -> list[dict[str, Any]]:

    configurations = [
        (
            "candidate-a",
            "Balanced Family Plan",
            "balanced",
        ),
        (
            "candidate-b",
            "Open Living Plan",
            "open_living",
        ),
        (
            "candidate-c",
            "Privacy Focused Plan",
            "privacy",
        ),
    ]

    candidates: list[
        dict[str, Any]
    ] = []

    for (
        candidate_id,
        title,
        strategy,
    ) in configurations:

        candidate = (
            generate_architectural_candidate(
                candidate_id=(
                    candidate_id
                ),
                title=title,
                strategy=strategy,
                width=width,
                height=height,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                floors=floors,
                project=project,
                requirements=requirements,
            )
        )

        candidates.append(
            candidate
        )

    return candidates