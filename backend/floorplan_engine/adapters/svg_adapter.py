"""SVG -> AdaptedFloorplan adapter (Workflow 1).

STATUS: implemented and verified against the REAL, unmodified
SvgHouseParser (the models-package import blocker documented in an
earlier revision of this docstring has since been fixed -- see
zynora_ai/core/models/__init__.py for that investigation. This file is
updated to reflect that current reality rather than leaving stale claims
in place).

=====================================================================
INPUT CONTRACT (verified against real, executed parser output, not
duck-typed guesses)
=====================================================================

`SvgAdapter.adapt()` is written against a duck-typed attribute contract
so it does not need to import svg_house_parser.py/wall_parser.py/
door_parser.py/window_parser.py/inference.py directly -- but that
contract has now been directly confirmed by running the real parser
against backend/tests/fixtures/synthetic_cubicasa_floorplan.svg and
inspecting the actual resulting objects (see test_svg_adapter.py):

    House:  .floors -> list[Floor]
    Floor:  .rooms -> list[Room], .walls -> list[Wall]
    Room:   .id, .room_type, .polygon -> list[Point]
    Wall:   .id, .wall_type ("External" | "Internal"), .polygon -> list[Point],
            .doors -> list[Door], .windows -> list[Window]
    Door:   .id, .door_type, .polygon -> list[Point]
    Window: .id, .window_type, .polygon -> list[Point]
    Point:  .x, .y

REMAINING, GENUINELY UNVERIFIED LIMITATION: no real CubiCasa SVG export
exists anywhere in this repository (confirmed via scripts/find_sample_svg.py
against the exact dataset paths the project's own tooling expects -- zero
found). The fixture used for verification is a hand-built, explicitly
synthetic SVG following CubiCasa's real class-naming conventions. This
adapter's logic is exercised against genuine parser execution, not
fabricated adapter-level fixtures -- but "genuine parser execution on a
synthetic input" is not the same claim as "validated against a real
CubiCasa export," and this file does not claim the latter.

=====================================================================
WALL REPRESENTATION: polygon, not centerline -- a genuine geometry
problem, not a rename
=====================================================================

Unlike the raster path (wall_detector.py already produces centerline
segments), CubiCasa-style SVG walls are drawn as filled POLYGONS (their
actual physical footprint, typically but not guaranteed to be a
4-point rectangle). The canonical schema and canonical_builder both
expect a wall as a centerline segment (x1/z1 -> x2/z2) plus a scalar
thickness -- there is no existing code anywhere in this repository that
converts a wall polygon into a centerline+thickness pair. This adapter
implements that conversion itself: for each wall polygon, it uses the
direction of the polygon's longest edge as the wall's length axis, then
projects every vertex onto that axis and its perpendicular to derive:
    - centerline endpoints = midpoints of the perpendicular span, at the
      extremes of the along-axis span
    - thickness = the perpendicular span
This degrades gracefully for near-rectangular polygons (typical CubiCasa
wall geometry) but is not a full rotating-calipers minimum-bounding-
rectangle solve, and is not guaranteed correct for wildly non-rectangular
wall polygons; such cases are surfaced via warnings, not silently forced
into a plausible-looking wall.

=====================================================================
OPENING REPRESENTATION: also polygon-based, and vertical position is
NOT present in the source data at all
=====================================================================

Door/window polygons are also raw in-plane (x, y) footprints from a
top-down floor plan. The canonical schema's Opening additionally needs
`bottom`/`height` (vertical position off the floor) -- information a 2D
floor-plan SVG structurally cannot contain. This adapter computes
`offset`/`width` genuinely (by projecting the opening polygon's extent
onto its parent wall's derived centerline), but `bottom`/`height` use
fixed defaults per opening type (door: bottom=0.0, height=2.1; window:
bottom=0.9, height=1.2 -- matching the general magnitude of defaults
already used elsewhere in this codebase, e.g. structural_generator.py's
own door/window generation). This is a genuine, disclosed information
loss, not a fabrication disguised as detected data.

=====================================================================
COORDINATE SCALE
=====================================================================

SvgHouseParser performs NO unit conversion -- Point.x/.y are raw SVG
user-space numbers exactly as they appear in the source file's `points`
attributes. Neither svg_house_parser.py nor wall_parser.py declares a
scale. The only existing, concrete precedent for a CubiCasa-SVG-to-metres
scale anywhere in this codebase is:

    zynora_ai/renderer/mesh_generator.py:
        PIXELS_PER_METER = 100.0
        pixels_to_meters(value) = round(value / 100.0, 3)

This adapter uses that same constant, cited explicitly rather than
invented, because it is the only existing statement of this assumption
in the repository. This is flagged as an ASSUMPTION REQUIRING
CONFIRMATION against a real CubiCasa SVG file once one is available for
testing (not currently possible -- see the import-chain finding above),
not treated as a verified fact.

=====================================================================
EXTERIOR/INTERIOR: a real, direct signal (unlike the raster path)
=====================================================================

wall_parser.py sets `wall_type = "External" if has_class(element,
"External") else "Internal"` directly from the SVG's own CSS class on
each Wall element -- this is genuine source information, not inferred.
This adapter maps "External" -> isExterior=True, "Internal" ->
isExterior=False, and passes it straight to canonical_builder as an
explicit flag (unlike RasterAdapter, which must leave it unset for
inference). canonical_builder.infer_exterior_walls() is still free to
run afterward, but should have little or nothing to correct here.

NEITHER svg_house_parser.py, wall_parser.py, door_parser.py,
window_parser.py, NOR inference.py IS MODIFIED BY THIS FILE.
"""

from __future__ import annotations

import math
from typing import Any

from floorplan_engine.adapters import AdaptedFloorplan

# Cited precedent, not invented -- see zynora_ai/renderer/mesh_generator.py.
SVG_PIXELS_PER_METER = 100.0

# Matches the general magnitude of defaults used elsewhere in this codebase
# for undetectable vertical opening placement (e.g. structural_generator.py's
# own door/window generation).
DEFAULT_OPENING_VERTICAL = {
    "door": {"bottom": 0.0, "height": 2.1},
    "window": {"bottom": 0.9, "height": 1.2},
}

DEFAULT_WALL_HEIGHT = 2.8
DEFAULT_WALL_THICKNESS = 0.16


def _to_metres(value: float) -> float:
    return round(value / SVG_PIXELS_PER_METER, 4)


def _polygon_points(polygon: Any) -> list[tuple[float, float]]:
    """Extract (x, y) tuples from a list of duck-typed Point objects
    (each exposing .x/.y), already in SVG units (not yet converted)."""
    return [(float(p.x), float(p.y)) for p in polygon]


def _dominant_long_edge_direction(
    points: list[tuple[float, float]],
) -> tuple[float, float]:
    """Return a unit vector along the polygon's longest edge, used as an
    approximation of the true minimum-area-rectangle orientation. This is
    sufficient for the axis-aligned-or-near-axis-aligned rectangular wall
    polygons CubiCasa produces; it is not a full rotating-calipers solve."""
    best_length = -1.0
    best_direction = (1.0, 0.0)

    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length > best_length:
            best_length = length
            if length > 1e-9:
                best_direction = (dx / length, dy / length)

    return best_direction


def wall_polygon_to_centerline(
    points: list[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float], float, list[str]]:
    """Convert a wall footprint polygon (points already in metres) into
    (start, end, thickness, warnings)."""
    warnings: list[str] = []

    if len(points) < 3:
        raise ValueError("Wall polygon needs at least 3 points.")

    direction = _dominant_long_edge_direction(points)
    perp = (-direction[1], direction[0])

    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)

    along = [
        (p[0] - cx) * direction[0] + (p[1] - cy) * direction[1] for p in points
    ]
    across = [(p[0] - cx) * perp[0] + (p[1] - cy) * perp[1] for p in points]

    along_min, along_max = min(along), max(along)
    across_min, across_max = min(across), max(across)

    length = along_max - along_min
    thickness = across_max - across_min

    if thickness <= 1e-6 or length <= 1e-6:
        raise ValueError(
            "Degenerate wall polygon (zero length or zero thickness after "
            "projection)."
        )

    if thickness > length:
        warnings.append(
            "Wall polygon's derived thickness exceeds its derived length "
            "-- the long/short edge detection may have picked the wrong "
            "axis for a non-rectangular polygon. Geometry produced "
            "anyway; treat with reduced confidence."
        )

    across_mid = (across_min + across_max) / 2

    start = (
        cx + direction[0] * along_min + perp[0] * across_mid,
        cy + direction[1] * along_min + perp[1] * across_mid,
    )
    end = (
        cx + direction[0] * along_max + perp[0] * across_mid,
        cy + direction[1] * along_max + perp[1] * across_mid,
    )

    return start, end, thickness, warnings


def project_opening_onto_wall(
    opening_points: list[tuple[float, float]],
    wall_start: tuple[float, float],
    wall_end: tuple[float, float],
) -> tuple[float, float]:
    """Project an opening polygon's extent onto the wall centerline,
    returning (offset, width) in metres from wall_start toward wall_end."""
    dx = wall_end[0] - wall_start[0]
    dz = wall_end[1] - wall_start[1]
    wall_length = math.hypot(dx, dz)

    if wall_length <= 1e-9:
        return 0.0, 0.0

    ux, uz = dx / wall_length, dz / wall_length

    projections = [
        (p[0] - wall_start[0]) * ux + (p[1] - wall_start[1]) * uz
        for p in opening_points
    ]
    start_offset = max(0.0, min(projections))
    end_offset = min(wall_length, max(projections))

    return start_offset, max(0.0, end_offset - start_offset)


class SvgAdapter:
    """Adapts already-parsed SVG floorplan data into AdaptedFloorplan.

    See module docstring for the exact duck-typed input contract (now
    verified against real, executed parser output). This class does NOT
    parse SVG files itself, and does NOT import SvgHouseParser or
    RoomTypeInferenceV5 -- callers run those and pass the resulting
    House object (and, optionally, room_predictions) in.
    """

    def adapt(
        self,
        house: Any,
        room_predictions: list[Any] | None = None,
    ) -> AdaptedFloorplan:
        """
        Args:
            house: a duck-typed House object (see module docstring),
                as SvgHouseParser().parse(svg_path) would produce.
            room_predictions: optional list of duck-typed RoomPrediction
                objects (see module docstring), as
                RoomTypeInferenceV5.predict_svg() would produce. When
                given, predicted_room_type overrides the raw SVG class
                name for matching rooms (matched by room_id, per
                inference.py's own convention of using the parser's
                Room.id directly as RoomPrediction.room_id).
        """
        warnings: list[str] = []
        predictions_by_id: dict[str, Any] = {
            p.room_id: p for p in (room_predictions or [])
        }

        floors = getattr(house, "floors", [])
        if not floors:
            raise ValueError("SVG house has no floors to adapt.")
        if len(floors) > 1:
            warnings.append(
                f"SVG house has {len(floors)} floors; only the first "
                "floor is adapted (multi-floor SVG adaptation is not "
                "yet implemented)."
            )
        floor = floors[0]

        walls: list[dict[str, Any]] = []
        for wall in getattr(floor, "walls", []):
            wall_points_svg = _polygon_points(wall.polygon)
            wall_points_m = [
                (_to_metres(x), _to_metres(y)) for x, y in wall_points_svg
            ]

            try:
                start, end, thickness, wall_warnings = wall_polygon_to_centerline(
                    wall_points_m
                )
            except ValueError as exc:
                warnings.append(
                    f"Skipped wall {getattr(wall, 'id', '?')!r}: {exc}"
                )
                continue
            warnings.extend(
                f"Wall {getattr(wall, 'id', '?')!r}: {w}" for w in wall_warnings
            )

            openings: list[dict[str, Any]] = []
            for door in getattr(wall, "doors", []):
                door_points_m = [
                    (_to_metres(p.x), _to_metres(p.y)) for p in door.polygon
                ]
                offset, width = project_opening_onto_wall(door_points_m, start, end)
                if width <= 1e-6:
                    warnings.append(
                        f"Door {getattr(door, 'id', '?')!r} on wall "
                        f"{getattr(wall, 'id', '?')!r} projected to zero "
                        "width; skipped."
                    )
                    continue
                vertical = DEFAULT_OPENING_VERTICAL["door"]
                openings.append(
                    {
                        "id": f"svg-{getattr(door, 'id', 'door')}",
                        "type": "door",
                        "offset": offset,
                        "width": width,
                        "bottom": vertical["bottom"],
                        "height": vertical["height"],
                    }
                )

            for window in getattr(wall, "windows", []):
                window_points_m = [
                    (_to_metres(p.x), _to_metres(p.y)) for p in window.polygon
                ]
                offset, width = project_opening_onto_wall(
                    window_points_m, start, end
                )
                if width <= 1e-6:
                    warnings.append(
                        f"Window {getattr(window, 'id', '?')!r} on wall "
                        f"{getattr(wall, 'id', '?')!r} projected to zero "
                        "width; skipped."
                    )
                    continue
                vertical = DEFAULT_OPENING_VERTICAL["window"]
                openings.append(
                    {
                        "id": f"svg-{getattr(window, 'id', 'window')}",
                        "type": "window",
                        "offset": offset,
                        "width": width,
                        "bottom": vertical["bottom"],
                        "height": vertical["height"],
                    }
                )

            wall_type = getattr(wall, "wall_type", None)
            is_exterior = wall_type == "External" if wall_type else None

            walls.append(
                {
                    "id": f"svg-{getattr(wall, 'id', len(walls) + 1)}",
                    "x1": start[0],
                    "z1": start[1],
                    "x2": end[0],
                    "z2": end[1],
                    "height": DEFAULT_WALL_HEIGHT,
                    "thickness": thickness or DEFAULT_WALL_THICKNESS,
                    "isExterior": is_exterior,
                    "openings": openings,
                    "color": "#eee9e1",
                    "metadata": {"sourceWallId": getattr(wall, "id", None)},
                }
            )

        if not walls:
            raise ValueError(
                "No usable walls could be derived from the SVG's wall "
                "polygons."
            )

        rooms: list[dict[str, Any]] = []
        for room in getattr(floor, "rooms", []):
            room_points_svg = _polygon_points(room.polygon)
            room_points_m = [
                {"x": _to_metres(x), "z": _to_metres(y)}
                for x, y in room_points_svg
            ]

            room_type = getattr(room, "room_type", "Unknown")
            room_id = getattr(room, "id", f"room-{len(rooms) + 1}")

            prediction = predictions_by_id.get(room_id)
            if prediction is not None:
                room_type = getattr(prediction, "predicted_room_type", room_type)

            rooms.append(
                {
                    "id": f"svg-{room_id}",
                    "type": room_type,
                    "outline": room_points_m,
                }
            )

        if room_predictions and not predictions_by_id:
            warnings.append(
                "room_predictions was provided but empty after keying by "
                "room_id; no predicted types were applied."
            )
        elif room_predictions and len(predictions_by_id) < len(
            getattr(floor, "rooms", [])
        ):
            warnings.append(
                "Some rooms had no matching entry in room_predictions "
                "(room_id mismatch); those rooms keep their raw SVG "
                "class-derived room_type instead of a predicted type."
            )

        warnings.append(
            f"Coordinates converted from SVG units using an assumed "
            f"{SVG_PIXELS_PER_METER:.0f} pixels/metre scale (cited from "
            "zynora_ai/renderer/mesh_generator.py; NOT independently "
            "confirmed against a real CubiCasa SVG export, since none "
            "exists anywhere in this repository -- see module docstring)."
        )
        warnings.append(
            "Opening vertical position (bottom/height) is not present in "
            "2D SVG floor-plan data; fixed defaults were used per opening "
            "type rather than detected values."
        )

        return AdaptedFloorplan(
            walls=walls,
            outline=[],
            rooms=rooms,
            source_type="svg",
            warnings=warnings,
        )
