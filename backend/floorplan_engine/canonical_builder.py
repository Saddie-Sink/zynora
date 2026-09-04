"""Backend canonical FloorPlanDocument builder.

This module is a Python port of the geometry pipeline that currently lives
in the frontend at:

    frontend/src/components/viewerV2/utils/wallTopology.js
    frontend/src/components/viewerV2/utils/polygonMath.js (buildOutlineFromWalls)

It exists so that canonical ``zynora.floorplan.v1`` documents can be
assembled on the backend -- shared by Workflow 1 (existing floorplan
adapters) and Workflow 2 (user-input generator) -- instead of only being
assembled inside viewer-adjacent frontend code.

SCOPE / KNOWN LIMITATION (read before relying on this for production):

The JS implementation has an "outline repair" step (``repairOutlineWithRooms``
-> ``connectNearbyComponents`` -> polygon union via the ``polygon-clipping``
npm package) that repairs the exterior outline when indoor rooms fall outside
it, by unioning room polygons with the outline and bridging disconnected
pieces. That polygon-boolean-union machinery is NOT ported here yet -- it is
a nontrivial dependency (general polygon clipping) and porting it well
deserves its own dedicated pass rather than being rushed into this change.

When this module detects that rooms fall outside the given outline, it does
NOT attempt to repair it. It behaves the same way the JS code behaves in the
*unresolvable* case: it keeps the original outline unchanged and reports the
condition in ``stats``/``warnings`` so callers can see it happened, exactly as
``repairOutlineWithRooms`` falls back to the original outline when no
repaired candidate can be found. For any input where rooms fit inside the
given outline (the expected case for both structural_generator.py output and
correctly-adapted floorplan input), this module's behavior is a faithful,
tested match for the JS pipeline -- see backend/tests/test_canonical_builder.py
and the equivalence notes in that file.

Everything else in the pipeline (duplicate/collinear wall merging, endpoint
snapping, exterior-wall inference, closed-shell detection, outline tracing
for a closed exterior graph, shell-wall synthesis, opening remapping/merging,
and the canonical field mapping itself) is a faithful, tested port.
"""

from __future__ import annotations

import math
from typing import Any

EPSILON = 1e-6
ANGLE_COSINE = math.cos(math.radians(1.5))
OUTDOOR_ROOM_KEYWORDS = (
    "outdoor",
    "balcony",
    "terrace",
    "patio",
    "porch",
    "deck",
    "garden",
    "yard",
    "veranda",
    "loggia",
)


# ============================================================
# BASIC VECTOR / WALL HELPERS
# (port of wallTopology.js lines ~17-83)
# ============================================================


def _finite(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def wall_length(wall: dict[str, Any]) -> float:
    return math.hypot(wall["x2"] - wall["x1"], wall["z2"] - wall["z1"])


def wall_unit(wall: dict[str, Any]) -> dict[str, float]:
    length = wall_length(wall)
    if length < EPSILON:
        return {"x": 1.0, "z": 0.0}
    return {
        "x": (wall["x2"] - wall["x1"]) / length,
        "z": (wall["z2"] - wall["z1"]) / length,
    }


def _dot(point: dict[str, float], axis: dict[str, float]) -> float:
    return point["x"] * axis["x"] + point["z"] * axis["z"]


def _point_on_wall(wall: dict[str, Any], distance: float) -> dict[str, float]:
    unit = wall_unit(wall)
    return {
        "x": wall["x1"] + unit["x"] * distance,
        "z": wall["z1"] + unit["z"] * distance,
    }


def _project_point(point: dict[str, float], wall: dict[str, Any]) -> float:
    unit = wall_unit(wall)
    return (point["x"] - wall["x1"]) * unit["x"] + (point["z"] - wall["z1"]) * unit["z"]


def _distance_to_segment(
    point: dict[str, float], start: dict[str, float], end: dict[str, float]
) -> float:
    dx = end["x"] - start["x"]
    dz = end["z"] - start["z"]
    length_squared = dx * dx + dz * dz
    if length_squared < EPSILON:
        return math.hypot(point["x"] - start["x"], point["z"] - start["z"])
    amount = max(
        0.0,
        min(
            1.0,
            ((point["x"] - start["x"]) * dx + (point["z"] - start["z"]) * dz)
            / length_squared,
        ),
    )
    return math.hypot(
        point["x"] - (start["x"] + dx * amount),
        point["z"] - (start["z"] + dz * amount),
    )


def normalize_exterior_flag(wall: dict[str, Any]) -> bool:
    direct = wall.get("isExterior", wall.get("is_exterior", wall.get("external", wall.get("exterior"))))
    if isinstance(direct, bool):
        return direct

    text = str(
        wall.get("wallClass")
        or wall.get("wall_class")
        or wall.get("className")
        or wall.get("kind")
        or (wall.get("metadata") or {}).get("wall_class")
        or ""
    )
    return bool(__import__("re").search(r"(^|\s)external(\s|$)", text, __import__("re").IGNORECASE))


# ============================================================
# OPENINGS
# (port of wallTopology.js lines ~108-191)
# ============================================================


def _opening_world_geometry(wall: dict[str, Any], opening: dict[str, Any]) -> dict[str, Any]:
    length = wall_length(wall)
    start = max(0.0, min(length, _finite(opening.get("start"))))
    end = max(
        start,
        min(length, _finite(opening.get("end"), start + _finite(opening.get("width"), 0.0))),
    )
    result = dict(opening)
    result["worldStart"] = _point_on_wall(wall, start)
    result["worldEnd"] = _point_on_wall(wall, end)
    return result


def remap_openings(wall: dict[str, Any], openings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    length = wall_length(wall)
    if length < EPSILON:
        return []

    remapped: list[dict[str, Any]] = []
    for index, opening in enumerate(openings):
        first = _project_point(opening["worldStart"], wall)
        second = _project_point(opening["worldEnd"], wall)
        start = max(0.0, min(length, min(first, second)))
        end = max(0.0, min(length, max(first, second)))
        width = end - start

        if width < 0.08:
            continue

        bottom = max(0.0, _finite(opening.get("bottom")))
        height = max(
            0.2,
            min(
                _finite(opening.get("height"), _finite(opening.get("top")) - bottom),
                max(wall["height"] - bottom, 0.2),
            ),
        )

        new_opening = dict(opening)
        new_opening.update(
            {
                "id": opening.get("id") or f"{wall['id']}-opening-{index}",
                "start": start,
                "end": end,
                "center": (start + end) / 2,
                "width": width,
                "bottom": bottom,
                "height": height,
                "top": bottom + height,
            }
        )
        remapped.append(new_opening)

    remapped.sort(key=lambda item: item["start"])
    return remapped


def merge_duplicate_openings(openings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for opening in openings:
        previous = merged[-1] if merged else None
        same_type = previous is not None and previous.get("type") == opening.get("type")
        overlaps = previous is not None and opening["start"] <= previous["end"] + 0.06
        same_height = previous is not None and (
            abs(previous["bottom"] - opening["bottom"]) <= 0.08
            and abs(previous["top"] - opening["top"]) <= 0.08
        )

        if not (same_type and overlaps and same_height):
            merged.append(dict(opening))
            continue

        previous["start"] = min(previous["start"], opening["start"])
        previous["end"] = max(previous["end"], opening["end"])
        previous["center"] = (previous["start"] + previous["end"]) / 2
        previous["width"] = previous["end"] - previous["start"]

    return merged


# ============================================================
# WALL MERGING
# (port of wallTopology.js lines ~193-322)
# ============================================================


def _wall_line_offset(wall: dict[str, Any], normal: dict[str, float]) -> float:
    return (
        _dot({"x": wall["x1"], "z": wall["z1"]}, normal)
        + _dot({"x": wall["x2"], "z": wall["z2"]}, normal)
    ) / 2


def _projected_interval(wall: dict[str, Any], axis: dict[str, float]) -> tuple[float, float]:
    first = _dot({"x": wall["x1"], "z": wall["z1"]}, axis)
    second = _dot({"x": wall["x2"], "z": wall["z2"]}, axis)
    return (min(first, second), max(first, second))


def _intervals_gap(left: tuple[float, float], right: tuple[float, float]) -> float:
    if left[1] < right[0]:
        return right[0] - left[1]
    if right[1] < left[0]:
        return left[0] - right[1]
    return 0.0


def _can_merge_walls(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_unit = wall_unit(left)
    right_unit = wall_unit(right)
    alignment = abs(left_unit["x"] * right_unit["x"] + left_unit["z"] * right_unit["z"])

    if alignment < ANGLE_COSINE:
        return False
    if left["isExterior"] != right["isExterior"]:
        return False

    normal = {"x": -left_unit["z"], "z": left_unit["x"]}
    line_distance = abs(_wall_line_offset(left, normal) - _wall_line_offset(right, normal))
    line_tolerance = max(0.025, min(left["thickness"], right["thickness"]) * 0.28)

    if line_distance > line_tolerance:
        return False

    gap = _intervals_gap(
        _projected_interval(left, left_unit),
        _projected_interval(right, left_unit),
    )
    return gap <= 0.035


def _merge_wall_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    axis = wall_unit(left)
    normal = {"x": -axis["z"], "z": axis["x"]}
    intervals = [_projected_interval(left, axis), _projected_interval(right, axis)]
    start_distance = min(intervals[0][0], intervals[1][0])
    end_distance = max(intervals[0][1], intervals[1][1])
    left_length = wall_length(left)
    right_length = wall_length(right)
    total_length = max(left_length + right_length, EPSILON)
    normal_offset = (
        _wall_line_offset(left, normal) * left_length
        + _wall_line_offset(right, normal) * right_length
    ) / total_length

    merged = dict(left)
    merged.update(
        {
            "x1": axis["x"] * start_distance + normal["x"] * normal_offset,
            "z1": axis["z"] * start_distance + normal["z"] * normal_offset,
            "x2": axis["x"] * end_distance + normal["x"] * normal_offset,
            "z2": axis["z"] * end_distance + normal["z"] * normal_offset,
            "height": max(left["height"], right["height"]),
            "thickness": max(left["thickness"], right["thickness"]),
            "sourceIds": [
                *(left.get("sourceIds") or [left.get("sourceId", left["id"])]),
                *(right.get("sourceIds") or [right.get("sourceId", right["id"])]),
            ],
        }
    )

    world_openings = [
        _opening_world_geometry(left, opening) for opening in (left.get("openings") or [])
    ] + [_opening_world_geometry(right, opening) for opening in (right.get("openings") or [])]

    merged["openings"] = merge_duplicate_openings(remap_openings(merged, world_openings))
    return merged


def merge_duplicate_walls(walls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for index, wall in enumerate(walls):
        item = dict(wall)
        item.setdefault("id", f"wall-{index}")
        item["isExterior"] = normalize_exterior_flag(wall)
        item["openings"] = list(wall.get("openings") or [])
        merged.append(item)

    changed = True
    while changed:
        changed = False
        left = 0
        while left < len(merged):
            right = left + 1
            found = False
            while right < len(merged):
                if _can_merge_walls(merged[left], merged[right]):
                    merged[left] = _merge_wall_pair(merged[left], merged[right])
                    del merged[right]
                    changed = True
                    found = True
                    break
                right += 1
            if found:
                break
            left += 1

    return merged


# ============================================================
# ENDPOINT SNAPPING
# (port of wallTopology.js lines ~324-426)
# ============================================================


def snap_wall_endpoints(walls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not walls:
        return []

    typical_thickness = max(0.08, sum(w["thickness"] for w in walls) / len(walls))
    tolerance = max(0.055, min(0.3, typical_thickness * 1.7))

    endpoints = []
    for wall_index, wall in enumerate(walls):
        endpoints.append({"wallIndex": wall_index, "side": "start", "x": wall["x1"], "z": wall["z1"]})
        endpoints.append({"wallIndex": wall_index, "side": "end", "x": wall["x2"], "z": wall["z2"]})

    parent = list(range(len(endpoints)))

    def root(index: int) -> int:
        current = index
        while parent[current] != current:
            parent[current] = parent[parent[current]]
            current = parent[current]
        return current

    def unite(left: int, right: int) -> None:
        left_root, right_root = root(left), root(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left in range(len(endpoints)):
        for right in range(left + 1, len(endpoints)):
            if endpoints[left]["wallIndex"] == endpoints[right]["wallIndex"]:
                continue
            if (
                math.hypot(
                    endpoints[left]["x"] - endpoints[right]["x"],
                    endpoints[left]["z"] - endpoints[right]["z"],
                )
                <= tolerance
            ):
                unite(left, right)

    clusters: dict[int, list[dict[str, Any]]] = {}
    for index, endpoint in enumerate(endpoints):
        key = root(index)
        clusters.setdefault(key, []).append(endpoint)

    snapped = []
    for wall in walls:
        item = dict(wall)
        item["openings"] = [_opening_world_geometry(wall, o) for o in (wall.get("openings") or [])]
        snapped.append(item)

    for cluster in clusters.values():
        if len(cluster) < 2:
            continue
        avg_x = sum(e["x"] for e in cluster) / len(cluster)
        avg_z = sum(e["z"] for e in cluster) / len(cluster)
        for endpoint in cluster:
            wall = snapped[endpoint["wallIndex"]]
            if endpoint["side"] == "start":
                wall["x1"], wall["z1"] = avg_x, avg_z
            else:
                wall["x2"], wall["z2"] = avg_x, avg_z

    result = []
    for wall in snapped:
        if wall_length(wall) < 0.04:
            continue
        wall["openings"] = merge_duplicate_openings(remap_openings(wall, wall.get("openings") or []))
        result.append(wall)

    return result


# ============================================================
# EXTERIOR-WALL INFERENCE
# (port of wallTopology.js lines ~428-473)
# ============================================================


def _wall_matches_outline(wall: dict[str, Any], outline: list[dict[str, float]]) -> bool:
    midpoint = {"x": (wall["x1"] + wall["x2"]) / 2, "z": (wall["z1"] + wall["z2"]) / 2}
    wall_direction = wall_unit(wall)
    tolerance = max(0.12, wall["thickness"] * 1.2)

    for index, start in enumerate(outline):
        end = outline[(index + 1) % len(outline)]
        edge_length = math.hypot(end["x"] - start["x"], end["z"] - start["z"])
        if edge_length < EPSILON:
            continue
        edge_direction = {"x": (end["x"] - start["x"]) / edge_length, "z": (end["z"] - start["z"]) / edge_length}
        parallel = abs(wall_direction["x"] * edge_direction["x"] + wall_direction["z"] * edge_direction["z"])
        if parallel >= 0.97 and _distance_to_segment(midpoint, start, end) <= tolerance:
            return True
    return False


def infer_exterior_walls(
    walls: list[dict[str, Any]], outline: list[dict[str, float]]
) -> list[dict[str, Any]]:
    explicitly_exterior = [w for w in walls if w["isExterior"]]
    if len(explicitly_exterior) >= 3:
        return walls

    result = []
    for wall in walls:
        item = dict(wall)
        item["isExterior"] = bool(
            wall["isExterior"] or (len(outline) >= 3 and _wall_matches_outline(wall, outline))
        )
        result.append(item)
    return result


# ============================================================
# GRAPH / SHELL HELPERS
# (port of wallTopology.js lines ~475-609)
# ============================================================


def graph_summary(walls: list[dict[str, Any]], tolerance: float = 0.08) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []

    def node_for(point: dict[str, float]) -> int:
        for index, node in enumerate(nodes):
            if math.hypot(node["x"] - point["x"], node["z"] - point["z"]) <= tolerance:
                return index
        nodes.append({"x": point["x"], "z": point["z"], "degree": 0, "neighbors": []})
        return len(nodes) - 1

    for wall in walls:
        start = node_for({"x": wall["x1"], "z": wall["z1"]})
        end = node_for({"x": wall["x2"], "z": wall["z2"]})
        nodes[start]["degree"] += 1
        nodes[end]["degree"] += 1
        nodes[start]["neighbors"].append(end)
        nodes[end]["neighbors"].append(start)

    visited: set[int] = set()
    queue = [0] if nodes else []
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for neighbor in nodes[current]["neighbors"]:
            if neighbor not in visited:
                queue.append(neighbor)

    closed = (
        len(walls) >= 3
        and len(nodes) >= 3
        and len(visited) == len(nodes)
        and all(node["degree"] == 2 for node in nodes)
    )

    return {
        "nodes": nodes,
        "connected": len(nodes) > 0 and len(visited) == len(nodes),
        "closed": closed,
        "openNodes": sum(1 for node in nodes if node["degree"] != 2),
    }


def _source_wall_for_edge(
    start: dict[str, float], end: dict[str, float], walls: list[dict[str, Any]]
) -> dict[str, Any] | None:
    edge_length = math.hypot(end["x"] - start["x"], end["z"] - start["z"])
    if edge_length < EPSILON:
        return None

    direction = {"x": (end["x"] - start["x"]) / edge_length, "z": (end["z"] - start["z"]) / edge_length}
    midpoint = {"x": (start["x"] + end["x"]) / 2, "z": (start["z"] + end["z"]) / 2}
    best_wall, best_distance = None, None

    for wall in walls:
        wall_direction = wall_unit(wall)
        parallel = abs(direction["x"] * wall_direction["x"] + direction["z"] * wall_direction["z"])
        if parallel < 0.94:
            continue
        distance = _distance_to_segment(
            midpoint, {"x": wall["x1"], "z": wall["z1"]}, {"x": wall["x2"], "z": wall["z2"]}
        )
        if best_distance is None or distance < best_distance:
            best_wall, best_distance = wall, distance

    return best_wall if best_distance is not None and best_distance <= 0.45 else None


def shell_from_outline(
    outline: list[dict[str, float]],
    source_walls: list[dict[str, Any]],
    all_walls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fallback_height = max(2.4, *(w.get("height", 2.8) for w in all_walls)) if all_walls else 2.4
    fallback_thickness = (
        max(0.12, sum(w["thickness"] for w in source_walls) / max(len(source_walls), 1))
        if source_walls
        else 0.12
    )

    shell_walls = []
    for index, start in enumerate(outline):
        end = outline[(index + 1) % len(outline)]
        source = _source_wall_for_edge(start, end, source_walls)

        shell_wall = dict(source) if source else {}
        shell_wall.update(
            {
                "id": f"shell-wall-{index}",
                "sourceId": (source or {}).get("sourceId", f"outline-{index}"),
                "x1": start["x"],
                "z1": start["z"],
                "x2": end["x"],
                "z2": end["z"],
                "height": (source or {}).get("height", fallback_height),
                "thickness": (source or {}).get("thickness", fallback_thickness),
                "color": (source or {}).get("color", "#e8e1d6"),
                "isExterior": True,
                "kind": "exterior",
                "openings": [],
            }
        )

        if source:
            world_openings = [_opening_world_geometry(source, o) for o in (source.get("openings") or [])]
            shell_wall["openings"] = remap_openings(shell_wall, world_openings)

        shell_walls.append(shell_wall)

    return shell_walls


def build_outline_from_walls(walls: list[dict[str, Any]]) -> list[dict[str, float]]:
    """Trace a closed exterior-wall loop into an ordered outline.

    Faithful port of the "every node has exactly 2 edges" branch of
    buildOutlineFromWalls() in polygonMath.js. The JS function has an
    additional convex-hull-style fallback for non-cyclic/disconnected wall
    sets; that fallback is not ported here because process_wall_topology()
    only calls this helper after graph_summary() has already confirmed the
    wall set forms a closed loop (mirroring how wallTopology.js gates its own
    call to buildOutlineFromWalls on `exteriorGraph.closed`).
    """
    if len(walls) < 3:
        return []

    tolerance_bounds = []
    for wall in walls:
        tolerance_bounds.extend([(wall["x1"], wall["z1"]), (wall["x2"], wall["z2"])])
    xs = [p[0] for p in tolerance_bounds]
    zs = [p[1] for p in tolerance_bounds]
    width = max(xs) - min(xs) if xs else 0
    depth = max(zs) - min(zs) if zs else 0
    tolerance = max(width, depth, 1) * 1e-4

    nodes: list[dict[str, Any]] = []

    def node_for(point: tuple[float, float]) -> int:
        for index, node in enumerate(nodes):
            if math.hypot(node["point"][0] - point[0], node["point"][1] - point[1]) <= tolerance:
                return index
        nodes.append({"point": point, "edges": []})
        return len(nodes) - 1

    edges = []
    for index, wall in enumerate(walls):
        start = node_for((wall["x1"], wall["z1"]))
        end = node_for((wall["x2"], wall["z2"]))
        edge = {"index": index, "start": start, "end": end}
        nodes[start]["edges"].append(edge)
        nodes[end]["edges"].append(edge)
        edges.append(edge)

    if not all(len(node["edges"]) == 2 for node in nodes):
        # Not a clean cycle -- caller should not have reached here (see
        # docstring); return empty so the caller's existing "outline.length
        # < 3" fallback path takes over, same as the JS function would end
        # up doing if this branch's precondition failed.
        return []

    current = sorted(range(len(nodes)), key=lambda i: (nodes[i]["point"][1], nodes[i]["point"][0]))[0]
    used: set[int] = set()
    ordered: list[tuple[float, float]] = []

    while len(ordered) <= len(edges):
        ordered.append(nodes[current]["point"])
        next_edge = next((e for e in nodes[current]["edges"] if e["index"] not in used), None)
        if next_edge is None:
            break
        used.add(next_edge["index"])
        current = next_edge["end"] if next_edge["start"] == current else next_edge["start"]

    # Drop the closing duplicate of the starting point, matching the JS
    # polygon convention of not repeating the first vertex at the end.
    if len(ordered) > 1 and ordered[0] == ordered[-1]:
        ordered = ordered[:-1]

    return [{"x": p[0], "z": p[1]} for p in ordered]


def sanitize_polygon(points: list[dict[str, float]] | None) -> list[dict[str, float]]:
    """Minimal port of polygonMath.js's sanitizePolygon: drop invalid points
    and collapse consecutive duplicates. Does not perform the JS version's
    optional Douglas-Peucker simplification pass -- outline simplification is
    not exercised by process_wall_topology()'s happy path (identical wall
    endpoints already collapse via snap_wall_endpoints), so it is left for a
    follow-up if a caller's outline actually needs it.
    """
    if not points:
        return []

    cleaned = []
    for point in points:
        try:
            x, z = float(point["x"]), float(point["z"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (math.isfinite(x) and math.isfinite(z)):
            continue
        if cleaned and math.hypot(x - cleaned[-1]["x"], z - cleaned[-1]["z"]) < 1e-9:
            continue
        cleaned.append({"x": x, "z": z})

    if len(cleaned) > 1 and math.hypot(
        cleaned[0]["x"] - cleaned[-1]["x"], cleaned[0]["z"] - cleaned[-1]["z"]
    ) < 1e-9:
        cleaned.pop()

    return cleaned


def _rooms_outside_outline(rooms: list[dict[str, Any]], outline: list[dict[str, float]]) -> list[dict[str, Any]]:
    """Simplified stand-in for wallTopology.js's roomsOutsideOutline(): flags
    rooms whose centroid falls outside the outline. The JS version performs a
    full polygon-containment check (polygonContainsPolygon with tolerance);
    this centroid check is a conservative approximation used only to decide
    whether the (unported) outline-repair path would have been triggered --
    see the module docstring's KNOWN LIMITATION section.
    """

    def is_indoor(room: dict[str, Any]) -> bool:
        if isinstance(room.get("isOutdoor"), bool):
            return not room["isOutdoor"]
        description = str(
            room.get("structuralRoomType")
            or room.get("originalRoomType")
            or room.get("roomType")
            or room.get("roomName")
            or room.get("predicted_room_type")
            or room.get("type")
            or "Room"
        ).lower()
        return not any(keyword in description for keyword in OUTDOOR_ROOM_KEYWORDS)

    def point_in_polygon(point: tuple[float, float], polygon: list[dict[str, float]]) -> bool:
        x, z = point
        inside = False
        n = len(polygon)
        for i in range(n):
            xi, zi = polygon[i]["x"], polygon[i]["z"]
            xj, zj = polygon[(i - 1) % n]["x"], polygon[(i - 1) % n]["z"]
            if ((zi > z) != (zj > z)) and (
                x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi
            ):
                inside = not inside
        return inside

    outside = []
    if len(outline) < 3:
        return outside

    for room in rooms:
        outline_pts = room.get("outline") or []
        if len(outline_pts) < 3 or not is_indoor(room):
            continue
        centroid_x = sum(p["x"] for p in outline_pts) / len(outline_pts)
        centroid_z = sum(p["z"] for p in outline_pts) / len(outline_pts)
        if not point_in_polygon((centroid_x, centroid_z), outline):
            outside.append(room)

    return outside


# ============================================================
# TOP-LEVEL PIPELINE
# (port of wallTopology.js processWallTopology(), lines ~832-914)
# ============================================================


def process_wall_topology(
    walls: list[dict[str, Any]],
    outline: list[dict[str, float]],
    rooms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rooms = rooms or []
    original_count = len(walls)
    safe_outline = sanitize_polygon(outline)

    merged = merge_duplicate_walls(walls)
    snapped = snap_wall_endpoints(merged)
    classified = infer_exterior_walls(snapped, safe_outline)
    exterior_walls = [w for w in classified if w["isExterior"]]
    exterior_graph = graph_summary(exterior_walls)

    if exterior_graph["closed"]:
        exterior_outline = sanitize_polygon(build_outline_from_walls(exterior_walls))
    else:
        exterior_outline = safe_outline

    if len(exterior_outline) < 3:
        exterior_outline = sanitize_polygon(
            build_outline_from_walls(exterior_walls if exterior_walls else classified)
        )

    outside_rooms = _rooms_outside_outline(rooms, exterior_outline)
    repaired = False  # outline-repair-via-union not ported; see module docstring
    average_thickness = (
        sum(_finite(w.get("thickness"), 0.16) for w in classified) / max(len(classified), 1)
        if classified
        else 0.16
    )

    shell_walls: list[dict[str, Any]]
    if exterior_graph["closed"] and not repaired:
        shell_walls = [{**w, "kind": "exterior"} for w in exterior_walls]
    else:
        shell_walls = shell_from_outline(exterior_outline, exterior_walls, classified)

    thicknesses = sorted(
        t for t in (_finite(w.get("thickness"), average_thickness) for w in shell_walls) if t > 0
    )
    shell_thickness = thicknesses[len(thicknesses) // 2] if thicknesses else max(average_thickness, 0.12)
    shell_walls = [{**w, "thickness": shell_thickness} for w in shell_walls]

    shell_graph = graph_summary(shell_walls, tolerance=0.0001)

    return {
        "walls": classified,
        "shellWalls": shell_walls,
        "exteriorOutline": exterior_outline,
        "stats": {
            "sourceWalls": original_count,
            "mergedWalls": len(classified),
            "duplicateWallsRemoved": max(0, original_count - len(classified)),
            "exteriorWalls": len(shell_walls),
            "exteriorShellClosed": shell_graph["closed"],
            "exteriorOpenNodes": shell_graph["openNodes"],
            "shellRepairedFromRooms": repaired,
            "roomsOutsideOriginalShell": len(outside_rooms),
            "outlineRepairNotSupported": bool(outside_rooms),
        },
    }


# ============================================================
# CANONICAL DOCUMENT MAPPING
# (port of wallTopology.js lines ~1145-1267)
# ============================================================


def _copy_point(point: dict[str, float]) -> dict[str, float]:
    return {"x": round(float(point["x"]), 5), "z": round(float(point["z"]), 5)}


def canonical_opening(wall: dict[str, Any], opening: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(opening["id"]),
        "wallId": str(wall["id"]),
        "type": "window" if opening.get("type") == "window" else "door",
        "offset": round(float(opening["start"]), 5),
        "width": round(float(opening["width"]), 5),
        "bottom": round(float(opening["bottom"]), 5),
        "height": round(float(opening["height"]), 5),
    }


def canonical_wall(wall: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(wall["id"]),
        "start": _copy_point({"x": wall["x1"], "z": wall["z1"]}),
        "end": _copy_point({"x": wall["x2"], "z": wall["z2"]}),
        "height": round(float(wall["height"]), 5),
        "thickness": round(float(wall["thickness"]), 5),
        "isExterior": bool(wall.get("isExterior", False)),
        "material": {"color": wall.get("color", "#eee9e1")},
        "openings": [canonical_opening(wall, o) for o in (wall.get("openings") or [])],
    }


def canonical_room(room: dict[str, Any]) -> dict[str, Any]:
    classification = None
    if room.get("classificationMatched"):
        classification = {
            "modelVersion": room.get("modelVersion", "v5"),
            "predictedType": str(room.get("predicted_room_type") or room.get("roomType")),
            "confidence": round(_finite(room.get("confidence")), 6),
            "status": str(room.get("confidence_status", "unknown")),
        }

    return {
        "id": str(room.get("id") or room.get("room_id")),
        "type": str(room.get("roomType") or room.get("predicted_room_type") or room.get("type") or "Room"),
        "outline": [_copy_point(p) for p in (room.get("outline") or [])],
        "area": round(_finite(room.get("area")), 5),
        "classification": classification,
    }


def canonical_floor(plan: dict[str, Any], index: int) -> dict[str, Any]:
    outline_source = plan.get("exteriorOutline") or plan["outline"]
    outline = [_copy_point(p) for p in outline_source]
    floor_id = str(plan.get("floorId") or plan.get("id") or f"floor-{index + 1}")
    elevation = _finite(plan.get("elevation"))
    roof = plan.get("roof") or {}
    slab = plan.get("slab") or {}

    return {
        "id": floor_id,
        "level": round(_finite(plan.get("floorIndex", plan.get("level", index)))),
        "elevation": round(elevation, 5),
        "height": round(float(plan["height"]), 5),
        "outline": outline,
        "rooms": [canonical_room(r) for r in (plan.get("rooms") or [])],
        "walls": [canonical_wall(w) for w in (plan.get("walls") or [])],
        "exteriorWalls": [canonical_wall(w) for w in (plan.get("shellWalls") or [])],
        "slabs": [
            {
                "id": str(slab.get("id") or f"{floor_id}-slab"),
                "outline": outline,
                "elevation": round(elevation + _finite(slab.get("elevation"), -0.16), 5),
                "thickness": _finite(slab.get("thickness"), 0.18),
            }
        ],
        "roof": {
            "id": str(roof.get("id") or f"{floor_id}-roof"),
            "type": str(roof.get("type", "flat")),
            "outline": outline,
            "elevation": round(elevation + _finite(roof.get("elevation"), plan["height"]), 5),
            "thickness": _finite(roof.get("thickness"), 0.22),
            "parapetHeight": _finite(roof.get("parapetHeight"), 0.35),
        },
    }


def create_floor_plan_document(plan: dict[str, Any], validation: dict[str, Any] | None = None) -> dict[str, Any]:
    floor_plans = plan["floors"] if plan.get("floors") else [plan]
    floors = [canonical_floor(floor_plan, index) for index, floor_plan in enumerate(floor_plans)]
    active_floor_id = str(plan.get("activeFloorId") or plan.get("floorId") or floors[0]["id"])

    return {
        "schemaVersion": "zynora.floorplan.v1",
        "id": str(plan.get("id", "zynora-floor-plan")),
        "unit": "m",
        "coordinateSystem": "x-right_y-up_z-forward",
        "metadata": {
            "source": str(plan.get("sourceType", "generated")),
            "floorCount": len(floors),
            "activeFloorId": active_floor_id,
            "roomClassifier": plan.get("classifierVersion", "v5"),
        },
        "floors": floors,
        "validation": validation,
    }


# ============================================================
# CONVENIENCE ENTRY POINT
# ============================================================


def build_canonical_document(
    walls: list[dict[str, Any]],
    outline: list[dict[str, float]],
    *,
    rooms: list[dict[str, Any]] | None = None,
    plan_id: str = "zynora-floor-plan",
    floor_id: str = "ground-floor",
    floor_index: int = 0,
    height: float = 2.8,
    source_type: str = "generated",
    slab: dict[str, Any] | None = None,
    roof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One-call helper: raw walls/outline/rooms -> canonical FloorPlanDocument.

    This is the function Workflow 1 adapters and Workflow 2's generator
    integration are expected to call once P1 wires them up.
    """
    rooms = rooms or []
    topology = process_wall_topology(walls, outline, rooms)

    plan = {
        "id": plan_id,
        "floorId": floor_id,
        "floorIndex": floor_index,
        "floorCount": 1,
        "sourceType": source_type,
        "height": height,
        "outline": topology["exteriorOutline"],
        "exteriorOutline": topology["exteriorOutline"],
        "rooms": rooms,
        "walls": topology["walls"],
        "shellWalls": topology["shellWalls"],
        "slab": slab or {"elevation": -0.16, "thickness": 0.18},
        "roof": roof or {"type": "flat", "elevation": height, "thickness": 0.22, "parapetHeight": 0.35},
    }

    document = create_floor_plan_document(plan)
    return {"document": document, "topology_stats": topology["stats"]}
