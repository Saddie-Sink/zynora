from pathlib import Path
from typing import Any

import joblib
import numpy as np

from floorplan_engine.layout_features import (
    FEATURE_NAMES,
    extract_layout_features,
    layout_feature_vector,
)


# ============================================================
# MODEL LOCATION
# ============================================================


MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "ml_models"
    / "layout_ranker_v1.joblib"
)


_model = None


# ============================================================
# LOAD MODEL
# ============================================================


def load_layout_model():
    global _model

    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Layout ranking model not found: {MODEL_PATH}"
        )

    _model = joblib.load(
        MODEL_PATH
    )

    return _model


# ============================================================
# PREDICTION EXPLANATIONS
# ============================================================


def _build_ml_reasons(
    candidate: dict[str, Any],
    features: dict[str, float],
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
            "Balanced distribution of social, "
            "family and private spaces."
        )

    elif strategy == "open_living":
        reasons.append(
            "Provides a stronger open-living "
            "and connected family layout."
        )

    elif strategy == "privacy":
        reasons.append(
            "Provides stronger private-space "
            "allocation and bedroom separation."
        )

    if (
        features.get(
            "circulation_score",
            0,
        )
        >= 0.70
    ):
        reasons.append(
            "Efficient circulation between spaces."
        )

    if (
        features.get(
            "accessibility_score",
            0,
        )
        >= 0.90
    ):
        reasons.append(
            "Strong accessibility support."
        )

    if (
        features.get(
            "natural_light_score",
            0,
        )
        >= 0.90
    ):
        reasons.append(
            "Strong natural-light potential."
        )

    if (
        features.get(
            "privacy_score",
            0,
        )
        >= 0.70
    ):
        reasons.append(
            "Good private-space allocation."
        )

    if (
        features.get(
            "open_living_score",
            0,
        )
        >= 0.90
    ):
        reasons.append(
            "Strong open-living configuration."
        )

    return reasons[:4]


# ============================================================
# PREDICT ONE CANDIDATE
# ============================================================


def predict_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:

    model = load_layout_model()

    vector = layout_feature_vector(
        candidate
    )

    x = np.asarray(
        [vector],
        dtype=float,
    )

    prediction = float(
        model.predict(x)[0]
    )

    prediction = max(
        0.0,
        min(
            1.0,
            prediction,
        ),
    )

    features = extract_layout_features(
        candidate
    )

    return {
        "candidate_id": candidate.get(
            "id"
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

        "ml_score": round(
            prediction * 100,
            1,
        ),

        "ml_score_normalized": round(
            prediction,
            4,
        ),

        "features": features,

        "reasons": _build_ml_reasons(
            candidate,
            features,
        ),

        "ranking_method": (
            "extra-trees-layout-ranker-v1"
        ),
    }


# ============================================================
# RANK ALL CANDIDATES
# ============================================================


def rank_candidates_ml(
    candidates: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:

    ranked: list[
        dict[str, Any]
    ] = []

    for candidate in candidates:

        prediction = predict_candidate(
            candidate
        )

        ranked.append(
            {
                "candidate": candidate,
                "ml_ranking": prediction,
            }
        )

    ranked.sort(
        key=lambda item: (
            item[
                "ml_ranking"
            ][
                "ml_score"
            ]
        ),
        reverse=True,
    )

    for rank, item in enumerate(
        ranked,
        start=1,
    ):

        ranking = item[
            "ml_ranking"
        ]

        ranking["rank"] = rank

        candidate = item[
            "candidate"
        ]

        candidate[
            "ml_ranking"
        ] = ranking

        candidate[
            "recommended"
        ] = (
            rank == 1
        )

    return ranked


# ============================================================
# MODEL INFORMATION
# ============================================================


def get_model_info() -> dict[str, Any]:

    model = load_layout_model()

    return {
        "loaded": True,
        "model_type": (
            model.__class__.__name__
        ),
        "model_path": str(
            MODEL_PATH
        ),
        "feature_count": len(
            FEATURE_NAMES
        ),
        "features": FEATURE_NAMES,
    }