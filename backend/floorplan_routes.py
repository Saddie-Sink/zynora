from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from floorplan_engine.dataset_loader import (
    load_floor_plans,
)
from floorplan_engine.plan_retriever import (
    retrieve_best_plan,
)
from floorplan_engine.plan_validator import (
    validate_plan,
    validate_requirements,
)
from floorplan_engine.furniture_generator import (
    generate_furniture,
)
from floorplan_engine.structural_generator import (
    generate_structural_candidates,
)
from floorplan_engine.ml_layout_ranker import (
    rank_candidates_ml,
)


router = APIRouter(
    prefix="/api/floor-plans",
    tags=["Floor Plans"],
)


# ============================================================
# REQUEST MODELS
# ============================================================


class BuildingRequest(BaseModel):
    length: float = Field(gt=0)
    width: float = Field(gt=0)


class SiteLayoutRequest(BaseModel):
    building: BuildingRequest


class FloorPlanGenerateRequest(BaseModel):
    project: dict[str, Any]
    site_layout: SiteLayoutRequest


# ============================================================
# HELPERS
# ============================================================


def get_integer_value(
    data: dict[str, Any],
    keys: list[str],
    default: int,
) -> int:

    for key in keys:
        value = data.get(key)

        if value is None or value == "":
            continue

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            continue

    return default


def validate_candidate(
    candidate: dict[str, Any],
    bedrooms: int,
    bathrooms: int,
    floors: int,
) -> dict[str, Any]:

    geometry_errors = validate_plan(
        candidate
    )

    requirement_errors = (
        validate_requirements(
            plan=candidate,
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

    errors = (
        geometry_errors
        + requirement_errors
    )

    return {
        "valid": len(errors) == 0,
        "geometry_errors": (
            geometry_errors
        ),
        "requirement_errors": (
            requirement_errors
        ),
        "errors": errors,
    }


def attach_furniture(
    candidate: dict[str, Any],
) -> dict[str, Any]:

    candidate["furniture"] = (
        generate_furniture(
            rooms=candidate.get(
                "rooms",
                [],
            )
        )
    )

    return candidate


# ============================================================
# GENERATE THREE FLOOR PLANS
# ============================================================


@router.post("/generate")
def generate_floor_plan(
    request: FloorPlanGenerateRequest,
) -> dict[str, Any]:

    print()
    print(
        "========== FLOOR PLAN REQUEST =========="
    )

    print(
        request.model_dump()
    )

    print(
        "========================================"
    )

    project = request.project

    building = (
        request.site_layout.building
    )

    bedrooms = get_integer_value(
        data=project,
        keys=[
            "bedrooms",
            "numberOfBedrooms",
        ],
        default=3,
    )

    bathrooms = get_integer_value(
        data=project,
        keys=[
            "bathrooms",
            "numberOfBathrooms",
        ],
        default=1,
    )

    floors = get_integer_value(
        data=project,
        keys=[
            "floors",
            "numberOfFloors",
        ],
        default=1,
    )

    target_width = float(
        building.length
    )

    target_height = float(
        building.width
    )

    print()
    print(
        "Parsed values:"
    )

    print(
        "Width:",
        target_width,
    )

    print(
        "Height:",
        target_height,
    )

    print(
        "Bedrooms:",
        bedrooms,
    )

    print(
        "Bathrooms:",
        bathrooms,
    )

    print(
        "Floors:",
        floors,
    )

    try:

        # ====================================================
        # STEP 1
        # LOAD REFERENCE FLOOR PLANS
        # ====================================================

        print()
        print(
            "STEP 1: Loading reference plans"
        )

        plans = load_floor_plans()

        print(
            "Loaded plan count:",
            len(plans),
        )

        # ====================================================
        # STEP 2
        # FIND REFERENCE PLAN
        #
        # This does NOT become the final design.
        # It is retained as a useful reference/template.
        # ====================================================

        print()
        print(
            "STEP 2: Finding closest reference plan"
        )

        selected_plan = (
            retrieve_best_plan(
                plans=plans,
                requested_width=(
                    target_width
                ),
                requested_height=(
                    target_height
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

        print(
            "Reference plan:",
            selected_plan.get(
                "name",
                selected_plan.get(
                    "id"
                ),
            ),
        )

        print(
            "Reference match type:",
            selected_plan.get(
                "match_type"
            ),
        )

        # ====================================================
        # STEP 3
        # GENERATE THREE PERSONALIZED OPTIONS
        # ====================================================

        print()
        print(
            "STEP 3: Generating "
            "three personalized floor plans"
        )

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

        print(
            "Generated candidate count:",
            len(candidates),
        )

        if len(candidates) < 3:
            raise ValueError(
                "ZYNORA could not generate "
                "three candidate designs."
            )

        # ====================================================
        # STEP 4
        # VALIDATE EVERY OPTION
        # ====================================================

        print()
        print(
            "STEP 4: Validating candidates"
        )

        valid_candidates: list[
            dict[str, Any]
        ] = []

        rejected_candidates: list[
            dict[str, Any]
        ] = []

        for candidate in candidates:

            candidate_id = candidate.get(
                "id",
                "unknown",
            )

            title = candidate.get(
                "title",
                candidate_id,
            )

            validation = (
                validate_candidate(
                    candidate=(
                        candidate
                    ),
                    bedrooms=(
                        bedrooms
                    ),
                    bathrooms=(
                        bathrooms
                    ),
                    floors=(
                        floors
                    ),
                )
            )

            candidate[
                "validation"
            ] = validation

            print()
            print(
                title
            )

            print(
                "Geometry errors:",
                validation[
                    "geometry_errors"
                ],
            )

            print(
                "Requirement errors:",
                validation[
                    "requirement_errors"
                ],
            )

            if validation["valid"]:
                valid_candidates.append(
                    candidate
                )

            else:
                rejected_candidates.append(
                    {
                        "id": (
                            candidate_id
                        ),
                        "title": (
                            title
                        ),
                        "errors": (
                            validation[
                                "errors"
                            ]
                        ),
                    }
                )

        if not valid_candidates:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": (
                        "ZYNORA generated "
                        "floor-plan options, "
                        "but none passed "
                        "validation."
                    ),
                    "rejected_candidates": (
                        rejected_candidates
                    ),
                },
            )

        # ====================================================
        # STEP 5
        # ADD FURNITURE
        # ====================================================

        print()
        print(
            "STEP 5: Generating furniture"
        )

        for candidate in valid_candidates:
            attach_furniture(
                candidate
            )

        # ====================================================
        # STEP 6
        # ML RANKING
        # ====================================================

        print()
        print(
            "STEP 6: Ranking candidates "
            "with ML"
        )

        ranked = rank_candidates_ml(
            valid_candidates
        )

        ranked_candidates: list[
            dict[str, Any]
        ] = []

        for item in ranked:

            candidate = item[
                "candidate"
            ]

            ml_ranking = item[
                "ml_ranking"
            ]

            candidate[
                "ml_ranking"
            ] = ml_ranking

            candidate[
                "recommended"
            ] = (
                ml_ranking.get(
                    "rank"
                )
                == 1
            )

            ranked_candidates.append(
                candidate
            )

            print(
                "#"
                + str(
                    ml_ranking.get(
                        "rank"
                    )
                ),
                candidate.get(
                    "title"
                ),
                "=",
                ml_ranking.get(
                    "ml_score"
                ),
                "%",
            )

        # ====================================================
        # STEP 7
        # ADD SHARED METADATA
        # ====================================================

        reference_metadata = {
            "id": (
                selected_plan.get(
                    "id"
                )
            ),
            "name": (
                selected_plan.get(
                    "name",
                    "Unnamed plan",
                )
            ),
            "source": (
                selected_plan.get(
                    "source",
                    "ZYNORA Curated",
                )
            ),
            "match_type": (
                selected_plan.get(
                    "match_type"
                )
            ),
            "match_score": (
                selected_plan.get(
                    "match_score"
                )
            ),
        }

        requested_configuration = {
            "width": (
                target_width
            ),
            "height": (
                target_height
            ),
            "bedrooms": (
                bedrooms
            ),
            "bathrooms": (
                bathrooms
            ),
            "floors": (
                floors
            ),
        }

        for candidate in (
            ranked_candidates
        ):

            candidate[
                "matched_reference_plan"
            ] = (
                reference_metadata
            )

            candidate[
                "requested_configuration"
            ] = (
                requested_configuration
            )

        # ====================================================
        # STEP 8
        # RECOMMENDED PLAN
        # ====================================================

        recommended_plan = (
            ranked_candidates[0]
        )

        recommended_id = (
            recommended_plan.get(
                "id"
            )
        )

        print()
        print(
            "STEP 7: Generation complete"
        )

        print(
            "Recommended candidate:",
            recommended_id,
        )

        print(
            "Recommended score:",
            recommended_plan.get(
                "ml_ranking",
                {},
            ).get(
                "ml_score"
            ),
        )

        # ====================================================
        # BACKWARD COMPATIBILITY
        #
        # The response contains the recommended plan's
        # normal fields at the top level so the OLD frontend
        # can still read things like:
        #
        # rooms
        # doors
        # windows
        # floor_plans
        #
        # New frontend code will use:
        #
        # candidates
        # recommended_candidate_id
        # ====================================================

        response = dict(
            recommended_plan
        )

        response[
            "generation_mode"
        ] = "candidate_selection"

        response[
            "candidate_count"
        ] = len(
            ranked_candidates
        )

        response[
            "recommended_candidate_id"
        ] = recommended_id

        response[
            "candidates"
        ] = ranked_candidates

        response[
            "reference_plan"
        ] = reference_metadata

        response[
            "requested_configuration"
        ] = requested_configuration

        response[
            "rejected_candidates"
        ] = rejected_candidates

        response[
            "ml_model"
        ] = {
            "name": (
                "ExtraTreesRegressor"
            ),
            "version": (
                "layout-ranker-v1"
            ),
            "feature_count": 16,
        }

        return response

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except HTTPException:
        raise

    except FileNotFoundError as error:

        print(
            "Floor-plan FileNotFoundError:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "A required ZYNORA "
                    "floor-plan or ML file "
                    "could not be found."
                ),
                "error": str(error),
            },
        ) from error

    except ValueError as error:

        print(
            "Floor-plan ValueError:",
            repr(error),
        )

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "The floor-plan request "
                    "could not be processed."
                ),
                "error": str(error),
            },
        ) from error

    except Exception as error:

        print(
            "Floor-plan generation error:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "An unexpected error "
                    "occurred while generating "
                    "the ZYNORA floor plans."
                ),
                "error": str(error),
                "error_type": (
                    type(error).__name__
                ),
            },
        ) from error