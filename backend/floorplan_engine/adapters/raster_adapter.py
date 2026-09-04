"""Raster (PDF/JPG/PNG) -> AdaptedFloorplan adapter (Workflow 1).

STATUS: implemented (P1), per the approved coordinate-transformation
investigation.

INPUT SHAPE: the dict returned by
floorplan_engine.image_plan_processor.process_uploaded_floor_plan()
(equivalently, the "floor_plan" field of the /api/floor-plans/upload
response body -- see floorplan_upload_routes.py line 137). Each wall in
raw_input["walls"] looks like:

    {"id": int, "x1": float, "y1": float, "x2": float, "y2": float,
     "orientation": str, "height": 3.0, "thickness": 0.18}

(see image_plan_processor.convert_walls_to_json).

COORDINATE TRANSFORMATION (approved investigation, not re-derived here):

    Raster image coordinates:  X -> right, Y -> down
    image_plan_processor.py already performs bounding-box origin
    subtraction and uniform metric scaling before this adapter ever sees
    the data (convert_walls_to_json, lines ~100-131). Two independent
    existing consumers of this exact wall shape -- the frontend
    normalizeFloorPlan.js (readWallPoint: `wall.z1 ?? wall.y1`) and the
    Blender renderer (render_zynora_floorplan.py line 474:
    `value.get("z", value.get("y"))`) -- already treat y as z with a
    plain rename, no sign flip. This adapter follows the same, now
    explicit, contract:

        x1 -> x1   (unchanged)
        y1 -> z1   (renamed, NOT inverted)
        x2 -> x2   (unchanged)
        y2 -> z2   (renamed, NOT inverted)

    No re-scaling, re-origin, mirroring, or rotation is applied here --
    all of that already happened upstream in image_plan_processor.py,
    which this adapter does not touch.

WALL HEIGHT (explicit, approved decision -- do not "fix" silently):
The raster processor hardcodes height=3.0 per wall (image_plan_processor.py
line 135), while most of the rest of the system (structural_generator.py,
canonical_builder.py's defaults) assumes 2.8. This adapter PRESERVES the
existing raster height value unchanged rather than overriding it. This is
a deliberate decision, not an oversight -- see the "KNOWN LIMITATIONS"
docstring section below and the P1/P2 backlog note it points to.

WHAT THIS ADAPTER DOES NOT DO (by design, matching the raster pipeline's
actual current capability -- see the coordinate investigation report):
  - Does not produce rooms: process_uploaded_floor_plan always returns
    "rooms": [] today (no room-polygon detection exists in this pipeline).
  - Does not produce openings: same reason -- "doors": [] and
    "windows": [] are always empty from this input path today.
  - Does not infer which walls are exterior: left to
    canonical_builder.infer_exterior_walls(), exactly as instructed.

NEITHER image_plan_processor.py NOR wall_detector.py IS MODIFIED HERE.
"""

from __future__ import annotations

from typing import Any

from floorplan_engine.adapters import AdaptedFloorplan

# Default default height used elsewhere in the system (structural_generator.py,
# canonical_builder.py). NOT applied to raster walls -- kept here only as a
# documented reference point for the height-consistency backlog item below.
_SYSTEM_DEFAULT_WALL_HEIGHT = 2.8


class RasterAdapter:
    """Adapts floorplan_engine.image_plan_processor.process_uploaded_floor_plan()
    output (walls already detected/merged by wall_detector.py) into
    AdaptedFloorplan.

    This class does not parse images, PDFs, or invoke OpenCV/wall_detector
    itself -- callers pass the already-processed dict in, keeping this a
    pure, easily-testable reshaping step.
    """

    def adapt(self, raw_input: dict[str, Any]) -> AdaptedFloorplan:
        raw_walls = raw_input.get("walls") or []
        warnings: list[str] = []

        if not raw_walls:
            warnings.append(
                "Raster processor returned no walls; nothing to adapt."
            )

        walls: list[dict[str, Any]] = []
        raster_heights: set[float] = set()

        for raw_wall in raw_walls:
            height = float(raw_wall.get("height", _SYSTEM_DEFAULT_WALL_HEIGHT))
            raster_heights.add(height)

            walls.append(
                {
                    "id": f"raster-wall-{raw_wall.get('id')}",
                    # Pure rename per the approved coordinate contract --
                    # NOT a flip, NOT a rescale, NOT a re-origin.
                    "x1": float(raw_wall["x1"]),
                    "z1": float(raw_wall["y1"]),
                    "x2": float(raw_wall["x2"]),
                    "z2": float(raw_wall["y2"]),
                    # Preserved as-is (see WALL HEIGHT note above --
                    # deliberately not normalized to 2.8 here).
                    "height": height,
                    "thickness": float(raw_wall.get("thickness", 0.18)),
                    "color": "#eee9e1",
                    # Left unset (not False, not True): normalize_exterior_flag
                    # in canonical_builder treats a missing/non-bool flag as
                    # "not explicitly exterior," which is exactly what we
                    # want -- infer_exterior_walls() then does the real
                    # inference from the outline, as instructed.
                    "openings": [],
                    "metadata": {
                        "sourceWallId": raw_wall.get("id"),
                        "orientation": raw_wall.get("orientation"),
                    },
                }
            )

        if raster_heights and raster_heights != {_SYSTEM_DEFAULT_WALL_HEIGHT}:
            warnings.append(
                f"Raster walls use height {sorted(raster_heights)} from "
                f"image_plan_processor.py, which differs from this "
                f"system's other default of {_SYSTEM_DEFAULT_WALL_HEIGHT}m "
                "(structural_generator.py / canonical_builder.py). This "
                "value is preserved as-is, not normalized -- see the "
                "wall-height consistency backlog item."
            )

        warnings.append(
            "Raster input contains no room polygons (image_plan_processor "
            "does not detect rooms); AdaptedFloorplan.rooms is empty."
        )
        warnings.append(
            "Raster input contains no door/window detections "
            "(image_plan_processor does not detect openings); all "
            "adapted walls have empty openings."
        )

        return AdaptedFloorplan(
            walls=walls,
            outline=[],  # let canonical_builder derive it from wall
            # endpoints via build_outline_from_walls, as instructed
            rooms=[],
            source_type="raster",
            warnings=warnings,
        )
