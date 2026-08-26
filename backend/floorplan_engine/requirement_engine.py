from typing import Any


def _to_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(
    value: Any,
    default: bool = False,
) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = (
            value.strip().lower()
        )

        if normalized in {
            "true",
            "yes",
            "1",
            "on",
        }:
            return True

        if normalized in {
            "false",
            "no",
            "0",
            "off",
        }:
            return False

    if value is None:
        return default

    return bool(value)


def _to_list(
    value: Any,
) -> list[str]:

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    return []


def _contains(
    values: list[str],
    *names: str,
) -> bool:

    normalized = {
        value.lower().strip()
        for value in values
    }

    return any(
        name.lower().strip()
        in normalized
        for name in names
    )


def build_requirements(
    project: dict[str, Any],
    building_width: float | None = None,
    building_height: float | None = None,
) -> dict[str, Any]:

    # ========================================================
    # BASIC USER INPUT
    # ========================================================

    bedrooms = max(
        1,
        _to_int(
            project.get(
                "bedrooms"
            ),
            1,
        ),
    )

    total_bathrooms = max(
        1,
        _to_int(
            project.get(
                "bathrooms"
            ),
            1,
        ),
    )

    floors = max(
        1,
        _to_int(
            project.get(
                "floors"
            ),
            1,
        ),
    )

    family_size = max(
        1,
        _to_int(
            project.get(
                "familySize"
            ),
            bedrooms,
        ),
    )

    children = max(
        0,
        _to_int(
            project.get(
                "children"
            ),
            0,
        ),
    )

    senior_citizens = max(
        0,
        _to_int(
            project.get(
                "seniorCitizens"
            ),
            0,
        ),
    )

    pets = max(
        0,
        _to_int(
            project.get(
                "pets"
            ),
            0,
        ),
    )

    parking_spaces = max(
        0,
        _to_int(
            project.get(
                "parkingSpaces"
            ),
            0,
        ),
    )

    budget = _to_float(
        project.get(
            "budget"
        ),
        0.0,
    )

    lifestyle = _to_list(
        project.get(
            "lifestyleFeatures"
        )
    )

    accessibility = _to_list(
        project.get(
            "accessibilityFeatures"
        )
    )

    materials = _to_list(
        project.get(
            "preferredMaterials"
        )
    )

    sustainability = _to_list(
        project.get(
            "sustainabilityFeatures"
        )
    )

    # ========================================================
    # EXTERNAL BATHROOM / WASH AREA
    #
    # This is separate from the main building's indoor
    # bathrooms.
    #
    # Accepted project fields:
    #
    # externalBathroom
    # externalBath
    # outsideBathroom
    #
    # Example:
    # externalBathroom = True
    # ========================================================

    external_bathroom_requested = (
        _to_bool(
            project.get(
                "externalBathroom"
            )
        )
        or _to_bool(
            project.get(
                "externalBath"
            )
        )
        or _to_bool(
            project.get(
                "outsideBathroom"
            )
        )
    )

    external_bathroom_count = (
        1
        if (
            external_bathroom_requested
            and total_bathrooms > 1
        )
        else 0
    )

    indoor_bathrooms = max(
        1,
        total_bathrooms
        - external_bathroom_count,
    )

    # ========================================================
    # SPECIAL ROOMS / FEATURES
    # ========================================================

    wants_home_office = (
        _contains(
            lifestyle,
            "Home Office",
        )
        or str(
            project.get(
                "workFromHome",
                "",
            )
        ).strip().lower()
        in {
            "yes",
            "always",
            "often",
        }
    )

    wants_garden = _contains(
        lifestyle,
        "Garden",
    )

    wants_prayer_room = _contains(
        lifestyle,
        "Prayer Room",
    )

    wants_balcony = _contains(
        lifestyle,
        "Balcony",
    )

    wants_pool = _contains(
        lifestyle,
        "Swimming Pool",
        "Pool",
    )

    # ========================================================
    # ACCESSIBILITY
    # ========================================================

    wants_ramp = _contains(
        accessibility,
        "Entrance Ramp",
    )

    wants_ground_bedroom = (
        senior_citizens > 0
        or _contains(
            accessibility,
            "Ground-Floor Bedroom",
            "Ground Floor Bedroom",
        )
    )

    wants_accessible_bathroom = (
        senior_citizens > 0
        or _contains(
            accessibility,
            "Accessible Bathroom",
        )
    )

    wheelchair_friendly = (
        _contains(
            accessibility,
            "Wheelchair Friendly",
        )
    )

    # ========================================================
    # USER PREFERENCE WEIGHTS
    # ========================================================

    privacy_score = 0.50
    open_living_score = 0.50
    family_space_score = 0.50
    accessibility_score = 0.20

    if family_size >= 4:
        family_space_score += 0.20

    if children > 0:
        family_space_score += 0.10

    if senior_citizens > 0:
        accessibility_score += 0.40
        privacy_score += 0.10

    if wheelchair_friendly:
        accessibility_score += 0.30

    if wants_ground_bedroom:
        accessibility_score += 0.10

    if wants_accessible_bathroom:
        accessibility_score += 0.10

    if wants_home_office:
        privacy_score += 0.10

    style = str(
        project.get(
            "style",
            "",
        )
    ).strip()

    if style.lower() in {
        "modern",
        "minimalist",
        "contemporary",
    }:
        open_living_score += 0.15

    privacy_score = min(
        max(
            privacy_score,
            0.0,
        ),
        1.0,
    )

    open_living_score = min(
        max(
            open_living_score,
            0.0,
        ),
        1.0,
    )

    family_space_score = min(
        max(
            family_space_score,
            0.0,
        ),
        1.0,
    )

    accessibility_score = min(
        max(
            accessibility_score,
            0.0,
        ),
        1.0,
    )

    # ========================================================
    # HARD CONSTRAINTS
    # ========================================================

    hard_constraints = {
        "bedrooms": (
            bedrooms
        ),

        "bathrooms": (
            total_bathrooms
        ),

        "indoor_bathrooms": (
            indoor_bathrooms
        ),

        "external_bathrooms": (
            external_bathroom_count
        ),

        "floors": floors,
    }

    if building_width is not None:
        hard_constraints[
            "building_width"
        ] = float(
            building_width
        )

    if building_height is not None:
        hard_constraints[
            "building_height"
        ] = float(
            building_height
        )

    # ========================================================
    # INDOOR ROOM REQUIREMENTS
    # ========================================================

    required_spaces = {
        "living_room": True,

        "kitchen": True,

        "dining": True,

        "bedrooms": bedrooms,

        # IMPORTANT:
        # Only indoor bathrooms go into the building.
        "bathrooms": (
            indoor_bathrooms
        ),

        "total_bathrooms": (
            total_bathrooms
        ),

        "stairs": (
            floors > 1
        ),

        "home_office": (
            wants_home_office
        ),

        "prayer_room": (
            wants_prayer_room
        ),

        "balcony": (
            wants_balcony
        ),
    }

    # ========================================================
    # SITE REQUIREMENTS
    # ========================================================

    site = {
        "road_facing": (
            project.get(
                "roadFacing"
            )
        ),

        "plot_shape": (
            project.get(
                "plotShape"
            )
        ),

        "measurement_unit": (
            project.get(
                "measurementUnit"
            )
        ),

        "land_length": (
            _to_float(
                project.get(
                    "landLength"
                )
            )
        ),

        "land_width": (
            _to_float(
                project.get(
                    "landWidth"
                )
            )
        ),

        "latitude": (
            project.get(
                "latitude"
            )
        ),

        "longitude": (
            project.get(
                "longitude"
            )
        ),
    }

    # ========================================================
    # ACCESSIBILITY RULES
    # ========================================================

    accessibility_rules = {
        "entrance_ramp": (
            wants_ramp
        ),

        "ground_floor_bedroom": (
            wants_ground_bedroom
        ),

        "accessible_bathroom": (
            wants_accessible_bathroom
        ),

        "wheelchair_friendly": (
            wheelchair_friendly
        ),
    }

    # ========================================================
    # OUTDOOR / SITE REQUIREMENTS
    # ========================================================

    outdoor = {
        "garden": (
            wants_garden
        ),

        "swimming_pool": (
            wants_pool
        ),

        "parking_spaces": (
            parking_spaces
        ),

        "external_bathroom": {
            "required": (
                external_bathroom_requested
            ),

            "count": (
                external_bathroom_count
            ),

            "outside_access_only": (
                external_bathroom_requested
            ),

            "near_main_entrance": (
                external_bathroom_requested
            ),

            "inside_main_building": (
                False
            ),
        },
    }

    # ========================================================
    # PREFERENCES
    # ========================================================

    preferences = {
        "privacy": round(
            privacy_score,
            3,
        ),

        "open_living": round(
            open_living_score,
            3,
        ),

        "family_space": round(
            family_space_score,
            3,
        ),

        "accessibility": round(
            accessibility_score,
            3,
        ),
    }

    # ========================================================
    # BATHROOM PROGRAM
    #
    # Helpful to all later generators.
    # ========================================================

    bathroom_program = {
        "total": (
            total_bathrooms
        ),

        "indoor": (
            indoor_bathrooms
        ),

        "external": (
            external_bathroom_count
        ),

        "external_required": (
            external_bathroom_requested
        ),

        "outside_access_only": (
            external_bathroom_requested
        ),
    }

    # ========================================================
    # FINAL NORMALIZED REQUIREMENTS
    # ========================================================

    return {
        "project_name": (
            project.get(
                "name",
                "Generated Home",
            )
        ),

        "location": (
            project.get(
                "location"
            )
        ),

        "hard_constraints": (
            hard_constraints
        ),

        "bathroom_program": (
            bathroom_program
        ),

        "family": {
            "size": (
                family_size
            ),

            "children": (
                children
            ),

            "senior_citizens": (
                senior_citizens
            ),

            "pets": pets,
        },

        "required_spaces": (
            required_spaces
        ),

        "accessibility": (
            accessibility_rules
        ),

        "outdoor": (
            outdoor
        ),

        "site": site,

        "preferences": (
            preferences
        ),

        "design": {
            "style": style,

            "materials": (
                materials
            ),

            "sustainability": (
                sustainability
            ),

            "budget": (
                budget
            ),

            "currency": (
                project.get(
                    "currency",
                    "INR",
                )
            ),

            "budget_flexibility": (
                project.get(
                    "budgetFlexibility"
                )
            ),

            "construction_priority": (
                project.get(
                    "constructionPriority"
                )
            ),

            "notes": (
                project.get(
                    "designNotes",
                    "",
                )
            ),
        },
    }