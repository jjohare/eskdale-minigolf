"""
Build Holes 2, 3, and 4 of the mini golf course.

Hole 2: "The Cascade" (Par 3) - S-curve with bumper stones, Tier 1 to Tier 2
Hole 3: "The Bridge" (Par 3) - Elevated bridge over gully, Tier 2
Hole 4: "The Spiral" (Par 3) - 270-degree banked spiral, Tier 2 to Tier 3

Coordinate system: X = width (0-10m), Y = depth uphill (0-15m), Z = height.
Course descends in +Y direction. Z=0 at top, negative Z going down.

Elevation reference:
  Tier 1 (H1-H2 start): Z = 0.0
  Tier 2 (H2 end, H3):  Z = -0.3
  Tier 3 (H3 end):      Z = -0.6
  Tier 4 (H4 end):      Z = -1.1

Requires existing collections: Hole_2, Hole_3, Hole_4 with sub-collections.
Requires existing materials: ArtificialTurf, PuttingGreen, StoneBorder, etc.
Missing materials/collections are created automatically as fallbacks.

Usage:
  Executed via WebSocket to a running Blender instance, or run directly
  in Blender's Python console / scripting workspace.
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# Import utilities. Try the module first; if unavailable (e.g. WebSocket
# exec() context where sys.path is not set up), fall back to scanning
# known locations, and finally define inline stubs.
import sys
import os

_imported_utils = False
# Attempt 1: direct import (works when scripts/ is on sys.path)
_script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else ''
if _script_dir and _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)
try:
    from hole_builder_utils import (
        lerp, lerp_vec, catmull_rom_chain,
        ensure_materials, ensure_collection,
        create_mesh_object, build_path_mesh, build_border_rail,
        build_cup, build_flag, build_green_surface, build_tee_marker,
    )
    _imported_utils = True
except ImportError:
    pass

# Attempt 2: read the utils file from known project path
if not _imported_utils:
    _candidates = [
        '/home/devuser/workspace/minigolf/scripts/hole_builder_utils.py',
    ]
    if hasattr(bpy.data, 'filepath') and bpy.data.filepath:
        _blend_dir = os.path.dirname(bpy.data.filepath)
        _candidates.insert(0, os.path.join(_blend_dir, 'scripts', 'hole_builder_utils.py'))
    for _path in _candidates:
        if os.path.isfile(_path):
            exec(compile(open(_path).read(), _path, 'exec'))
            _imported_utils = True
            break

if not _imported_utils:
    raise ImportError(
        "Could not import hole_builder_utils. Ensure it exists at "
        "/home/devuser/workspace/minigolf/scripts/hole_builder_utils.py"
    )


# ---------------------------------------------------------------------------
# HOLE 2: "The Cascade" (Par 3)
# Tier 1 -> Tier 2, drop 0.3m. S-curve fairway with two bumper stones.
# Start: ~(3, 3.2, 0.0)  Green: ~(7, 4.5, -0.3)
# ---------------------------------------------------------------------------

def build_hole_2():
    print("[Hole 2] Building 'The Cascade' (Par 3)...")

    for sub in ("H2_Fairway", "H2_Green", "H2_Borders", "H2_Obstacles", "H2_Decorations"):
        ensure_collection(sub, "Hole_2")

    # S-curve centerline going east across the course while descending
    control_points = [
        Vector((3.0, 3.2, 0.0)),
        Vector((3.8, 3.0, -0.05)),
        Vector((4.8, 3.5, -0.12)),
        Vector((5.5, 4.2, -0.18)),
        Vector((6.2, 4.0, -0.24)),
        Vector((6.8, 4.3, -0.28)),
        Vector((7.0, 4.5, -0.30)),
    ]
    centerline = catmull_rom_chain(control_points, segments_per_span=16)
    width = 1.2

    # Fairway
    print("[Hole 2]   Fairway...")
    fairway = create_mesh_object("H2_Fairway", "H2_Fairway", "ArtificialTurf")
    build_path_mesh(fairway, centerline, width)

    # Borders
    print("[Hole 2]   Borders...")
    borders = create_mesh_object("H2_Borders", "H2_Borders", "StoneBorder")
    build_border_rail(borders, centerline, width, height=0.1, thickness=0.05)

    # Green
    print("[Hole 2]   Green...")
    green_center = Vector((7.0, 4.5, -0.30))
    build_green_surface("H2_Green", green_center, 0.6, -0.30, "H2_Green")

    # Cup + flag
    print("[Hole 2]   Cup & flag...")
    build_cup("H2_Cup", green_center, "H2_Green")
    build_flag("H2_Flag", green_center, "H2_Green")

    # Bumper stones (chicane at 40% and 60% along path)
    print("[Hole 2]   Bumper stones...")
    _build_bumper_stone("H2_BumperStone_1", centerline, 0.40, Vector((0.25, 0.1, 0)))
    _build_bumper_stone("H2_BumperStone_2", centerline, 0.60, Vector((-0.25, -0.1, 0)))

    # Tee marker
    build_tee_marker("H2_TeeMarker", centerline[0], "H2_Decorations")

    print("[Hole 2] Complete.")


def _build_bumper_stone(name, centerline, pct, offset):
    """Place an irregular bumper stone at a percentage along the centerline."""
    idx = int(len(centerline) * pct)
    pos = centerline[idx] + offset
    stone = create_mesh_object(name, "H2_Obstacles", "NaturalStone")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.15)
    for v in bm.verts:
        v.co.z *= 0.6  # Flatten
    bm.to_mesh(stone.data)
    bm.free()
    stone.location = Vector((pos.x, pos.y, pos.z + 0.08))
    stone.data.update()


# ---------------------------------------------------------------------------
# HOLE 3: "The Bridge" (Par 3)
# Tier 2, drop 0.3m. Bridge over planted gully, left turn to green.
# Start: ~(7, 4.8, -0.3)  Green: ~(3, 6.0, -0.6)
# ---------------------------------------------------------------------------

def build_hole_3():
    print("[Hole 3] Building 'The Bridge' (Par 3)...")

    for sub in ("H3_Fairway", "H3_Green", "H3_Borders", "H3_Obstacles", "H3_Decorations"):
        ensure_collection(sub, "Hole_3")

    control_points = [
        Vector((7.0, 4.8, -0.30)),
        Vector((6.5, 5.0, -0.33)),
        Vector((6.0, 5.2, -0.35)),
        Vector((5.5, 5.4, -0.38)),
        Vector((5.0, 5.5, -0.42)),
        Vector((4.5, 5.6, -0.46)),
        Vector((4.0, 5.8, -0.50)),
        Vector((3.5, 5.9, -0.55)),
        Vector((3.0, 6.0, -0.60)),
    ]
    centerline = catmull_rom_chain(control_points, segments_per_span=14)
    width = 1.2

    # Fairway
    print("[Hole 3]   Fairway...")
    fairway = create_mesh_object("H3_Fairway", "H3_Fairway", "ArtificialTurf")
    build_path_mesh(fairway, centerline, width)

    # Borders: split around bridge (no stone borders on the bridge itself)
    total = len(centerline)
    bridge_start_pct = 0.30
    bridge_end_pct = 0.60
    pre_bridge = centerline[:int(total * bridge_start_pct) + 1]
    post_bridge = centerline[int(total * bridge_end_pct):]

    print("[Hole 3]   Borders (pre-bridge)...")
    bp = create_mesh_object("H3_Borders_Pre", "H3_Borders", "StoneBorder")
    build_border_rail(bp, pre_bridge, width, height=0.1, thickness=0.05)

    print("[Hole 3]   Borders (post-bridge)...")
    ba = create_mesh_object("H3_Borders_Post", "H3_Borders", "StoneBorder")
    build_border_rail(ba, post_bridge, width, height=0.1, thickness=0.05)

    # Bridge structure
    bridge_cl = centerline[int(total * bridge_start_pct):int(total * bridge_end_pct) + 1]
    _build_bridge_deck(bridge_cl)
    _build_bridge_rails(bridge_cl)
    _build_gully(bridge_cl)

    # Green
    print("[Hole 3]   Green...")
    green_center = Vector((3.0, 6.0, -0.60))
    build_green_surface("H3_Green", green_center, 0.6, -0.60, "H3_Green")

    # Cup + flag
    print("[Hole 3]   Cup & flag...")
    build_cup("H3_Cup", green_center, "H3_Green")
    build_flag("H3_Flag", green_center, "H3_Green")

    # Tee marker
    build_tee_marker("H3_TeeMarker", centerline[0], "H3_Decorations")

    print("[Hole 3] Complete.")


def _build_bridge_deck(bridge_cl):
    """Build wooden plank bridge deck over the gully."""
    print("[Hole 3]   Bridge deck...")
    bridge_width = 0.6
    plank_thickness = 0.04
    plank_offset = 0.02

    deck = create_mesh_object("H3_Bridge_Deck", "H3_Obstacles", "WoodRail")
    bm = bmesh.new()
    half_w = bridge_width / 2.0
    prev = None

    for i, pt in enumerate(bridge_cl):
        if i == 0:
            tangent = (bridge_cl[min(1, len(bridge_cl)-1)] - bridge_cl[0]).normalized()
        elif i == len(bridge_cl) - 1:
            tangent = (bridge_cl[-1] - bridge_cl[max(0, len(bridge_cl)-2)]).normalized()
        else:
            tangent = (bridge_cl[i+1] - bridge_cl[i-1]).normalized()

        perp = Vector((-tangent.y, tangent.x, 0)).normalized()

        lb = pt + perp * half_w + Vector((0, 0, plank_offset))
        rb = pt - perp * half_w + Vector((0, 0, plank_offset))
        lt = lb + Vector((0, 0, plank_thickness))
        rt = rb + Vector((0, 0, plank_thickness))

        v0, v1, v2, v3 = (bm.verts.new(lb), bm.verts.new(rb),
                           bm.verts.new(rt), bm.verts.new(lt))
        curr = (v0, v1, v2, v3)

        if prev is not None:
            pv, cv = prev, curr
            for quad in (
                [pv[3], pv[2], cv[2], cv[3]],  # top
                [pv[0], cv[0], cv[1], pv[1]],  # bottom
                [pv[0], pv[3], cv[3], cv[0]],  # left side
                [pv[1], cv[1], cv[2], pv[2]],  # right side
            ):
                try:
                    bm.faces.new(quad)
                except ValueError:
                    pass
        prev = curr

    bm.to_mesh(deck.data)
    bm.free()
    deck.data.update()


def _build_bridge_rails(bridge_cl):
    """Build low wooden side rails on the bridge."""
    print("[Hole 3]   Bridge rails...")
    rails = create_mesh_object("H3_Bridge_Rails", "H3_Obstacles", "WoodDark")
    build_border_rail(rails, bridge_cl, 0.6, height=0.08, thickness=0.03)


def _build_gully(bridge_cl):
    """Build the planted gully depression beneath the bridge."""
    print("[Hole 3]   Gully...")
    gully = create_mesh_object("H3_Gully", "H3_Decorations", "GullyDirt")
    bm = bmesh.new()

    gully_width = 1.8
    gully_depth = 0.25
    gully_hw = gully_width / 2.0
    prev = None

    for i, pt in enumerate(bridge_cl):
        if i == 0:
            tangent = (bridge_cl[min(1, len(bridge_cl)-1)] - bridge_cl[0]).normalized()
        elif i == len(bridge_cl) - 1:
            tangent = (bridge_cl[-1] - bridge_cl[max(0, len(bridge_cl)-2)]).normalized()
        else:
            tangent = (bridge_cl[i+1] - bridge_cl[i-1]).normalized()

        perp = Vector((-tangent.y, tangent.x, 0)).normalized()

        lt = pt + perp * gully_hw
        rt = pt - perp * gully_hw
        lb = pt + perp * (gully_hw * 0.4) + Vector((0, 0, -gully_depth))
        rb = pt - perp * (gully_hw * 0.4) + Vector((0, 0, -gully_depth))

        v0, v1, v2, v3 = (bm.verts.new(lt), bm.verts.new(lb),
                           bm.verts.new(rb), bm.verts.new(rt))
        curr = (v0, v1, v2, v3)

        if prev is not None:
            pv, cv = prev, curr
            for quad in (
                [pv[0], pv[1], cv[1], cv[0]],  # left slope
                [pv[1], pv[2], cv[2], cv[1]],  # bottom
                [pv[2], pv[3], cv[3], cv[2]],  # right slope
            ):
                try:
                    bm.faces.new(quad)
                except ValueError:
                    pass
        prev = curr

    bm.to_mesh(gully.data)
    bm.free()
    gully.data.update()


# ---------------------------------------------------------------------------
# HOLE 4: "The Spiral" (Par 3)
# Tier 2 -> Tier 3, drop 0.5m. 270-degree banked spiral around rock mound.
# Start: ~(3, 6.3, -0.6)  Green: ~(5, 8.0, -1.1)
# ---------------------------------------------------------------------------

def build_hole_4():
    print("[Hole 4] Building 'The Spiral' (Par 3)...")

    for sub in ("H4_Fairway", "H4_Green", "H4_Borders", "H4_Obstacles", "H4_Decorations"):
        ensure_collection(sub, "Hole_4")

    spiral_center = Vector((4.5, 7.5, 0))
    spiral_radius = 1.5
    spiral_width = 1.0
    start_z = -0.60
    end_z = -1.10
    green_center = Vector((5.0, 8.0, end_z))

    # Lead-in from H3 green area
    lead_in = [
        Vector((3.0, 6.3, -0.60)),
        Vector((3.3, 6.6, -0.62)),
        Vector((3.6, 6.9, -0.64)),
        Vector((3.9, 7.2, -0.66)),
    ]

    # 270-degree spiral (clockwise when viewed from above)
    start_angle = math.radians(200)
    sweep = math.radians(270)
    n_seg = 60
    spiral_pts = []
    for i in range(n_seg + 1):
        t = i / n_seg
        angle = start_angle - sweep * t
        z = lerp(-0.66, end_z, t)
        x = spiral_center.x + spiral_radius * math.cos(angle)
        y = spiral_center.y + spiral_radius * math.sin(angle)
        spiral_pts.append(Vector((x, y, z)))

    # Lead-out to green
    last = spiral_pts[-1]
    lead_out = [
        last,
        lerp_vec(last, green_center, 0.33),
        lerp_vec(last, green_center, 0.66),
        green_center,
    ]
    for i, pt in enumerate(lead_out):
        pt.z = lerp(last.z, end_z, i / max(1, len(lead_out) - 1))

    all_pts = lead_in + spiral_pts + lead_out[1:]
    centerline = catmull_rom_chain(all_pts, segments_per_span=8)

    # Banked fairway
    print("[Hole 4]   Spiral fairway (banked)...")
    _build_banked_fairway(centerline, spiral_center, spiral_width, start_z, end_z)

    # Borders
    print("[Hole 4]   Borders...")
    borders = create_mesh_object("H4_Borders", "H4_Borders", "StoneBorder")
    build_border_rail(borders, centerline, spiral_width, height=0.1, thickness=0.05)

    # Central rock mound
    print("[Hole 4]   Rock mound...")
    _build_rock_mound(spiral_center, start_z, end_z)

    # Accent rocks
    print("[Hole 4]   Accent rocks...")
    _build_accent_rocks(spiral_center, start_z, end_z)

    # Green
    print("[Hole 4]   Green...")
    build_green_surface("H4_Green", green_center, 0.6, end_z, "H4_Green")

    # Cup + flag
    print("[Hole 4]   Cup & flag...")
    build_cup("H4_Cup", green_center, "H4_Green")
    build_flag("H4_Flag", green_center, "H4_Green")

    # Tee marker
    build_tee_marker("H4_TeeMarker", centerline[0], "H4_Decorations")

    print("[Hole 4] Complete.")


def _build_banked_fairway(centerline, spiral_center, width, start_z, end_z):
    """Build the spiral fairway with inward banking on curved sections."""
    fairway = create_mesh_object("H4_Fairway", "H4_Fairway", "ArtificialTurf")
    bm = bmesh.new()

    half_w = width / 2.0
    lead_margin = len(centerline) // 6  # approximate lead-in/lead-out region
    verts_left = []
    verts_right = []

    for i, pt in enumerate(centerline):
        if i == 0:
            tangent = (centerline[1] - centerline[0]).normalized()
        elif i == len(centerline) - 1:
            tangent = (centerline[-1] - centerline[-2]).normalized()
        else:
            tangent = (centerline[i+1] - centerline[i-1]).normalized()

        perp = Vector((-tangent.y, tangent.x, 0)).normalized()
        to_center = Vector((spiral_center.x - pt.x, spiral_center.y - pt.y, 0))

        # Apply banking only in the spiral core section
        bank = 0.0
        if lead_margin < i < len(centerline) - lead_margin:
            bank = 0.06

        inner_side = 1 if to_center.dot(perp) > 0 else -1
        left = pt + perp * half_w
        right = pt - perp * half_w

        if inner_side > 0:
            left.z = pt.z + bank
            right.z = pt.z
        else:
            left.z = pt.z
            right.z = pt.z + bank

        vl = bm.verts.new(left)
        vr = bm.verts.new(right)
        verts_left.append(vl)
        verts_right.append(vr)

    bm.verts.ensure_lookup_table()
    for i in range(len(centerline) - 1):
        try:
            bm.faces.new([verts_left[i], verts_right[i],
                          verts_right[i+1], verts_left[i+1]])
        except ValueError:
            pass

    uv_layer = bm.loops.layers.uv.new("UVMap")
    bm.faces.ensure_lookup_table()
    for face in bm.faces:
        for loop in face.loops:
            co = loop.vert.co
            loop[uv_layer].uv = (co.x * 2.0, co.y * 2.0)

    bm.to_mesh(fairway.data)
    bm.free()
    fairway.data.update()


def _build_rock_mound(spiral_center, start_z, end_z):
    """Build the central irregular rock mound inside the spiral."""
    rock = create_mesh_object("H4_RockMound", "H4_Obstacles", "NaturalStone")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.4)

    random.seed(42)
    for v in bm.verts:
        v.co.x *= 1.2
        v.co.y *= 1.2
        v.co.z *= 0.7
        d = random.uniform(-0.06, 0.06)
        v.co.x += d
        v.co.y += d * 0.8
        v.co.z += d * 0.5
        if v.co.z < -0.15:
            v.co.z = -0.15

    bm.to_mesh(rock.data)
    bm.free()
    rock_z = (start_z + end_z) / 2.0
    rock.location = Vector((spiral_center.x, spiral_center.y, rock_z + 0.2))
    rock.data.update()


def _build_accent_rocks(spiral_center, start_z, end_z):
    """Scatter small accent rocks around the central mound."""
    random.seed(99)
    mid_z = lerp(start_z, end_z, 0.5)
    for idx in range(5):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0.5, 0.8)
        rx = spiral_center.x + dist * math.cos(angle)
        ry = spiral_center.y + dist * math.sin(angle)

        name = f"H4_AccentRock_{idx+1}"
        accent = create_mesh_object(name, "H4_Decorations", "NaturalStone")
        bm = bmesh.new()
        r = random.uniform(0.06, 0.12)
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
        for v in bm.verts:
            v.co.z *= 0.5
            v.co.x += random.uniform(-0.02, 0.02)
            v.co.y += random.uniform(-0.02, 0.02)
        bm.to_mesh(accent.data)
        bm.free()
        accent.location = Vector((rx, ry, mid_z + 0.05))
        accent.data.update()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  MINI GOLF COURSE: Building Holes 2, 3, and 4")
    print("=" * 60)

    print("\n[Setup] Ensuring materials...")
    ensure_materials()

    for n in (2, 3, 4):
        ensure_collection(f"Hole_{n}")

    print()
    build_hole_2()
    print()
    build_hole_3()
    print()
    build_hole_4()

    bpy.context.view_layer.update()

    print("\n" + "=" * 60)
    print("  BUILD COMPLETE: Holes 2, 3, and 4 are ready.")
    print("=" * 60)

    for n in (2, 3, 4):
        objs = [o.name for o in bpy.data.objects if o.name.startswith(f"H{n}_")]
        print(f"  Hole {n} objects ({len(objs)}): {', '.join(objs)}")


if __name__ == "__main__":
    main()
else:
    main()
