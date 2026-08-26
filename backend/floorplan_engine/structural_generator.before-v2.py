from typing import Any

from floorplan_engine.requirement_engine import (
    build_requirements,
)
from floorplan_engine.architectural_generator import (
    generate_architectural_candidates,
)
from floorplan_engine.architectural_openings import (
    apply_architectural_openings,
)


# ============================================================
# ZYNORA LIVE STRUCTURAL GENERATOR
#
# This file is now the bridge between:
#
# user requirements
#       ↓
# requirement_engine.py
#       ↓
# architectural_generator.py
#       ↓
# architectural_openings.py
#       ↓
# floorplan_routes.py
#
# The old percentage-based row packing is no longer used.
# ============================================================


def _positive_int(
    value: Any,
    fallback: int,
) -> int:

    try:
        number = int(value)

        if number > 0:
            return number

    except (
        TypeError,
        ValueError,
    ):
        pass

    return fallback


# ============================================================
# ATTACH SHARED METADATA
# ============================================================


def _finalize_candidate(
    candidate: dict[str, Any],
    requirements: dict[str, Any],
    requested_bedrooms: int,
    requested_bathrooms: int,
    requested_floors: int,
) -> dict[str, Any]:

    bathroom_program = (
        requirements.get(
            "bathroom_program",
            {},
        )
    )

    indoor_bathrooms = (
        _positive_int(
            bathroom_program.get(
                "indoor"
            ),
            requested_bathrooms,
        )
    )

    external_bathrooms = max(
        0,
        int(
            bathroom_program.get(
                "external",
                0,
            )
            or 0
        ),
    )

    # --------------------------------------------------------
    # IMPORTANT
    #
    # "bathrooms" remains the TOTAL user-requested count.
    #
    # This keeps the existing API and requirement validator
    # compatible.
    #
    # Actual indoor bathroom geometry is stored separately.
    # --------------------------------------------------------

    candidate["bedrooms"] = (
        requested_bedrooms
    )

    candidate["bathrooms"] = (
        requested_bathrooms
    )

    candidate["floors"] = (
        requested_floors
    )

    candidate[
        "indoor_bathrooms"
    ] = indoor_bathrooms

    candidate[
        "external_bathrooms"
    ] = external_bathrooms

    candidate[
        "bathroom_program"
    ] = bathroom_program

    candidate[
        "external_bathroom_required"
    ] = bool(
        bathroom_program.get(
            "external_required",
            False,
        )
    )

    candidate[
        "external_bathroom"
    ] = {
        "required": bool(
            bathroom_program.get(
                "external_required",
                False,
            )
        ),
        "count": (
            external_bathrooms
        ),
        "outside_access_only": bool(
            bathroom_program.get(
                "outside_access_only",
                False,
            )
        ),
        "status": (
            "site_planning_required"
            if external_bathrooms > 0
            else "not_requested"
        ),
    }

    candidate[
        "requirements"
    ] = requirements

    candidate[
        "generation_version"
    ] = (
        "zynora-architectural-live-v1"
    )

    candidate[
        "generated_from_requirements"
    ] = True

    candidate[
        "requires_structural_generation"
    ] = False

    return candidate


# ============================================================
# THREE PERSONALIZED ARCHITECTURAL CANDIDATES
# ============================================================


def generate_structural_candidates(
    target_width: float,
    target_height: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    project: dict[str, Any],
) -> list[dict[str, Any]]:

    if target_width <= 0:
        raise ValueError(
            "Target width must be greater than zero."
        )

    if target_height <= 0:
        raise ValueError(
            "Target height must be greater than zero."
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

    # ========================================================
    # STEP 1
    # NORMALIZE USER REQUIREMENTS
    # ========================================================

    requirements = build_requirements(
        project=project,
        building_width=(
            target_width
        ),
        building_height=(
            target_height
        ),
    )

    # Explicit API arguments remain authoritative.

    requirements[
        "hard_constraints"
    ]["bedrooms"] = bedrooms

    requirements[
        "hard_constraints"
    ]["bathrooms"] = bathrooms

    requirements[
        "hard_constraints"
    ]["floors"] = floors

    # ========================================================
    # STEP 2
    # DETERMINE INDOOR / EXTERNAL BATHROOM SPLIT
    # ========================================================

    bathroom_program = (
        requirements.get(
            "bathroom_program",
            {},
        )
    )

    indoor_bathrooms = (
        _positive_int(
            bathroom_program.get(
                "indoor"
            ),
            bathrooms,
        )
    )

    # Never generate more indoor bathrooms than requested.

    indoor_bathrooms = min(
        indoor_bathrooms,
        bathrooms,
    )

    # ========================================================
    # STEP 3
    # GENERATE A / B / C ARCHITECTURAL OPTIONS
    # ========================================================

    candidates = (
        generate_architectural_candidates(
            width=target_width,
            height=target_height,
            bedrooms=bedrooms,

            # IMPORTANT:
            # Architectural geometry receives only
            # indoor bathroom count.
            bathrooms=(
                indoor_bathrooms
            ),

            floors=floors,
            project=project,
            requirements=requirements,
        )
    )

    if not candidates:
        raise ValueError(
            "Architectural generator returned no candidates."
        )

    # ========================================================
    # STEP 4
    # APPLY REAL SHARED-WALL OPENINGS
    # ========================================================

    completed_candidates: list[
        dict[str, Any]
    ] = []

    for candidate in candidates:

        candidate = (
            apply_architectural_openings(
                candidate
            )
        )

        candidate = (
            _finalize_candidate(
                candidate=(
                    candidate
                ),
                requirements=(
                    requirements
                ),
                requested_bedrooms=(
                    bedrooms
                ),
                requested_bathrooms=(
                    bathrooms
                ),
                requested_floors=(
                    floors
                ),
            )
        )

        completed_candidates.append(
            candidate
        )

    return completed_candidates


# ============================================================
# BACKWARD-COMPATIBLE SINGLE PLAN
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

    if not candidates:
        raise ValueError(
            "No architectural floor plans were generated."
        )

    return candidates[0]