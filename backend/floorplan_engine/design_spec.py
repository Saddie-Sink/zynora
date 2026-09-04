"""StructuredDesignSpec -- the contract between AI design reasoning
(Gemini) and the deterministic floorplan generator (structural_generator.py).

STATUS: contract only, per the P0 scope. Nothing in this module is wired
into gemini_service.py or structural_generator.py yet -- that integration
is P1 work. This file exists so the contract can be reviewed and agreed on
before any wiring happens.

DESIGN PRINCIPLE (per the approved architecture):

    Gemini reasons about things the deterministic generator does NOT
    already decide well: style, massing variety, and priority among
    ambiguous room trade-offs.

    Gemini does NOT re-decide things the generator already handles
    deterministically: exact room adjacency, door placement, wall
    geometry, dimensions. Those stay entirely inside
    structural_generator.py's existing logic (_touching, _preferred_room,
    _generate_internal_doors, etc.).

This keeps the spec intentionally narrow. A wider spec (room-relationship
graphs, explicit dimensional constraints, circulation rules) would create a
second, competing source of truth for decisions the generator already
makes -- which is the exact failure mode the two-workflow architecture is
meant to avoid.

INTEGRATION CONTRACT (for the P1 wiring task):

    structural_generator.generate_structural_candidates() already accepts
    an open-ended `project: dict[str, Any]`. The plan for P1 is to attach
    a StructuredDesignSpec under `project["design_spec"]` and have the
    generator read it as OPTIONAL, additive hints -- never required
    input. When no spec is present (Gemini unavailable, or Workflow 1
    doesn't use it), the generator must behave exactly as it does today.
    This module does not implement that reading; it defines the shape
    the generator will eventually read.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoomPriority(BaseModel):
    """One room the user/AI considers important enough to protect when the
    generator has to make a trade-off (e.g. which room loses space first
    on a tight plot)."""

    model_config = ConfigDict(extra="forbid")

    room_type: str = Field(
        min_length=1,
        max_length=80,
        description=(
            "Matches a room type the generator already produces, e.g. "
            "'master-bedroom', 'living', 'kitchen'. Free text, not an "
            "enum, since structural_generator.py's own room types are "
            "not a closed enum today."
        ),
    )
    priority: Literal["high", "medium", "low"] = "medium"


class MassingHints(BaseModel):
    """Massing-level preferences. These map to real geometry gaps
    identified in the architecture review (terrace/porch are not yet
    implemented in structural_generator.py or the Blender renderer --
    see the P2 roadmap item). Until that geometry exists, the generator
    should treat these as best-effort hints it may not yet be able to
    satisfy, not as hard requirements."""

    model_config = ConfigDict(extra="forbid")

    wants_terrace: bool = False
    wants_porch: bool = False
    wants_double_height_volume: bool = False


class StructuredDesignSpec(BaseModel):
    """The full, intentionally narrow contract Gemini produces and the
    generator may optionally consume.

    Every field is optional with a safe default so that a partially-filled
    or entirely-empty spec never breaks generation -- the generator must
    remain fully functional with `StructuredDesignSpec()` (all defaults).
    """

    model_config = ConfigDict(extra="forbid")

    room_priorities: list[RoomPriority] = Field(default_factory=list)

    style_tags: list[str] = Field(
        default_factory=list,
        max_length=8,
        description=(
            "Free-text style descriptors, e.g. ['contemporary', "
            "'flat-roof', 'minimal-ornament']. Currently has no consumer "
            "in structural_generator.py; intended to eventually inform "
            "Blender's material `style` selection (warm-modern / "
            "graphite-white / sandstone) rather than room geometry."
        ),
    )

    massing_hints: MassingHints = Field(default_factory=MassingHints)

    material_preference: (
        Literal["warm-modern", "graphite-white", "sandstone"] | None
    ) = Field(
        default=None,
        description=(
            "Maps directly to the existing Blender render style enum "
            "(see routes/blender_render.py BlenderRenderJobRequest.style) "
            "-- this is a real, already-existing enum, not a new one."
        ),
    )

    notes_summary: str = Field(
        default="",
        max_length=500,
        description=(
            "Free text for display only. Non-binding -- must not be "
            "parsed for instructions by the generator."
        ),
    )

    def is_empty(self) -> bool:
        """True when the spec carries no actual guidance, i.e. the
        generator should behave identically to having no spec at all."""
        return (
            not self.room_priorities
            and not self.style_tags
            and not self.massing_hints.wants_terrace
            and not self.massing_hints.wants_porch
            and not self.massing_hints.wants_double_height_volume
            and self.material_preference is None
        )
