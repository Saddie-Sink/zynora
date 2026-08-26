from typing import Any

from floorplan_engine.layout_features import (
    extract_layout_features,
)


# ============================================================
# HELPERS
# ============================================================


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )


def _preference_similarity(
    actual: float,
    desired: float,
) -> float:
    """
    Measures how closely a generated candidate
    matches a user's preference weight.
    """

    difference = abs(
        actual - desired
    )

    return _clamp(
        1.0 - difference
    )


def _area_quality(
    area: float,
    ideal_min: float,
    ideal_max: float,
) -> float:
    """
    Returns a 0-1 score for room size.

    Areas inside the preferred interval receive
    full marks. Very small or extremely oversized
    rooms receive lower scores.
    """

    if area <= 0:
        return 0.0

    if ideal_min <= area <= ideal_max:
        return 1.0

    if area < ideal_min:
        return _clamp(
            area / ideal_min
        )

    oversize = (
        area - ideal_max
    )

    tolerance = ideal_max

    return _clamp(
        1.0 - oversize / tolerance
    )


# ============================================================
# STRATEGY BONUS
# ============================================================


def _strategy_alignment(
    candidate: dict[str, Any],
    preferences: dict[str, Any],
) -> float:

    strategy = str(
        candidate.get(
            "strategy",
            "",
        )
    )

    privacy = float(
        preferences.get(
            "privacy",
            0.5,
        )
    )

    open_living = float(
        preferences.get(
            "open_living",
            0.5,
        )
    )

    family_space = float(
        preferences.get(
            "family_space",
            0.5,
        )
    )

    if strategy == "balanced":
        average = (
            privacy
            + open_living
            + family_space
        ) / 3

        return _clamp(
            1.0
            - abs(
                average - 0.65
            )
        )

    if strategy == "open_living":
        return _clamp(
            (
                open_living * 0.65
                + family_space * 0.35
            )
        )

    if strategy == "privacy":
        return _clamp(
            (
                privacy * 0.75
                + family_space * 0.25
            )
        )

    return 0.5


# ============================================================
# REASONS
# ============================================================


def _build_reasons(
    candidate: dict[str, Any],
    features: dict[str, float],
    preferences: dict[str, Any],
) -> list[str]:

    reasons: list[str] = []

    strategy = str(
        candidate.get(
            "strategy",
            "",
        )
    )

    if strategy == "balanced":
        reasons.append(
            "Balanced allocation between "
            "family, social and private spaces."
        )

    elif strategy == "open_living":
        reasons.append(
            "Prioritizes larger connected "
            "living and family spaces."
        )

    elif strategy == "privacy":
        reasons.append(
            "Prioritizes private bedrooms "
            "and quieter personal spaces."
        )

    if (
        features.get(
            "accessibility_score",
            0,
        )
        >= 0.9
    ):
        reasons.append(
            "Strong match for the requested "
            "accessibility requirements."
        )

    if (
        features.get(
            "natural_light_score",
            0,
        )
        >= 0.8
    ):
        reasons.append(
            "Good exterior-window and "
            "natural-light potential."
        )

    if (
        features.get(
            "circulation_score",
            0,
        )
        >= 0.7
    ):
        reasons.append(
            "Uses circulation space efficiently."
        )

    desired_open = float(
        preferences.get(
            "open_living",
            0.5,
        )
    )

    if (
        desired_open >= 0.65
        and features.get(
            "open_living_score",
            0,
        )
        >= 0.8
    ):
        reasons.append(
            "Matches the user's preference "
            "for open living."
        )

    desired_privacy = float(
        preferences.get(
            "privacy",
            0.5,
        )
    )

    if (
        desired_privacy >= 0.65
        and features.get(
            "privacy_score",
            0,
        )
        >= 0.65
    ):
        reasons.append(
            "Provides stronger separation "
            "for private areas."
        )

    return reasons[:4]


# ============================================================
# ONE CANDIDATE SCORE
# ============================================================


def score_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:

    features = (
        extract_layout_features(
            candidate
        )
    )

    requirements = candidate.get(
        "requirements",
        {},
    )

    preferences = requirements.get(
        "preferences",
        {},
    )

    desired_privacy = float(
        preferences.get(
            "privacy",
            0.5,
        )
    )

    desired_open_living = float(
        preferences.get(
            "open_living",
            0.5,
        )
    )

    desired_family_space = float(
        preferences.get(
            "family_space",
            0.5,
        )
    )

    desired_accessibility = float(
        preferences.get(
            "accessibility",
            0.5,
        )
    )

    # --------------------------------------------------------
    # USER-PREFERENCE MATCH
    # --------------------------------------------------------

    privacy_match = (
        _preference_similarity(
            features[
                "privacy_score"
            ],
            desired_privacy,
        )
    )

    open_match = (
        _preference_similarity(
            features[
                "open_living_score"
            ],
            desired_open_living,
        )
    )

    family_match = (
        _preference_similarity(
            features[
                "family_space_score"
            ],
            desired_family_space,
        )
    )

    accessibility_match = (
        _preference_similarity(
            features[
                "accessibility_score"
            ],
            desired_accessibility,
        )
    )

    # --------------------------------------------------------
    # ARCHITECTURAL QUALITY
    # --------------------------------------------------------

    circulation_quality = features[
        "circulation_score"
    ]

    light_quality = features[
        "natural_light_score"
    ]

    bedroom_size_quality = (
        _area_quality(
            features[
                "average_bedroom_area"
            ],
            ideal_min=100,
            ideal_max=220,
        )
    )

    bathroom_size_quality = (
        _area_quality(
            features[
                "average_bathroom_area"
            ],
            ideal_min=35,
            ideal_max=90,
        )
    )

    strategy_quality = (
        _strategy_alignment(
            candidate,
            preferences,
        )
    )

    # --------------------------------------------------------
    # FINAL BASELINE SCORE
    #
    # Later ML will learn/replace these weights.
    # --------------------------------------------------------

    raw_score = (
        privacy_match * 0.12
        + open_match * 0.15
        + family_match * 0.15
        + accessibility_match * 0.13
        + circulation_quality * 0.12
        + light_quality * 0.08
        + bedroom_size_quality * 0.08
        + bathroom_size_quality * 0.07
        + strategy_quality * 0.10
    )

    raw_score = _clamp(
        raw_score
    )

    score_100 = round(
        raw_score * 100,
        1,
    )

    reasons = _build_reasons(
        candidate,
        features,
        preferences,
    )

    return {
        "candidate_id": (
            candidate.get("id")
        ),

        "title": candidate.get(
            "title",
            candidate.get(
                "name",
                "ZYNORA Design",
            ),
        ),

        "strategy": candidate.get(
            "strategy"
        ),

        "score": score_100,

        "score_normalized": round(
            raw_score,
            4,
        ),

        "features": features,

        "preference_match": {
            "privacy": round(
                privacy_match,
                4,
            ),

            "open_living": round(
                open_match,
                4,
            ),

            "family_space": round(
                family_match,
                4,
            ),

            "accessibility": round(
                accessibility_match,
                4,
            ),
        },

        "reasons": reasons,

        "ranking_method": (
            "personalized-baseline-v1"
        ),
    }


# ============================================================
# RANK ALL THREE
# ============================================================


def rank_candidates(
    candidates: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:

    scored: list[
        dict[str, Any]
    ] = []

    for candidate in candidates:

        result = score_candidate(
            candidate
        )

        scored.append(
            {
                "candidate": candidate,
                "ranking": result,
            }
        )

    scored.sort(
        key=lambda item: (
            item["ranking"][
                "score"
            ]
        ),
        reverse=True,
    )

    for index, item in enumerate(
        scored,
        start=1,
    ):
        item["ranking"][
            "rank"
        ] = index

        item["candidate"][
            "ranking"
        ] = item["ranking"]

        item["candidate"][
            "recommended"
        ] = (
            index == 1
        )

    return scored