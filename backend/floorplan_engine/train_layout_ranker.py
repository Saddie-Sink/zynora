import json
import random
from pathlib import Path

import joblib
import numpy as np

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
)
from sklearn.model_selection import (
    train_test_split,
)

from floorplan_engine.layout_features import (
    FEATURE_NAMES,
    layout_feature_vector,
)
from floorplan_engine.layout_ranker import (
    score_candidate,
)
from floorplan_engine.structural_generator import (
    generate_structural_candidates,
)


# ============================================================
# CONFIG
# ============================================================


RANDOM_SEED = 42

SCENARIO_COUNT = 400

MODEL_DIR = (
    Path(__file__).resolve().parent.parent
    / "ml_models"
)

MODEL_PATH = (
    MODEL_DIR
    / "layout_ranker_v1.joblib"
)

METADATA_PATH = (
    MODEL_DIR
    / "layout_ranker_v1.json"
)


random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ============================================================
# RANDOM USER PROJECT
# ============================================================


def random_project(
    index: int,
) -> tuple[
    dict,
    float,
    float,
]:

    bedrooms = random.randint(
        2,
        5,
    )

    bathrooms = random.randint(
        max(1, bedrooms - 1),
        bedrooms + 1,
    )

    floors = random.choice(
        [1, 2]
    )

    family_size = random.randint(
        bedrooms,
        bedrooms + 3,
    )

    children = random.randint(
        0,
        min(
            3,
            family_size,
        ),
    )

    seniors = random.randint(
        0,
        1,
    )

    width = random.choice(
        [
            28,
            30,
            32,
            35,
            38,
            40,
            42,
            45,
        ]
    )

    height = random.choice(
        [
            30,
            32,
            35,
            38,
            40,
            42,
            45,
            48,
        ]
    )

    lifestyle_pool = [
        "Garden",
        "Balcony",
        "Home Office",
        "Prayer Room",
        "Swimming Pool",
    ]

    accessibility_pool = [
        "Entrance Ramp",
        "Wheelchair Friendly",
        "Ground-Floor Bedroom",
        "Accessible Bathroom",
    ]

    lifestyle = random.sample(
        lifestyle_pool,
        random.randint(
            0,
            min(
                3,
                len(lifestyle_pool),
            ),
        ),
    )

    accessibility = []

    if seniors > 0:
        accessibility.extend(
            [
                "Ground-Floor Bedroom",
                "Accessible Bathroom",
            ]
        )

    if random.random() < 0.25:
        accessibility.append(
            "Entrance Ramp"
        )

    if random.random() < 0.20:
        accessibility.append(
            "Wheelchair Friendly"
        )

    accessibility = list(
        dict.fromkeys(
            accessibility
        )
    )

    project = {
        "name": (
            f"Training Project {index}"
        ),

        "propertyType": "House",

        "floors": str(floors),

        "bedrooms": str(
            bedrooms
        ),

        "bathrooms": str(
            bathrooms
        ),

        "familySize": str(
            family_size
        ),

        "children": str(
            children
        ),

        "seniorCitizens": str(
            seniors
        ),

        "pets": str(
            random.randint(
                0,
                2,
            )
        ),

        "parkingSpaces": str(
            random.randint(
                1,
                3,
            )
        ),

        "workFromHome": (
            random.choice(
                [
                    "No",
                    "Sometimes",
                    "Often",
                    "Yes",
                ]
            )
        ),

        "lifestyleFeatures": (
            lifestyle
        ),

        "accessibilityFeatures": (
            accessibility
        ),

        "roadFacing": (
            random.choice(
                [
                    "North",
                    "South",
                    "East",
                    "West",
                ]
            )
        ),

        "plotShape": (
            random.choice(
                [
                    "Square",
                    "Rectangle",
                ]
            )
        ),

        "measurementUnit": (
            "Feet"
        ),

        "landWidth": str(
            width + random.randint(
                10,
                25,
            )
        ),

        "landLength": str(
            height + random.randint(
                10,
                25,
            )
        ),

        "style": (
            random.choice(
                [
                    "Modern",
                    "Contemporary",
                    "Minimalist",
                    "Traditional",
                ]
            )
        ),

        "budget": str(
            random.randint(
                4_000_000,
                15_000_000,
            )
        ),

        "currency": "INR",
    }

    return (
        project,
        float(width),
        float(height),
    )


# ============================================================
# TRAINING DATA
# ============================================================


def build_training_dataset():
    x_rows = []
    y_rows = []

    candidate_count = 0
    skipped = 0

    for index in range(
        SCENARIO_COUNT
    ):
        (
            project,
            width,
            height,
        ) = random_project(
            index
        )

        bedrooms = int(
            project["bedrooms"]
        )

        bathrooms = int(
            project["bathrooms"]
        )

        floors = int(
            project["floors"]
        )

        try:
            candidates = (
                generate_structural_candidates(
                    target_width=width,
                    target_height=height,
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                    floors=floors,
                    project=project,
                )
            )

        except Exception as error:
            skipped += 1

            print(
                "Skipped scenario",
                index,
                ":",
                error,
            )

            continue

        for candidate in candidates:

            feature_vector = (
                layout_feature_vector(
                    candidate
                )
            )

            baseline = (
                score_candidate(
                    candidate
                )
            )

            target_score = (
                baseline[
                    "score_normalized"
                ]
            )

            x_rows.append(
                feature_vector
            )

            y_rows.append(
                target_score
            )

            candidate_count += 1

    x = np.asarray(
        x_rows,
        dtype=float,
    )

    y = np.asarray(
        y_rows,
        dtype=float,
    )

    print()
    print(
        "Training scenarios:",
        SCENARIO_COUNT,
    )

    print(
        "Generated candidates:",
        candidate_count,
    )

    print(
        "Skipped scenarios:",
        skipped,
    )

    print(
        "Feature count:",
        len(FEATURE_NAMES),
    )

    return x, y


# ============================================================
# TRAIN MODEL
# ============================================================


def train():

    print(
        "Building ZYNORA layout "
        "ranking dataset..."
    )

    x, y = (
        build_training_dataset()
    )

    if len(x) < 30:
        raise RuntimeError(
            "Not enough training "
            "examples were generated."
        )

    (
        x_train,
        x_test,
        y_train,
        y_test,
    ) = train_test_split(
        x,
        y,
        test_size=0.20,
        random_state=(
            RANDOM_SEED
        ),
    )

    model = ExtraTreesRegressor(
        n_estimators=300,
        random_state=(
            RANDOM_SEED
        ),
        n_jobs=-1,
        min_samples_leaf=2,
    )

    print()
    print(
        "Training Extra Trees "
        "layout ranker..."
    )

    model.fit(
        x_train,
        y_train,
    )

    predictions = model.predict(
        x_test
    )

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    print()
    print(
        "=============================="
    )

    print(
        "ZYNORA ML LAYOUT RANKER"
    )

    print(
        "=============================="
    )

    print(
        "Training rows:",
        len(x_train),
    )

    print(
        "Testing rows:",
        len(x_test),
    )

    print(
        "MAE:",
        round(
            mae,
            4,
        ),
    )

    print(
        "R2:",
        round(
            r2,
            4,
        ),
    )

    # --------------------------------------------------------
    # FEATURE IMPORTANCE
    # --------------------------------------------------------

    importance = sorted(
        zip(
            FEATURE_NAMES,
            model.feature_importances_,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    print()
    print(
        "Top ML features:"
    )

    for (
        feature_name,
        score,
    ) in importance[:8]:

        print(
            " -",
            feature_name,
            ":",
            round(
                float(score),
                4,
            ),
        )

    # --------------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------------

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    metadata = {
        "model": (
            "ExtraTreesRegressor"
        ),

        "version": (
            "layout-ranker-v1"
        ),

        "training_scenarios": (
            SCENARIO_COUNT
        ),

        "training_candidates": (
            int(len(x))
        ),

        "feature_names": (
            FEATURE_NAMES
        ),

        "mae": float(mae),

        "r2": float(r2),

        "random_seed": (
            RANDOM_SEED
        ),

        "label_source": (
            "ZYNORA personalized "
            "baseline synthetic labels"
        ),

        "notes": (
            "Initial ML ranker for "
            "demo. Future versions "
            "should incorporate real "
            "user preference selections."
        ),
    }

    METADATA_PATH.write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "Model saved:"
    )

    print(
        MODEL_PATH
    )

    print()
    print(
        "Metadata saved:"
    )

    print(
        METADATA_PATH
    )


if __name__ == "__main__":
    train()