"""Equivalence tests: backend canonical_builder.py vs frontend wallTopology.js.

Per the P0 acceptance criteria, this does NOT require byte-for-byte JSON
equality (ordering/serialization is allowed to differ). Instead it checks
*structural/geometric equivalence*: same wall count, same endpoints within a
tight tolerance, same openings (position/size), same merge/snap statistics,
and the same canonical FloorPlanDocument shape for the same input.

The reference values in ``_js_reference_output.json`` were captured by
running the actual frontend implementation:

    cd frontend && node tests/dump_reference_output.mjs

against the same two fixtures used by frontend/tests/wallTopology.test.js
("merges duplicate walls..." and "creates valid canonical FloorPlanJSON...").
If wallTopology.js changes, regenerate this fixture file the same way.

KNOWN GAP (see canonical_builder.py module docstring): the JS "outline
repair via polygon union" branch is not ported. Fixtures A and B below do not
exercise that branch (no rooms fall outside the outline), so they do not
test it -- this is a real, documented limitation, not something hidden by
these tests.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from floorplan_engine.canonical_builder import (
    build_canonical_document,
    create_floor_plan_document,
    process_wall_topology,
)

FIXTURE_PATH = Path(__file__).parent / "_js_reference_output.json"


@pytest.fixture(scope="module")
def js_reference() -> dict:
    with FIXTURE_PATH.open() as handle:
        return json.load(handle)


def wall(wall_id, x1, z1, x2, z2, **overrides):
    base = {
        "id": wall_id,
        "x1": x1,
        "z1": z1,
        "x2": x2,
        "z2": z2,
        "height": 2.8,
        "thickness": 0.16,
        "color": "#eee9e1",
        "isExterior": True,
        "openings": [],
    }
    base.update(overrides)
    return base


OUTLINE = [
    {"x": 0, "z": 0},
    {"x": 10, "z": 0},
    {"x": 10, "z": 7},
    {"x": 0, "z": 7},
]


def approx(actual, expected, tol=1e-3):
    return math.isclose(actual, expected, abs_tol=tol)


def point_close(actual: dict, expected: dict, tol=1e-3) -> bool:
    return approx(actual["x"], expected["x"], tol) and approx(
        actual["z"], expected["z"], tol
    )


def find_wall(walls, wall_id):
    for w in walls:
        if w["id"] == wall_id:
            return w
    raise AssertionError(f"wall {wall_id!r} not found among {[w['id'] for w in walls]}")


# ============================================================
# FIXTURE A: duplicate/collinear wall merge + opening preservation
# ============================================================


def _fixture_a_walls():
    return [
        wall(
            "south",
            0,
            0,
            10,
            0,
            openings=[
                {
                    "id": "front-door",
                    "type": "door",
                    "start": 4.5,
                    "end": 5.5,
                    "center": 5,
                    "width": 1,
                    "bottom": 0,
                    "top": 2.1,
                    "height": 2.1,
                }
            ],
        ),
        wall("south-copy", 0.001, 0.001, 10.001, 0.001),
        wall("east", 10, 0, 10, 7),
        wall("north", 10, 7, 0, 7),
        wall("west", 0, 7, 0, 0),
    ]


class TestFixtureA:
    def test_duplicate_wall_removed(self, js_reference):
        topology = process_wall_topology(_fixture_a_walls(), OUTLINE)
        expected_stats = js_reference["fixtureA"]["stats"]

        assert topology["stats"]["sourceWalls"] == expected_stats["sourceWalls"]
        assert topology["stats"]["mergedWalls"] == expected_stats["mergedWalls"]
        assert (
            topology["stats"]["duplicateWallsRemoved"]
            == expected_stats["duplicateWallsRemoved"]
        )
        assert topology["stats"]["exteriorWalls"] == expected_stats["exteriorWalls"]
        assert (
            topology["stats"]["exteriorShellClosed"]
            == expected_stats["exteriorShellClosed"]
        )

    def test_merged_wall_geometry_matches_js(self, js_reference):
        """The merged 'south' wall's endpoints/opening must match the JS
        reference within a tight tolerance -- this is the core geometric
        equivalence check, not just a count check."""
        topology = process_wall_topology(_fixture_a_walls(), OUTLINE)
        py_south = find_wall(topology["walls"], "south")
        js_south = find_wall(js_reference["fixtureA"]["walls"], "south")

        assert point_close({"x": py_south["x1"], "z": py_south["z1"]}, {"x": js_south["x1"], "z": js_south["z1"]})
        assert point_close({"x": py_south["x2"], "z": py_south["z2"]}, {"x": js_south["x2"], "z": js_south["z2"]})
        assert len(py_south["openings"]) == 1 == len(js_south["openings"])

        py_opening = py_south["openings"][0]
        js_opening = js_south["openings"][0]
        assert approx(py_opening["start"], js_opening["start"])
        assert approx(py_opening["end"], js_opening["end"])
        assert approx(py_opening["width"], js_opening["width"])
        assert py_opening["type"] == js_opening["type"]

    def test_unmerged_walls_unchanged(self, js_reference):
        topology = process_wall_topology(_fixture_a_walls(), OUTLINE)
        for wall_id in ("east", "north", "west"):
            py_wall = find_wall(topology["walls"], wall_id)
            js_wall = find_wall(js_reference["fixtureA"]["walls"], wall_id)
            assert point_close(
                {"x": py_wall["x1"], "z": py_wall["z1"]},
                {"x": js_wall["x1"], "z": js_wall["z1"]},
            )
            assert point_close(
                {"x": py_wall["x2"], "z": py_wall["z2"]},
                {"x": js_wall["x2"], "z": js_wall["z2"]},
            )


# ============================================================
# FIXTURE B: canonical FloorPlanJSON for a simple closed shell
# ============================================================


def _fixture_b_walls():
    return [
        wall("south", 0, 0, 10, 0),
        wall("east", 10, 0, 10, 7),
        wall("north", 10, 7, 0, 7),
        wall("west", 0, 7, 0, 0),
    ]


class TestFixtureB:
    def test_canonical_document_schema_shape(self, js_reference):
        topology = process_wall_topology(_fixture_b_walls(), OUTLINE)
        plan = {
            "id": "test-plan",
            "floorId": "ground-floor",
            "floorIndex": 0,
            "floorCount": 1,
            "sourceType": "unit-test",
            "classifierVersion": "v5",
            "height": 2.8,
            "outline": topology["exteriorOutline"],
            "exteriorOutline": topology["exteriorOutline"],
            "rooms": [],
            "walls": topology["walls"],
            "shellWalls": topology["shellWalls"],
            "slab": {"elevation": -0.16, "thickness": 0.18},
            "roof": {
                "type": "flat",
                "elevation": 2.8,
                "thickness": 0.22,
                "parapetHeight": 0.35,
            },
        }
        document = create_floor_plan_document(plan)
        js_document = js_reference["fixtureB"]["document"]

        assert document["schemaVersion"] == js_document["schemaVersion"] == "zynora.floorplan.v1"
        assert document["metadata"]["floorCount"] == js_document["metadata"]["floorCount"]

        py_floor = document["floors"][0]
        js_floor = js_document["floors"][0]

        assert len(py_floor["walls"]) == len(js_floor["walls"])
        assert len(py_floor["exteriorWalls"]) == len(js_floor["exteriorWalls"])
        assert len(py_floor["outline"]) == len(js_floor["outline"])

        for py_point, js_point in zip(py_floor["outline"], js_floor["outline"]):
            assert point_close(py_point, js_point)

        # Slab/roof derived fields
        assert approx(py_floor["slabs"][0]["thickness"], js_floor["slabs"][0]["thickness"])
        assert approx(py_floor["roof"]["parapetHeight"], js_floor["roof"]["parapetHeight"])
        assert py_floor["roof"]["type"] == js_floor["roof"]["type"]

    def test_document_is_pydantic_schema_valid(self):
        """The produced document must actually satisfy schemas.FloorPlanDocument
        -- i.e. it's not just JSON-shaped, it's a *valid* zynora.floorplan.v1
        document per the strict schema used elsewhere in the backend."""
        from floorplan_engine.schemas import FloorPlanDocument

        result = build_canonical_document(
            walls=_fixture_b_walls(),
            outline=OUTLINE,
            rooms=[],
            plan_id="test-plan",
        )
        # Will raise a pydantic ValidationError if the shape is wrong.
        FloorPlanDocument.model_validate(result["document"])


# ============================================================
# DOCUMENTED GAP: outline repair (polygon union) is not ported
# ============================================================


def test_outline_repair_gap_is_reported_not_silently_wrong():
    """When a room falls outside the given outline, the JS implementation
    attempts a polygon-union repair. That is NOT ported here (see module
    docstring). This test locks in the documented fallback behavior: the
    outline is left unchanged and the condition is surfaced in stats,
    rather than silently producing an incorrect-but-plausible-looking
    result."""
    walls = _fixture_b_walls()
    room_outside = {
        "id": "room-outside",
        "outline": [
            {"x": 20, "z": 20},
            {"x": 22, "z": 20},
            {"x": 22, "z": 22},
            {"x": 20, "z": 22},
        ],
        "area": 4.0,
    }

    topology = process_wall_topology(walls, OUTLINE, [room_outside])

    assert topology["stats"]["outlineRepairNotSupported"] is True
    assert topology["stats"]["shellRepairedFromRooms"] is False
    # Outline is left as the original 10x7 rectangle rather than an
    # incorrectly "repaired" shape.
    assert len(topology["exteriorOutline"]) == 4
