"""Workflow 1 floorplan adapters: existing floorplan -> canonical document.

STATUS: interface contracts only, per the P0 scope. No adapter here calls
the real parsers/classifiers/detectors yet -- wiring SvgAdapter and
RasterAdapter to SvgHouseParser/RoomTypeInferenceV5 and
image_plan_processor/wall_detector respectively is P1 work.

Both existing input paths are UNTOUCHED by this module:
  - zynora_ai.core.parser.svg_house_parser.SvgHouseParser
  - zynora_ai.core.ml.inference.RoomTypeInferenceV5
  - floorplan_engine.image_plan_processor.process_uploaded_floor_plan
  - floorplan_engine.wall_detector.detect_and_merge_walls

This package defines the shared shape an adapter must produce so both
input paths can feed the same canonical_builder.build_canonical_document()
regardless of how they parsed their input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AdaptedFloorplan:
    """The common output shape every Workflow 1 adapter must produce.

    Field names/units intentionally match what
    floorplan_engine.canonical_builder.build_canonical_document() already
    expects, so an adapter's job is purely "reshape parser/detector output
    into this," with no further translation needed downstream.

    Coordinates are metres, using the wallTopology.js convention of
    (x1, z1) -> (x2, z2) per wall -- NOT (x, y). This matters concretely
    for the raster path: image_plan_processor.convert_walls_to_json()
    emits pixel-derived walls as x1/y1/x2/y2, already origin-shifted and
    scaled to metres. Per the approved coordinate-transformation
    investigation (see raster_adapter.py), this is a PURE RENAME
    (y -> z, no flip, no re-scale, no re-origin) -- confirmed against two
    independent existing consumers (frontend normalizeFloorPlan.js and
    the Blender renderer) that already treat raster-style y the same way.
    """

    walls: list[dict[str, Any]]
    outline: list[dict[str, float]]
    rooms: list[dict[str, Any]] = field(default_factory=list)
    source_type: str = "unknown"
    warnings: list[str] = field(default_factory=list)


class FloorplanAdapter(Protocol):
    """Interface every Workflow 1 input adapter implements."""

    def adapt(self, raw_input: Any) -> AdaptedFloorplan:
        """Convert a parser/classifier/detector's raw output into
        AdaptedFloorplan. Must not raise for input the underlying parser
        already accepted -- validation of the *original* file (SVG/PDF/
        image) stays in the existing upload routes; this method only
        reshapes already-parsed data.
        """
        ...
