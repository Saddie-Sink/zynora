from typing import Any


# ============================================================
# BASIC HELPERS
# ============================================================


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _room_area(
    room: dict[str, Any],
) -> float:
    area = room.get("area")

    if area is not None:
        return _safe_float(area)

    width = _safe_float(
        room.get("width")
    )

    height = _safe_float(
        room.get("height")
    )

    return width * height


def _rooms_of_type(
    rooms: list[dict[str, Any]],
    room_type: str,
) -> list[dict[str, Any]]:
    return [
        room
        for room in rooms
        if str(
            room.get("type", "")
        ).lower() == room_type.lower()
    ]


def _total_area(
    rooms: list[dict[str, Any]],
) -> float:
    return sum(
        _room_area(room)
        for room in rooms
    )


def _average_area(
    rooms: list[dict[str, Any]],
) -> float:
    if not rooms:
        return 0.0

    return (
        _total_area(rooms)
        / len(rooms)
    )


def _ratio(
    value: float,
    total: float,
) -> float:
    if total <= 0:
        return 0.0

    return value / total


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


# ============================================================
# ACCESSIBILITY FEATURES
# ============================================================


def _accessibility_score(
    plan: dict[str, Any],
) -> float:

    rooms = plan.get(
        "rooms",
        [],
    )

    requirements = plan.get(
        "requirements",
        {},
    )

    accessibility = requirements.get(
        "accessibility",
        {},
    )

    requested_features = [
        bool(
            accessibility.get(
                "entrance_ramp"
            )
        ),
        bool(
            accessibility.get(
                "ground_floor_bedroom"
            )
        ),
        bool(
            accessibility.get(
                "accessible_bathroom"
            )
        ),
        bool(
            accessibility.get(
                "wheelchair_friendly"
            )
        ),
    ]

    requested_count = sum(
        requested_features
    )

    if requested_count == 0:
        return 1.0

    achieved = 0

    site_features = plan.get(
        "site_features",
        [],
    )

    # Entrance ramp

    if accessibility.get(
        "entrance_ramp"
    ):
        has_ramp = any(
            "ramp"
            in str(
                feature.get(
                    "name",
                    "",
                )
            ).lower()
            for feature in site_features
        )

        if has_ramp:
            achieved += 1

    # Ground-floor bedroom

    if accessibility.get(
        "ground_floor_bedroom"
    ):
        has_ground_bedroom = any(
            room.get("type")
            == "bedroom"
            and int(
                room.get(
                    "floor_level",
                    0,
                )
            ) == 0
            for room in rooms
        )

        if has_ground_bedroom:
            achieved += 1

    # Accessible bathroom

    if accessibility.get(
        "accessible_bathroom"
    ):
        has_accessible_bathroom = any(
            room.get("type")
            == "bathroom"
            and bool(
                room.get(
                    "accessible",
                    False,
                )
            )
            for room in rooms
        )

        if has_accessible_bathroom:
            achieved += 1

    # Wheelchair friendly

    if accessibility.get(
        "wheelchair_friendly"
    ):
        ground_rooms = [
            room
            for room in rooms
            if int(
                room.get(
                    "floor_level",
                    0,
                )
            ) == 0
        ]

        accessible_ground = [
            room
            for room in ground_rooms
            if bool(
                room.get(
                    "accessible",
                    False,
                )
            )
            or room.get("type")
            in {
                "living",
                "dining",
                "kitchen",
                "passage",
            }
        ]

        if (
            ground_rooms
            and len(
                accessible_ground
            )
            >= max(
                1,
                len(ground_rooms) // 2,
            )
        ):
            achieved += 1

    return _clamp(
        achieved
        / requested_count
    )


# ============================================================
# PRIVACY FEATURE
# ============================================================


def _privacy_score(
    plan: dict[str, Any],
) -> float:

    rooms = plan.get(
        "rooms",
        [],
    )

    bedrooms = _rooms_of_type(
        rooms,
        "bedroom",
    )

    if not bedrooms:
        return 0.0

    floors = max(
        int(
            plan.get(
                "floors",
                1,
            )
        ),
        1,
    )

    upper_bedrooms = sum(
        1
        for room in bedrooms
        if int(
            room.get(
                "floor_level",
                0,
            )
        ) > 0
    )

    upper_ratio = (
        upper_bedrooms
        / len(bedrooms)
    )

    bathrooms = _rooms_of_type(
        rooms,
        "bathroom",
    )

    bedroom_area = _total_area(
        bedrooms
    )

    bathroom_area = _total_area(
        bathrooms
    )

    private_area = (
        bedroom_area
        + bathroom_area
    )

    total = _total_area(
        rooms
    )

    private_area_ratio = _ratio(
        private_area,
        total,
    )

    if floors == 1:
        upper_ratio = 0.5

    score = (
        upper_ratio * 0.60
        + min(
            private_area_ratio
            / 0.55,
            1.0,
        ) * 0.40
    )

    return _clamp(score)


# ============================================================
# OPEN-LIVING FEATURE
# ============================================================


def _open_living_score(
    plan: dict[str, Any],
) -> float:

    rooms = plan.get(
        "rooms",
        [],
    )

    social_types = {
        "living",
        "dining",
        "kitchen",
    }

    social_rooms = [
        room
        for room in rooms
        if room.get("type")
        in social_types
    ]

    total_area = _total_area(
        rooms
    )

    social_area = _total_area(
        social_rooms
    )

    social_ratio = _ratio(
        social_area,
        total_area,
    )

    # Around 35-45% social space is
    # considered strongly open/family oriented.

    return _clamp(
        social_ratio / 0.40
    )


# ============================================================
# FAMILY SPACE FEATURE
# ============================================================


def _family_space_score(
    plan: dict[str, Any],
) -> float:

    rooms = plan.get(
        "rooms",
        [],
    )

    family_types = {
        "living",
        "dining",
        "family",
        "balcony",
    }

    family_rooms = [
        room
        for room in rooms
        if room.get("type")
        in family_types
    ]

    total_area = _total_area(
        rooms
    )

    family_area = _total_area(
        family_rooms
    )

    return _clamp(
        _ratio(
            family_area,
            total_area,
        )
        / 0.40
    )


# ============================================================
# NATURAL LIGHT / OPENINGS
# ============================================================


def _natural_light_score(
    plan: dict[str, Any],
) -> float:

    rooms = plan.get(
        "rooms",
        [],
    )

    windows = plan.get(
        "windows",
        [],
    )

    habitable_rooms = [
        room
        for room in rooms
        if room.get("type")
        in {
            "living",
            "dining",
            "kitchen",
            "bedroom",
            "office",
        }
    ]

    if not habitable_rooms:
        return 0.0

    # Approximation for now.
    # Later we will map each window
    # to the exact room and exterior wall.

    window_ratio = (
        len(windows)
        / len(habitable_rooms)
    )

    return _clamp(
        window_ratio / 1.5
    )


# ============================================================
# CIRCULATION FEATURE
# ============================================================


def _circulation_score(
    plan: dict[str, Any],
) -> float:

    rooms = plan.get(
        "rooms",
        [],
    )

    circulation = [
        room
        for room in rooms
        if room.get("type")
        in {
            "passage",
            "stairs",
        }
    ]

    total_area = _total_area(
        rooms
    )

    circulation_area = _total_area(
        circulation
    )

    ratio = _ratio(
        circulation_area,
        total_area,
    )

    # Prefer circulation around 10-18%.
    # Too little can hurt movement;
    # too much wastes usable area.

    ideal = 0.14

    difference = abs(
        ratio - ideal
    )

    return _clamp(
        1.0
        - difference / ideal
    )


# ============================================================
# SPACE UTILIZATION
# ============================================================


def _space_utilization(
    plan: dict[str, Any],
) -> float:

    width = _safe_float(
        plan.get("width")
    )

    height = _safe_float(
        plan.get("height")
    )

    floors = max(
        int(
            plan.get(
                "floors",
                1,
            )
        ),
        1,
    )

    available_area = (
        width
        * height
        * floors
    )

    if available_area <= 0:
        return 0.0

    rooms = plan.get(
        "rooms",
        [],
    )

    used_area = _total_area(
        rooms
    )

    return _clamp(
        used_area
        / available_area
    )


# ============================================================
# MAIN FEATURE EXTRACTOR
# ============================================================


def extract_layout_features(
    plan: dict[str, Any],
) -> dict[str, float]:

    rooms = plan.get(
        "rooms",
        [],
    )

    bedrooms = _rooms_of_type(
        rooms,
        "bedroom",
    )

    bathrooms = _rooms_of_type(
        rooms,
        "bathroom",
    )

    living_rooms = _rooms_of_type(
        rooms,
        "living",
    )

    kitchens = _rooms_of_type(
        rooms,
        "kitchen",
    )

    passages = _rooms_of_type(
        rooms,
        "passage",
    )

    total_area = _total_area(
        rooms
    )

    bedroom_area = _total_area(
        bedrooms
    )

    bathroom_area = _total_area(
        bathrooms
    )

    living_area = _total_area(
        living_rooms
    )

    kitchen_area = _total_area(
        kitchens
    )

    passage_area = _total_area(
        passages
    )

    features = {
        "space_utilization": (
            _space_utilization(
                plan
            )
        ),

        "average_bedroom_area": (
            _average_area(
                bedrooms
            )
        ),

        "average_bathroom_area": (
            _average_area(
                bathrooms
            )
        ),

        "living_area_ratio": (
            _ratio(
                living_area,
                total_area,
            )
        ),

        "bedroom_area_ratio": (
            _ratio(
                bedroom_area,
                total_area,
            )
        ),

        "bathroom_area_ratio": (
            _ratio(
                bathroom_area,
                total_area,
            )
        ),

        "kitchen_area_ratio": (
            _ratio(
                kitchen_area,
                total_area,
            )
        ),

        "circulation_area_ratio": (
            _ratio(
                passage_area,
                total_area,
            )
        ),

        "door_density": (
            _ratio(
                len(
                    plan.get(
                        "doors",
                        [],
                    )
                ),
                max(
                    len(rooms),
                    1,
                ),
            )
        ),

        "window_density": (
            _ratio(
                len(
                    plan.get(
                        "windows",
                        [],
                    )
                ),
                max(
                    len(rooms),
                    1,
                ),
            )
        ),

        "accessibility_score": (
            _accessibility_score(
                plan
            )
        ),

        "privacy_score": (
            _privacy_score(
                plan
            )
        ),

        "open_living_score": (
            _open_living_score(
                plan
            )
        ),

        "family_space_score": (
            _family_space_score(
                plan
            )
        ),

        "natural_light_score": (
            _natural_light_score(
                plan
            )
        ),

        "circulation_score": (
            _circulation_score(
                plan
            )
        ),
    }

    return {
        key: round(
            value,
            4,
        )
        for key, value
        in features.items()
    }


# ============================================================
# ML VECTOR
#
# Stable feature order is important for ML.
# ============================================================


FEATURE_NAMES = [
    "space_utilization",
    "average_bedroom_area",
    "average_bathroom_area",
    "living_area_ratio",
    "bedroom_area_ratio",
    "bathroom_area_ratio",
    "kitchen_area_ratio",
    "circulation_area_ratio",
    "door_density",
    "window_density",
    "accessibility_score",
    "privacy_score",
    "open_living_score",
    "family_space_score",
    "natural_light_score",
    "circulation_score",
]


def layout_feature_vector(
    plan: dict[str, Any],
) -> list[float]:

    features = (
        extract_layout_features(
            plan
        )
    )

    return [
        features[name]
        for name in FEATURE_NAMES
    ]