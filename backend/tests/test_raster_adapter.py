"""Tests for RasterAdapter: unit tests for the coordinate transformation
contract, plus a full raster -> AdaptedFloorplan -> canonical_builder ->
FloorPlanDocument integration test.

These tests use a synthetic process_uploaded_floor_plan()-shaped dict
rather than running real OpenCV wall detection, since wall_detector.py
and image_plan_processor.py are explicitly NOT modified or exercised by
this change -- RasterAdapter's job starts after that processing is done.
"""

from __future__ import annotations

from floorplan_engine.adapters.raster_adapter import RasterAdapter
from floorplan_engine.canonical_builder import build_canonical_document
from floorplan_engine.schemas import FloorPlanDocument


def _raster_processor_output(**overrides):
    """Shaped exactly like process_uploaded_floor_plan()'s return value
    (equivalently, the API's "floor_plan" response field) for a simple
    rectangular room: four walls forming a closed 10m x 7m rectangle,
    detected from a raster image and already origin-shifted/scaled by
    the (untouched) image_plan_processor.py."""

    base = {
        "source": "uploaded_floor_plan",
        "width": 10.0,
        "height": 7.0,
        "wall_count": 4,
        "walls": [
            {"id": 1, "x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "orientation": "horizontal", "height": 3.0, "thickness": 0.18},
            {"id": 2, "x1": 10.0, "y1": 0.0, "x2": 10.0, "y2": 7.0, "orientation": "vertical", "height": 3.0, "thickness": 0.18},
            {"id": 3, "x1": 10.0, "y1": 7.0, "x2": 0.0, "y2": 7.0, "orientation": "horizontal", "height": 3.0, "thickness": 0.18},
            {"id": 4, "x1": 0.0, "y1": 7.0, "x2": 0.0, "y2": 0.0, "orientation": "vertical", "height": 3.0, "thickness": 0.18},
        ],
        "rooms": [],
        "doors": [],
        "windows": [],
        "furniture": [],
        "original_filename": "sample_floorplan.jpg",
        "image_width": 1200,
        "image_height": 900,
        "processing_width": 1200,
        "processing_height": 900,
        "processing_scale": 1.0,
        "debug_directory": "debug/floor_plan",
    }
    base.update(overrides)
    return base


class TestRasterAdapterCoordinateTransformation:
    """The approved contract: pure rename (y -> z), no flip/rescale/reorigin."""

    def test_x_coordinates_unchanged(self):
        adapted = RasterAdapter().adapt(_raster_processor_output())
        wall = adapted.walls[0]
        assert wall["x1"] == 0.0
        assert wall["x2"] == 10.0

    def test_y_becomes_z_without_inversion(self):
        """This is THE core contract test: y1=0.0 must become z1=0.0 (not
        e.g. height-minus-y, and not negated) -- a plain rename."""
        adapted = RasterAdapter().adapt(_raster_processor_output())
        wall1 = adapted.walls[0]  # raw y1=0.0, y2=0.0
        wall3 = next(w for w in adapted.walls if w["id"] == "raster-wall-3")  # raw y1=7.0, y2=7.0

        assert wall1["z1"] == 0.0
        assert wall1["z2"] == 0.0
        assert wall3["z1"] == 7.0
        assert wall3["z2"] == 7.0

    def test_no_rescaling_applied(self):
        """A wall spanning raw x 0->10 must remain exactly 0->10 -- the
        adapter must not reapply any scale factor on top of what
        image_plan_processor.py already did."""
        adapted = RasterAdapter().adapt(_raster_processor_output())
        wall = adapted.walls[0]
        assert wall["x2"] - wall["x1"] == 10.0

    def test_diagonal_wall_not_mirrored_or_rotated(self):
        """A wall that isn't axis-aligned would reveal an accidental
        mirror/rotation immediately if one were applied; this locks in
        that none is."""
        raw = _raster_processor_output(
            walls=[
                {"id": 1, "x1": 1.0, "y1": 2.0, "x2": 4.0, "y2": 6.0, "orientation": "diagonal", "height": 3.0, "thickness": 0.18},
            ]
        )
        adapted = RasterAdapter().adapt(raw)
        wall = adapted.walls[0]
        assert (wall["x1"], wall["z1"]) == (1.0, 2.0)
        assert (wall["x2"], wall["z2"]) == (4.0, 6.0)


class TestRasterAdapterHeightPreservation:
    def test_existing_raster_height_is_preserved_not_overridden(self):
        """Explicit approved decision: do NOT silently change 3.0 -> 2.8."""
        adapted = RasterAdapter().adapt(_raster_processor_output())
        assert all(w["height"] == 3.0 for w in adapted.walls)

    def test_height_discrepancy_is_surfaced_as_a_warning(self):
        adapted = RasterAdapter().adapt(_raster_processor_output())
        assert any("height" in w.lower() and "2.8" in w for w in adapted.warnings)


class TestRasterAdapterEmptyRoomsAndOpenings:
    def test_rooms_are_empty_with_explicit_warning(self):
        adapted = RasterAdapter().adapt(_raster_processor_output())
        assert adapted.rooms == []
        assert any("room" in w.lower() for w in adapted.warnings)

    def test_all_walls_have_empty_openings_with_explicit_warning(self):
        adapted = RasterAdapter().adapt(_raster_processor_output())
        assert all(w["openings"] == [] for w in adapted.walls)
        assert any("door/window" in w.lower() or "openings" in w.lower() for w in adapted.warnings)

    def test_exterior_flag_left_for_canonical_builder_to_infer(self):
        """isExterior must NOT be forced true/false by the adapter --
        canonical_builder.infer_exterior_walls() owns that decision."""
        adapted = RasterAdapter().adapt(_raster_processor_output())
        for wall in adapted.walls:
            assert "isExterior" not in wall


class TestRasterAdapterEdgeCases:
    def test_no_walls_produces_empty_result_with_warning(self):
        adapted = RasterAdapter().adapt(_raster_processor_output(walls=[]))
        assert adapted.walls == []
        assert any("no walls" in w.lower() for w in adapted.warnings)

    def test_source_type_is_raster(self):
        adapted = RasterAdapter().adapt(_raster_processor_output())
        assert adapted.source_type == "raster"


class TestRasterToCanonicalPipeline:
    """Full pipeline: raster processor output -> RasterAdapter ->
    canonical_builder.build_canonical_document() -> valid FloorPlanDocument."""

    def test_full_pipeline_produces_valid_floor_plan_document(self):
        raw = _raster_processor_output()
        adapted = RasterAdapter().adapt(raw)

        result = build_canonical_document(
            walls=adapted.walls,
            outline=adapted.outline,
            rooms=adapted.rooms,
            plan_id="raster-test-plan",
            source_type=adapted.source_type,
            height=3.0,  # matches the preserved raster wall height
        )

        # Must not raise -- confirms the adapted shape really is
        # consumable by the canonical builder + schema, end to end.
        document = FloorPlanDocument.model_validate(result["document"])

        floor = document.floors[0]
        assert len(floor.walls) == 4
        # The four raster walls form a closed rectangle; canonical_builder's
        # exterior-wall inference (build_outline_from_walls / graph_summary)
        # should recognize this as a closed shell with no adapter-side help.
        assert len(floor.exteriorWalls) == 4
        assert floor.rooms == []

    def test_pipeline_reports_no_outline_repair_needed(self):
        """With no rooms supplied, the documented outline-repair gap
        (see canonical_builder.py module docstring) is never triggered --
        confirms the raster path stays inside the ported/tested subset of
        the geometry pipeline for this simple case."""
        raw = _raster_processor_output()
        adapted = RasterAdapter().adapt(raw)

        result = build_canonical_document(
            walls=adapted.walls,
            outline=adapted.outline,
            rooms=adapted.rooms,
            source_type=adapted.source_type,
        )
        assert result["topology_stats"]["outlineRepairNotSupported"] is False

    def test_discovered_quirk_interior_wall_list_keeps_isExterior_false(self):
        """DISCOVERED WHILE VERIFYING THIS ADAPTER (not a bug introduced
        by it -- an existing property of the ported wallTopology.js
        algorithm, confirmed here rather than assumed):

        Because RasterAdapter has no interior/exterior signal to offer
        (raster detection doesn't know which walls are exterior), every
        adapted wall omits isExterior entirely, and
        canonical_builder.infer_exterior_walls() has no explicit-exterior
        walls and no outline to match against (outline=[]). The
        build_outline_from_walls / shell_from_outline fallback still
        successfully reconstructs a closed exterior shell from the wall
        endpoints alone -- but only in the SYNTHESIZED `exteriorWalls`
        list. The raw `walls` list entries keep isExterior=False even
        though they physically form the shell.

        This is harmless for rendering (Three.js/Blender both consume
        `exteriorWalls` for the shell), but it means `walls[].isExterior`
        is not a meaningful signal for raster-derived documents today.
        Flagging this explicitly rather than leaving it as an implicit,
        undocumented side effect."""
        raw = _raster_processor_output()
        adapted = RasterAdapter().adapt(raw)

        result = build_canonical_document(
            walls=adapted.walls,
            outline=adapted.outline,
            rooms=adapted.rooms,
            source_type=adapted.source_type,
        )
        document = FloorPlanDocument.model_validate(result["document"])
        floor = document.floors[0]

        assert all(w.isExterior is False for w in floor.walls)
        assert all(w.isExterior is True for w in floor.exteriorWalls)
        assert len(floor.exteriorWalls) == 4

    def test_near_duplicate_walls_from_detection_noise_are_merged(self):
        """Simulates a realistic wall_detector.py Hough-line-detection
        artifact: two near-identical segments for the same physical wall.
        Confirms canonical_builder's merge step (already equivalence-
        tested against real JS output separately) also behaves correctly
        specifically on RasterAdapter-shaped input."""
        raw = _raster_processor_output(
            walls=_raster_processor_output()["walls"]
            + [
                {
                    "id": 5,
                    "x1": 0.02,
                    "y1": 0.01,
                    "x2": 9.98,
                    "y2": 0.01,
                    "orientation": "horizontal",
                    "height": 3.0,
                    "thickness": 0.18,
                }
            ]
        )
        adapted = RasterAdapter().adapt(raw)

        result = build_canonical_document(
            walls=adapted.walls,
            outline=adapted.outline,
            rooms=adapted.rooms,
            source_type=adapted.source_type,
        )
        document = FloorPlanDocument.model_validate(result["document"])
        floor = document.floors[0]

        assert result["topology_stats"]["duplicateWallsRemoved"] >= 1
        assert len(floor.exteriorWalls) == 4

    def test_missing_required_coordinate_field_raises_clearly(self):
        """Refuses to guess a coordinate for a malformed upstream response
        rather than silently defaulting to 0."""
        raw = _raster_processor_output()
        del raw["walls"][0]["y2"]

        import pytest

        with pytest.raises(KeyError):
            RasterAdapter().adapt(raw)
