"""Tests for SvgAdapter.

PRIMARY chain tested (real parser execution, per the mandatory
"real data first" requirement): the actual, unmodified SvgHouseParser
running against backend/tests/fixtures/synthetic_cubicasa_floorplan.svg,
through SvgAdapter, through the shared canonical_builder, validated
against schemas.FloorPlanDocument and (separately, see the report) the
real JS wallTopology.validateFloorPlanGeometry.

SUPPLEMENTARY: direct unit tests of the geometric helper functions
(wall_polygon_to_centerline, project_opening_onto_wall) using hand-built
synthetic polygons, explicitly labeled as synthetic, to cover cases the
fixture SVG doesn't exercise (rotated walls, multiple openings sanity,
degenerate input).

HONEST STATUS (do not overstate): the fixture is a hand-built synthetic
SVG, not a real CubiCasa export -- see fixtures/synthetic_cubicasa_floorplan.svg's
own header comment and backend/tests/test_reconstructed_models.py for the
independently-verified evidence that no real sample exists anywhere in
this repository. "Verified against real parser code" and "validated
against a real CubiCasa export" are different claims; only the former is
made here.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from floorplan_engine.adapters.svg_adapter import (
    SvgAdapter,
    project_opening_onto_wall,
    wall_polygon_to_centerline,
)
from floorplan_engine.canonical_builder import build_canonical_document
from floorplan_engine.schemas import FloorPlanDocument
from zynora_ai.core.parser.svg_house_parser import SvgHouseParser

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "synthetic_cubicasa_floorplan.svg"
)


@pytest.fixture(scope="module")
def parsed_house():
    return SvgHouseParser().parse(FIXTURE_PATH)


@pytest.fixture(scope="module")
def adapted(parsed_house):
    return SvgAdapter().adapt(parsed_house)


@pytest.fixture(scope="module")
def canonical_result(adapted):
    return build_canonical_document(
        walls=adapted.walls,
        outline=adapted.outline,
        rooms=adapted.rooms,
        source_type=adapted.source_type,
    )


# ============================================================
# 1-2. SvgAdapter fed real, executed parser output
# ============================================================


class TestAdapterOnRealParserOutput:
    def test_all_five_walls_adapted(self, adapted):
        assert len(adapted.walls) == 5

    def test_wall_ids_are_svg_namespaced_but_traceable(self, adapted):
        ids = {w["id"] for w in adapted.walls}
        assert ids == {
            "svg-wall-1",
            "svg-wall-2",
            "svg-wall-3",
            "svg-wall-4",
            "svg-wall-5",
        }
        assert all(
            w["metadata"]["sourceWallId"] in {f"wall-{i}" for i in range(1, 6)}
            for w in adapted.walls
        )

    def test_source_type_is_svg(self, adapted):
        assert adapted.source_type == "svg"


# ============================================================
# 3. Wall polygon -> canonical centerline+thickness (real fixture walls)
# ============================================================


class TestWallPolygonToCenterline:
    def test_south_wall_centerline_matches_hand_calculation(self, adapted):
        """South wall SVG polygon: 0,390 1000,390 1000,410 0,410 (post
        fixture revision). At the cited 100px/m scale: centerline should
        run horizontally at z=4.0m from x=0 to x=10.0m, thickness=0.2m."""
        wall = next(w for w in adapted.walls if w["id"] == "svg-wall-1")
        assert wall["x1"] == pytest.approx(0.0, abs=1e-6)
        assert wall["z1"] == pytest.approx(4.0, abs=1e-6)
        assert wall["x2"] == pytest.approx(10.0, abs=1e-6)
        assert wall["z2"] == pytest.approx(4.0, abs=1e-6)
        assert wall["thickness"] == pytest.approx(0.2, abs=1e-6)

    def test_east_wall_is_vertical(self, adapted):
        wall = next(w for w in adapted.walls if w["id"] == "svg-wall-4")
        assert wall["x1"] == pytest.approx(wall["x2"], abs=1e-6)
        assert abs(wall["z2"] - wall["z1"]) == pytest.approx(4.0, abs=1e-6)

    def test_rotated_wall_polygon_synthetic_case(self):
        """SUPPLEMENTARY, explicitly synthetic: the fixture SVG only has
        axis-aligned walls. This hand-built 45-degree-rotated rectangle
        (length 10, thickness 1) checks the general projection algorithm
        doesn't silently assume axis alignment."""
        u = (1 / math.sqrt(2), 1 / math.sqrt(2))
        perp = (-u[1], u[0])
        length, thickness = 10.0, 1.0

        def pt(along, across):
            return (u[0] * along + perp[0] * across, u[1] * along + perp[1] * across)

        polygon = [
            pt(-length / 2, -thickness / 2),
            pt(length / 2, -thickness / 2),
            pt(length / 2, thickness / 2),
            pt(-length / 2, thickness / 2),
        ]

        start, end, derived_thickness, warnings = wall_polygon_to_centerline(polygon)

        derived_length = math.hypot(end[0] - start[0], end[1] - start[1])
        assert derived_length == pytest.approx(length, abs=1e-6)
        assert derived_thickness == pytest.approx(thickness, abs=1e-6)
        assert warnings == []

    def test_degenerate_polygon_raises_rather_than_guessing(self):
        """SUPPLEMENTARY, synthetic: a polygon with fewer than 3 points
        cannot represent a wall footprint at all."""
        with pytest.raises(ValueError):
            wall_polygon_to_centerline([(0.0, 0.0), (1.0, 0.0)])

    def test_zero_thickness_polygon_raises_rather_than_guessing(self):
        """SUPPLEMENTARY, synthetic: a perfectly degenerate (zero-area)
        polygon must not silently produce a plausible-looking wall."""
        with pytest.raises(ValueError):
            wall_polygon_to_centerline(
                [(0.0, 0.0), (5.0, 0.0), (5.0, 0.0), (0.0, 0.0)]
            )


# ============================================================
# 4. External/Internal preservation
# ============================================================


class TestExteriorInteriorPreservation:
    def test_external_walls_map_to_isExterior_true(self, adapted):
        external_ids = {"svg-wall-1", "svg-wall-2", "svg-wall-3", "svg-wall-4"}
        for wall in adapted.walls:
            if wall["id"] in external_ids:
                assert wall["isExterior"] is True

    def test_internal_wall_maps_to_isExterior_false(self, adapted):
        interior_wall = next(w for w in adapted.walls if w["id"] == "svg-wall-5")
        assert interior_wall["isExterior"] is False

    def test_explicit_flag_not_left_for_inference_unlike_raster(self, adapted):
        """Unlike RasterAdapter (which omits isExterior entirely), the
        SVG path has a real signal and must supply an actual bool for
        every wall, not None/absent."""
        assert all(w["isExterior"] is not None for w in adapted.walls)


# ============================================================
# 5. Doors and windows -> canonical Openings
# ============================================================


class TestOpeningMapping:
    def test_door_offset_and_width_match_hand_calculation(self, adapted):
        """South wall door SVG polygon: 200,390 260,390 260,410 200,410.
        Projected onto the south wall's centerline (0,4.0)->(10,4.0):
        offset=2.0m, width=0.6m."""
        wall = next(w for w in adapted.walls if w["id"] == "svg-wall-1")
        assert len(wall["openings"]) == 1
        door = wall["openings"][0]
        assert door["type"] == "door"
        assert door["offset"] == pytest.approx(2.0, abs=1e-3)
        assert door["width"] == pytest.approx(0.6, abs=1e-3)

    def test_window_offset_and_width_match_hand_calculation(self, adapted):
        """North wall window SVG polygon: 150,-10 250,-10 250,10 150,10.
        Projected onto the north wall's centerline (0,0)->(10,0):
        offset=1.5m, width=1.0m."""
        wall = next(w for w in adapted.walls if w["id"] == "svg-wall-2")
        assert len(wall["openings"]) == 1
        window = wall["openings"][0]
        assert window["type"] == "window"
        assert window["offset"] == pytest.approx(1.5, abs=1e-3)
        assert window["width"] == pytest.approx(1.0, abs=1e-3)

    def test_interior_wall_door_is_preserved(self, adapted):
        """Confirms doors are not assumed exterior-only."""
        interior_wall = next(w for w in adapted.walls if w["id"] == "svg-wall-5")
        assert len(interior_wall["openings"]) == 1
        assert interior_wall["openings"][0]["type"] == "door"

    def test_parent_wall_association_preserved(self, adapted):
        """Each opening must stay attached to the wall dict it was found
        on -- never pooled into a separate flat list that could lose the
        parent-wall relationship the parser already established."""
        walls_with_openings = [w for w in adapted.walls if w["openings"]]
        assert len(walls_with_openings) == 3  # south, north, interior

    def test_walls_with_multiple_openings_would_all_be_kept(self):
        """SUPPLEMENTARY, synthetic: confirms project_opening_onto_wall
        (used per-opening in a loop) doesn't have any single-opening
        assumption baked in -- two non-overlapping openings on one wall
        both project correctly and independently."""
        wall_start, wall_end = (0.0, 0.0), (10.0, 0.0)
        opening_a = [(1.0, -0.1), (2.0, -0.1), (2.0, 0.1), (1.0, 0.1)]
        opening_b = [(6.0, -0.1), (8.0, -0.1), (8.0, 0.1), (6.0, 0.1)]

        offset_a, width_a = project_opening_onto_wall(opening_a, wall_start, wall_end)
        offset_b, width_b = project_opening_onto_wall(opening_b, wall_start, wall_end)

        assert offset_a == pytest.approx(1.0)
        assert width_a == pytest.approx(1.0)
        assert offset_b == pytest.approx(6.0)
        assert width_b == pytest.approx(2.0)

    def test_vertical_position_defaults_are_disclosed_not_hidden(self, adapted):
        """Confirms bottom/height come from the documented fixed
        defaults, and that this is disclosed via warnings rather than
        presented as detected data."""
        wall = next(w for w in adapted.walls if w["id"] == "svg-wall-1")
        door = wall["openings"][0]
        assert door["bottom"] == 0.0
        assert door["height"] == 2.1
        assert any("not present in 2D SVG" in w for w in adapted.warnings)


# ============================================================
# 6. Room mapping: parser-provided vs ML-classified, explicitly separated
# ============================================================


class TestRoomMapping:
    def test_rooms_use_parser_provided_type_when_no_predictions_given(
        self, adapted
    ):
        rooms_by_id = {r["id"]: r for r in adapted.rooms}
        assert rooms_by_id["svg-room-living"]["type"] == "Living Room"
        assert rooms_by_id["svg-room-bedroom"]["type"] == "Bedroom"

    def test_room_ids_and_polygons_preserved(self, adapted):
        assert len(adapted.rooms) == 2
        for room in adapted.rooms:
            assert len(room["outline"]) == 4

    def test_ml_predictions_override_parser_type_when_provided(self, parsed_house):
        """Confirms the adapter distinguishes parser-provided info from
        ML-classified info by preferring the latter ONLY when explicitly
        supplied, matched by room_id (matching inference.py's own
        room_id convention). RoomTypeInferenceV5 cannot actually run
        (missing trained-model artifacts, a separate documented gap), so
        this uses a hand-built, explicitly synthetic stand-in prediction
        object matching RoomPrediction's real shape as seen in
        inference.py -- not a claim that V5 itself was executed."""

        class _FakePrediction:
            def __init__(self, room_id, predicted_room_type):
                self.room_id = room_id
                self.predicted_room_type = predicted_room_type

        predictions = [_FakePrediction("room-living", "Family Room")]
        adapted_with_predictions = SvgAdapter().adapt(
            parsed_house, room_predictions=predictions
        )
        rooms_by_id = {r["id"]: r for r in adapted_with_predictions.rooms}
        assert rooms_by_id["svg-room-living"]["type"] == "Family Room"
        # Unmatched room keeps its parser-provided type, not a guess.
        assert rooms_by_id["svg-room-bedroom"]["type"] == "Bedroom"

    def test_partial_prediction_coverage_is_warned_about(self, parsed_house):
        class _FakePrediction:
            def __init__(self, room_id, predicted_room_type):
                self.room_id = room_id
                self.predicted_room_type = predicted_room_type

        predictions = [_FakePrediction("room-living", "Family Room")]
        adapted_with_predictions = SvgAdapter().adapt(
            parsed_house, room_predictions=predictions
        )
        assert any(
            "no matching entry in room_predictions" in w
            for w in adapted_with_predictions.warnings
        )


# ============================================================
# 7, 9-10. Canonical builder integration + validation (no duplicated
# geometry logic inside the adapter -- shared canonical_builder used)
# ============================================================


class TestCanonicalBuilderIntegration:
    def test_produces_schema_valid_document(self, canonical_result):
        FloorPlanDocument.model_validate(canonical_result["document"])

    def test_shell_closes_with_the_corrected_fixture(self, canonical_result):
        stats = canonical_result["topology_stats"]
        assert stats["exteriorShellClosed"] is True
        assert stats["exteriorWalls"] == 4
        assert stats["outlineRepairNotSupported"] is False

    def test_both_rooms_present_in_canonical_document(self, canonical_result):
        document = FloorPlanDocument.model_validate(canonical_result["document"])
        floor = document.floors[0]
        assert len(floor.rooms) == 2
        room_types = {r.type for r in floor.rooms}
        assert room_types == {"Living Room", "Bedroom"}

    def test_all_openings_survive_into_canonical_document(self, canonical_result):
        document = FloorPlanDocument.model_validate(canonical_result["document"])
        floor = document.floors[0]
        total_openings = sum(len(w.openings) for w in floor.walls)
        assert total_openings == 3  # 2 doors + 1 window


# ============================================================
# 12. Malformed/minimal SVG behavior the parser actually supports
# ============================================================


class TestMalformedOrMinimalInput:
    def test_house_with_no_floors_raises(self):
        class _EmptyHouse:
            floors: list = []

        with pytest.raises(ValueError, match="no floors"):
            SvgAdapter().adapt(_EmptyHouse())

    def test_floor_with_no_walls_raises(self):
        """SUPPLEMENTARY, synthetic: a floor with rooms but literally no
        wall polygons cannot produce any canonical geometry -- the
        adapter must refuse clearly rather than emit an empty-but-valid-
        looking document."""

        class _EmptyFloor:
            rooms: list = []
            walls: list = []

        class _HouseWithEmptyFloor:
            floors = [_EmptyFloor()]

        with pytest.raises(ValueError, match="No usable walls"):
            SvgAdapter().adapt(_HouseWithEmptyFloor())

    def test_multi_floor_house_only_adapts_first_floor_with_warning(
        self, parsed_house
    ):
        """SUPPLEMENTARY, synthetic: multi-floor SVG adaptation is
        explicitly not yet implemented (per the adapter's own docstring)
        -- confirms this limitation is surfaced as a warning, not
        silently mishandled by merging/dropping floors unpredictably."""
        floor = parsed_house.floors[0]

        class _TwoFloorHouse:
            floors = [floor, floor]

        result = SvgAdapter().adapt(_TwoFloorHouse())
        assert any("2 floors" in w and "only the first" in w for w in result.warnings)
        assert len(result.walls) == 5  # only floor[0]'s walls, not doubled
