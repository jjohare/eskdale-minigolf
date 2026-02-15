"""
Build Holes 6-9 of the mini golf course in Blender.

Hole 6: "The Tunnel" (Par 3) - Ball through a stone tunnel in an artificial hill
Hole 7: "The Stepping Stones" (Par 3) - Stepping stone platforms over a decorative pond
Hole 8: "The Ravine" (Par 3) - Ramp launch across a ravine gap
Hole 9: "The Grand Finale" (Par 3) - Gauntlet of spinning pinwheel obstacles

Requires existing collections (Hole_6..Hole_9 with sub-collections) and materials
(ArtificialTurf, PuttingGreen, StoneBorder, NaturalStone, WoodRail, WoodDark,
Water, TransparentTube, DirtSoil, MetalPin, RedPaint, CupBlack, WindmillBlade).

Coordinates: 1 BU = 1 meter, Z-axis up, Z=0 at top (Hole 1 tee).
Elevation descends: Hole 6 starts Z=-1.6, Hole 9 finishes Z=-2.7.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CUP_DIAMETER = 0.108
CUP_RADIUS = CUP_DIAMETER / 2.0
CUP_DEPTH = 0.10
FLAG_PIN_HEIGHT = 0.30
FLAG_PIN_RADIUS = 0.003
FLAG_WIDTH = 0.06
FLAG_HEIGHT = 0.04
BORDER_HEIGHT = 0.10
BORDER_THICKNESS = 0.05
FAIRWAY_WIDTH = 1.2
FPS = 30

# ---------------------------------------------------------------------------
# Material helpers
# ---------------------------------------------------------------------------

_material_cache = {}


def get_material(name):
    """Retrieve a material by name, falling back to a flat-color placeholder."""
    if name in _material_cache:
        return _material_cache[name]
    mat = bpy.data.materials.get(name)
    if mat is None:
        print(f"  [WARN] Material '{name}' not found, creating placeholder")
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    _material_cache[name] = mat
    return mat


# ---------------------------------------------------------------------------
# Collection helpers
# ---------------------------------------------------------------------------


def get_or_create_collection(name, parent_name=None):
    """Return an existing collection or create one under the given parent."""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        if parent_name:
            parent = bpy.data.collections.get(parent_name)
            if parent:
                parent.children.link(col)
            else:
                bpy.context.scene.collection.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col


def link_to_collection(obj, collection_name, parent_collection_name=None):
    """Link *obj* into *collection_name*, creating the collection if needed."""
    col = get_or_create_collection(collection_name, parent_collection_name)
    if obj.name not in col.objects:
        col.objects.link(obj)
    # Remove from scene root collection if present
    scene_col = bpy.context.scene.collection
    if obj.name in scene_col.objects:
        scene_col.objects.unlink(obj)


def safe_name(prefix, suffix):
    """Build an object name and check for duplicates."""
    name = f"{prefix}_{suffix}"
    if bpy.data.objects.get(name):
        print(f"  [SKIP] Object '{name}' already exists")
        return None
    return name


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------


def create_plane(name, size_x, size_y, location, material_name, collection_name,
                 parent_col=None, subdivisions=0):
    """Create a flat rectangular plane mesh."""
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return bpy.data.objects[name]
    bm = bmesh.new()
    hx, hy = size_x / 2.0, size_y / 2.0
    verts = [
        bm.verts.new((-hx, -hy, 0)),
        bm.verts.new((hx, -hy, 0)),
        bm.verts.new((hx, hy, 0)),
        bm.verts.new((-hx, hy, 0)),
    ]
    face = bm.faces.new(verts)
    if subdivisions > 0:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdivisions)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.data.materials.append(get_material(material_name))
    link_to_collection(obj, collection_name, parent_col)
    return obj


def create_sloped_fairway(name, width, length, start_loc, drop, direction,
                          material_name, collection_name, parent_col=None,
                          segments=10):
    """Create a rectangular fairway strip that slopes downward along *direction*.

    *direction* is a unit-length 2D vector (dx, dy) on the XY plane.
    *drop* is the total Z descent (positive value means going down).
    """
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return bpy.data.objects[name]

    bm = bmesh.new()
    dx, dy = direction
    # Perpendicular (left-hand normal on XY plane)
    px, py = -dy, dx
    half_w = width / 2.0
    seg_len = length / segments

    rows = []
    for i in range(segments + 1):
        t = i / segments
        cx = start_loc[0] + dx * seg_len * i
        cy = start_loc[1] + dy * seg_len * i
        cz = start_loc[2] - drop * t
        left = bm.verts.new((cx + px * half_w, cy + py * half_w, cz))
        right = bm.verts.new((cx - px * half_w, cy - py * half_w, cz))
        rows.append((left, right))

    for i in range(len(rows) - 1):
        l0, r0 = rows[i]
        l1, r1 = rows[i + 1]
        bm.faces.new([l0, l1, r1, r0])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(get_material(material_name))
    link_to_collection(obj, collection_name, parent_col)
    return obj


def create_cylinder(name, radius, depth, location, material_name,
                    collection_name, parent_col=None, segments=32):
    """Create a cylinder (Z-axis aligned) at *location*."""
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return bpy.data.objects[name]
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, vertices=segments
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(get_material(material_name))
    # Unlink from current collections and relink
    for col in obj.users_collection:
        col.objects.unlink(obj)
    link_to_collection(obj, collection_name, parent_col)
    return obj


def create_uv_sphere(name, radius, location, material_name,
                     collection_name, parent_col=None, segments=32, rings=16):
    """Create a UV sphere at *location*."""
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return bpy.data.objects[name]
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=location, segments=segments, ring_count=rings
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(get_material(material_name))
    for col in obj.users_collection:
        col.objects.unlink(obj)
    link_to_collection(obj, collection_name, parent_col)
    return obj


def create_cone(name, radius1, radius2, depth, location, material_name,
                collection_name, parent_col=None, segments=32):
    """Create a cone/truncated cone at *location*."""
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return bpy.data.objects[name]
    bpy.ops.mesh.primitive_cone_add(
        radius1=radius1, radius2=radius2, depth=depth,
        location=location, vertices=segments
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(get_material(material_name))
    for col in obj.users_collection:
        col.objects.unlink(obj)
    link_to_collection(obj, collection_name, parent_col)
    return obj


def create_torus(name, major_radius, minor_radius, location, material_name,
                 collection_name, parent_col=None):
    """Create a torus at *location*."""
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return bpy.data.objects[name]
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius, minor_radius=minor_radius,
        location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(get_material(material_name))
    for col in obj.users_collection:
        col.objects.unlink(obj)
    link_to_collection(obj, collection_name, parent_col)
    return obj


def create_empty(name, location, collection_name, parent_col=None,
                 display_type='PLAIN_AXES', display_size=0.1):
    """Create an Empty object for parenting / rotation pivots."""
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return bpy.data.objects[name]
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = display_type
    empty.empty_display_size = display_size
    empty.location = location
    link_to_collection(empty, collection_name, parent_col)
    return empty


# ---------------------------------------------------------------------------
# Compound constructions
# ---------------------------------------------------------------------------


def build_cup_and_flag(hole_prefix, cup_location, collection_fw, parent_col):
    """Build the cup recess, flag pin, and triangular flag at *cup_location*."""
    # Cup
    cup_name = f"{hole_prefix}_Cup"
    create_cylinder(
        cup_name, CUP_RADIUS, CUP_DEPTH,
        (cup_location[0], cup_location[1], cup_location[2] - CUP_DEPTH / 2.0),
        "CupBlack", collection_fw, parent_col
    )
    # Flag pin
    pin_name = f"{hole_prefix}_FlagPin"
    create_cylinder(
        pin_name, FLAG_PIN_RADIUS, FLAG_PIN_HEIGHT,
        (cup_location[0], cup_location[1],
         cup_location[2] + FLAG_PIN_HEIGHT / 2.0),
        "MetalPin", collection_fw, parent_col
    )
    # Flag (small triangular plane)
    flag_name = f"{hole_prefix}_Flag"
    if not bpy.data.objects.get(flag_name):
        bm = bmesh.new()
        v0 = bm.verts.new((0, 0, 0))
        v1 = bm.verts.new((FLAG_WIDTH, 0, 0))
        v2 = bm.verts.new((0, 0, -FLAG_HEIGHT))
        bm.faces.new([v0, v1, v2])
        mesh = bpy.data.meshes.new(flag_name)
        bm.to_mesh(mesh)
        bm.free()
        flag_obj = bpy.data.objects.new(flag_name, mesh)
        flag_obj.location = (
            cup_location[0] + FLAG_PIN_RADIUS,
            cup_location[1],
            cup_location[2] + FLAG_PIN_HEIGHT,
        )
        flag_obj.data.materials.append(get_material("RedPaint"))
        link_to_collection(flag_obj, collection_fw, parent_col)


def build_border_pair(hole_prefix, start, end, width, z_start, z_end,
                      collection_name, parent_col, segments=10):
    """Build left and right border rails along a straight path from *start* to *end*."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.001:
        return
    ndx, ndy = dx / length, dy / length
    # Perpendicular
    px, py = -ndy, ndx
    half_w = width / 2.0

    for side, sign, label in [("L", 1, "Border_L"), ("R", -1, "Border_R")]:
        name = f"{hole_prefix}_{label}"
        if bpy.data.objects.get(name):
            print(f"  [SKIP] '{name}' exists")
            continue
        bm = bmesh.new()
        seg_len = length / segments
        rows = []
        for i in range(segments + 1):
            t = i / segments
            cx = start[0] + ndx * seg_len * i + sign * px * half_w
            cy = start[1] + ndy * seg_len * i + sign * py * half_w
            cz_base = z_start + (z_end - z_start) * t
            inner = bm.verts.new((cx, cy, cz_base))
            outer = bm.verts.new((cx + sign * px * BORDER_THICKNESS,
                                  cy + sign * py * BORDER_THICKNESS, cz_base))
            inner_top = bm.verts.new((cx, cy, cz_base + BORDER_HEIGHT))
            outer_top = bm.verts.new((cx + sign * px * BORDER_THICKNESS,
                                      cy + sign * py * BORDER_THICKNESS,
                                      cz_base + BORDER_HEIGHT))
            rows.append((inner, outer, inner_top, outer_top))

        for i in range(len(rows) - 1):
            ib, ob, it, ot = rows[i]
            ib2, ob2, it2, ot2 = rows[i + 1]
            # Outer face
            bm.faces.new([ob, ob2, ot2, ot])
            # Inner face
            bm.faces.new([ib, it, it2, ib2])
            # Top face
            bm.faces.new([it, ot, ot2, it2])

        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(get_material("StoneBorder"))
        link_to_collection(obj, collection_name, parent_col)


def build_border_along_points(name, points_inner, width_outward, z_values,
                              material_name, collection_name, parent_col):
    """Build a border rail along a list of (x, y) points with per-point Z.

    *width_outward* is a (dx, dy) offset direction for the outer edge, applied
    uniformly.  For complex paths, pass pre-computed outer points instead.
    """
    if bpy.data.objects.get(name):
        print(f"  [SKIP] '{name}' exists")
        return
    bm = bmesh.new()
    rows = []
    ox, oy = width_outward
    for idx, (ix, iy) in enumerate(points_inner):
        z = z_values[idx] if idx < len(z_values) else z_values[-1]
        inner_b = bm.verts.new((ix, iy, z))
        outer_b = bm.verts.new((ix + ox, iy + oy, z))
        inner_t = bm.verts.new((ix, iy, z + BORDER_HEIGHT))
        outer_t = bm.verts.new((ix + ox, iy + oy, z + BORDER_HEIGHT))
        rows.append((inner_b, outer_b, inner_t, outer_t))

    for i in range(len(rows) - 1):
        ib, ob, it, ot = rows[i]
        ib2, ob2, it2, ot2 = rows[i + 1]
        bm.faces.new([ob, ob2, ot2, ot])
        bm.faces.new([ib, it, it2, ib2])
        bm.faces.new([it, ot, ot2, it2])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(get_material(material_name))
    link_to_collection(obj, collection_name, parent_col)


# ---------------------------------------------------------------------------
# HOLE 6 - "The Tunnel"
# ---------------------------------------------------------------------------

def build_hole_6():
    """Hole 6: The Tunnel (Par 3).

    Ball enters a stone tunnel through an artificial hill.
    Inside: split path (left=longer/safer, right=shorter/riskier narrow gap).
    Both paths merge before the green.

    Start: ~(5, 13, -1.6)  End/Green: ~(2, 13, -2.0)
    Direction: west (decreasing X), length 5.5m, drop 0.4m.
    """
    print("\n=== Building Hole 6: The Tunnel ===")

    H = "Hole_06"
    FW = "H6_Fairway"
    GR = "H6_Green"
    BD = "H6_Borders"
    OB = "H6_Obstacles"
    DC = "H6_Decorations"

    # Ensure sub-collections exist
    for sub in [FW, GR, BD, OB, DC]:
        get_or_create_collection(sub, "Hole_6")

    # -- Coordinates --
    tee_x, tee_y, tee_z = 5.0, 13.0, -1.6
    green_x, green_y, green_z = 2.0, 13.0, -2.0
    direction = (-1.0, 0.0)  # west
    total_length = 5.5
    drop = 0.4

    # ---- Approach fairway (tee to tunnel entrance) ----
    approach_len = 1.2
    print("  Building approach fairway...")
    create_sloped_fairway(
        f"{H}_Fairway_Approach", FAIRWAY_WIDTH, approach_len,
        (tee_x, tee_y, tee_z), drop * (approach_len / total_length),
        direction, "ArtificialTurf", FW, "Hole_6"
    )

    # ---- Tunnel Hill (dome over the tunnel area) ----
    tunnel_entrance_x = tee_x - approach_len  # 3.8
    hill_center_x = tunnel_entrance_x - 1.0   # 2.8
    hill_center_z = tee_z - drop * ((approach_len + 1.0) / total_length)

    print("  Building tunnel hill...")
    hill_name = f"{H}_TunnelHill"
    if not bpy.data.objects.get(hill_name):
        # Half-sphere hill mesh
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=1.2, location=(hill_center_x, tee_y, hill_center_z),
            segments=32, ring_count=16
        )
        hill = bpy.context.active_object
        hill.name = hill_name
        hill.data.name = hill_name
        # Delete bottom half (Z < hill center)
        bpy.ops.object.mode_set(mode='EDIT')
        bm_hill = bmesh.from_edit_mesh(hill.data)
        bm_hill.verts.ensure_lookup_table()
        verts_to_delete = [v for v in bm_hill.verts
                           if v.co.z < -0.05]
        bmesh.ops.delete(bm_hill, geom=verts_to_delete, context='VERTS')
        bmesh.update_edit_mesh(hill.data)
        bpy.ops.object.mode_set(mode='OBJECT')
        hill.data.materials.append(get_material("ArtificialTurf"))
        for col in hill.users_collection:
            col.objects.unlink(hill)
        link_to_collection(hill, OB, "Hole_6")

    # ---- Tunnel archway openings ----
    print("  Building tunnel arches...")
    arch_radius = 0.2
    arch_height = 0.25
    for side_label, ax in [("Entrance", tunnel_entrance_x),
                           ("Exit", tunnel_entrance_x - 2.0)]:
        arch_name = f"{H}_TunnelArch_{side_label}"
        if not bpy.data.objects.get(arch_name):
            arch_z = tee_z - drop * ((tee_x - ax) / total_length)
            # Arch: a half-cylinder opening indicator
            bpy.ops.mesh.primitive_cylinder_add(
                radius=arch_radius, depth=BORDER_THICKNESS,
                location=(ax, tee_y, arch_z + arch_height / 2.0),
                rotation=(0, math.pi / 2.0, 0), vertices=16
            )
            arch = bpy.context.active_object
            arch.name = arch_name
            arch.data.name = arch_name
            arch.data.materials.append(get_material("NaturalStone"))
            for col in arch.users_collection:
                col.objects.unlink(arch)
            link_to_collection(arch, OB, "Hole_6")

    # ---- Interior tunnel floor (split path) ----
    print("  Building split tunnel paths...")
    tunnel_start_x = tunnel_entrance_x
    tunnel_end_x = tunnel_entrance_x - 2.0
    tunnel_mid_x = (tunnel_start_x + tunnel_end_x) / 2.0

    # Left path (longer, curves up in Y then back) -- safer
    left_path_name = f"{H}_Tunnel_LeftPath"
    if not bpy.data.objects.get(left_path_name):
        bm = bmesh.new()
        path_w = 0.4
        # Points along the left (safer) path
        points = [
            (tunnel_start_x, tee_y + 0.1, 0),
            (tunnel_mid_x + 0.3, tee_y + 0.5, 0),
            (tunnel_mid_x, tee_y + 0.6, 0),
            (tunnel_mid_x - 0.3, tee_y + 0.5, 0),
            (tunnel_end_x, tee_y + 0.1, 0),
        ]
        z_start_tunnel = tee_z - drop * ((tee_x - tunnel_start_x) / total_length)
        z_end_tunnel = tee_z - drop * ((tee_x - tunnel_end_x) / total_length)
        rows = []
        for i, (px, py, _) in enumerate(points):
            t = i / (len(points) - 1)
            z = z_start_tunnel + (z_end_tunnel - z_start_tunnel) * t
            left_v = bm.verts.new((px, py + path_w / 2.0, z))
            right_v = bm.verts.new((px, py - path_w / 2.0, z))
            rows.append((left_v, right_v))
        for i in range(len(rows) - 1):
            l0, r0 = rows[i]
            l1, r1 = rows[i + 1]
            bm.faces.new([l0, l1, r1, r0])
        mesh = bpy.data.meshes.new(left_path_name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(left_path_name, mesh)
        obj.data.materials.append(get_material("NaturalStone"))
        link_to_collection(obj, FW, "Hole_6")

    # Right path (shorter, narrow gap) -- riskier
    right_path_name = f"{H}_Tunnel_RightPath"
    if not bpy.data.objects.get(right_path_name):
        bm = bmesh.new()
        path_w = 0.25  # narrower
        points = [
            (tunnel_start_x, tee_y - 0.1, 0),
            (tunnel_mid_x, tee_y - 0.2, 0),
            (tunnel_end_x, tee_y - 0.1, 0),
        ]
        z_start_tunnel = tee_z - drop * ((tee_x - tunnel_start_x) / total_length)
        z_end_tunnel = tee_z - drop * ((tee_x - tunnel_end_x) / total_length)
        rows = []
        for i, (px, py, _) in enumerate(points):
            t = i / (len(points) - 1)
            z = z_start_tunnel + (z_end_tunnel - z_start_tunnel) * t
            left_v = bm.verts.new((px, py + path_w / 2.0, z))
            right_v = bm.verts.new((px, py - path_w / 2.0, z))
            rows.append((left_v, right_v))
        for i in range(len(rows) - 1):
            l0, r0 = rows[i]
            l1, r1 = rows[i + 1]
            bm.faces.new([l0, l1, r1, r0])
        mesh = bpy.data.meshes.new(right_path_name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(right_path_name, mesh)
        obj.data.materials.append(get_material("NaturalStone"))
        link_to_collection(obj, FW, "Hole_6")

    # Narrow gap obstacle on right path
    gap_name = f"{H}_NarrowGap"
    gap_x = tunnel_mid_x
    gap_z = tee_z - drop * ((tee_x - tunnel_mid_x) / total_length)
    for side_i, y_off in enumerate([0.12, -0.12]):
        block_name = f"{gap_name}_{side_i}"
        create_cylinder(
            block_name, 0.06, 0.2,
            (gap_x, tee_y - 0.2 + y_off, gap_z + 0.1),
            "NaturalStone", OB, "Hole_6", segments=8
        )

    # ---- Merge fairway (tunnel exit to green) ----
    merge_start_x = tunnel_end_x
    merge_len = abs(merge_start_x - green_x)
    merge_z_start = tee_z - drop * ((tee_x - merge_start_x) / total_length)
    print("  Building merge fairway...")
    create_sloped_fairway(
        f"{H}_Fairway_Merge", FAIRWAY_WIDTH, merge_len,
        (merge_start_x, tee_y, merge_z_start),
        green_z - merge_z_start if green_z < merge_z_start else 0,
        direction, "ArtificialTurf", FW, "Hole_6"
    )

    # ---- Green ----
    print("  Building green...")
    green_size = 1.0
    create_plane(
        f"{H}_Green", green_size, green_size,
        (green_x, green_y, green_z),
        "PuttingGreen", GR, "Hole_6", subdivisions=2
    )

    # ---- Cup and flag ----
    print("  Building cup and flag...")
    build_cup_and_flag(H, (green_x, green_y, green_z), GR, "Hole_6")

    # ---- Borders ----
    print("  Building borders...")
    build_border_pair(
        H, (tee_x, tee_y), (green_x, green_y), FAIRWAY_WIDTH,
        tee_z, green_z, BD, "Hole_6"
    )

    print("  Hole 6 complete.")


# ---------------------------------------------------------------------------
# HOLE 7 - "The Stepping Stones"
# ---------------------------------------------------------------------------

def build_hole_7():
    """Hole 7: The Stepping Stones (Par 3).

    3 raised circular stone platforms over a decorative pond.
    Japanese garden feel with a small tree.

    Start: near H6 green ~(2, 13, -2.0)  End: ~(7, 13.5, -2.3)
    Direction: east (increasing X), length 5m, drop 0.3m.
    """
    print("\n=== Building Hole 7: The Stepping Stones ===")

    H = "Hole_07"
    FW = "H7_Fairway"
    GR = "H7_Green"
    BD = "H7_Borders"
    OB = "H7_Obstacles"
    DC = "H7_Decorations"

    for sub in [FW, GR, BD, OB, DC]:
        get_or_create_collection(sub, "Hole_7")

    tee_x, tee_y, tee_z = 2.0, 13.0, -2.0
    green_x, green_y, green_z = 7.0, 13.5, -2.3
    direction = (1.0, 0.0)
    total_length = 5.0
    drop = 0.3

    # ---- Approach fairway (tee to pond start) ----
    approach_len = 1.0
    print("  Building approach fairway...")
    create_sloped_fairway(
        f"{H}_Fairway_Approach", FAIRWAY_WIDTH, approach_len,
        (tee_x, tee_y, tee_z), drop * (approach_len / total_length),
        direction, "ArtificialTurf", FW, "Hole_7"
    )

    # ---- Decorative pond ----
    print("  Building pond...")
    pond_center_x = tee_x + 2.5
    pond_center_y = tee_y + 0.25
    pond_z = tee_z - drop * 0.5 - 0.05  # slightly below fairway level
    create_plane(
        f"{H}_Pond", 2.0, 1.5,
        (pond_center_x, pond_center_y, pond_z),
        "Water", OB, "Hole_7", subdivisions=3
    )

    # ---- Stepping stones (3 raised platforms) ----
    print("  Building stepping stones...")
    stone_radius = 0.25
    stone_height = 0.08
    stone_positions = [
        (tee_x + 1.5, tee_y + 0.1, tee_z - drop * 0.3),
        (tee_x + 2.5, tee_y + 0.3, tee_z - drop * 0.5),
        (tee_x + 3.5, tee_y + 0.2, tee_z - drop * 0.7),
    ]
    for i, (sx, sy, sz) in enumerate(stone_positions):
        stone_name = f"{H}_SteppingStone_{i}"
        create_cylinder(
            stone_name, stone_radius, stone_height,
            (sx, sy, sz + stone_height / 2.0),
            "NaturalStone", OB, "Hole_7"
        )

    # ---- Connecting ramps between stones ----
    print("  Building connecting ramps...")
    ramp_positions = [
        ((tee_x + approach_len, tee_y, tee_z - drop * (approach_len / total_length)),
         stone_positions[0]),
        (stone_positions[0], stone_positions[1]),
        (stone_positions[1], stone_positions[2]),
    ]
    for i, (start_pos, end_pos) in enumerate(ramp_positions):
        ramp_name = f"{H}_Ramp_{i}"
        if bpy.data.objects.get(ramp_name):
            continue
        bm = bmesh.new()
        ramp_w = 0.3  # narrow connecting ramp
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        rlen = math.sqrt(dx * dx + dy * dy)
        if rlen < 0.001:
            bm.free()
            continue
        ndx, ndy = dx / rlen, dy / rlen
        px, py = -ndy, ndx
        hw = ramp_w / 2.0
        segs = 4
        rows = []
        for s in range(segs + 1):
            t = s / segs
            cx = start_pos[0] + dx * t
            cy = start_pos[1] + dy * t
            cz = start_pos[2] + (end_pos[2] - start_pos[2]) * t
            lv = bm.verts.new((cx + px * hw, cy + py * hw, cz))
            rv = bm.verts.new((cx - px * hw, cy - py * hw, cz))
            rows.append((lv, rv))
        for s in range(len(rows) - 1):
            l0, r0 = rows[s]
            l1, r1 = rows[s + 1]
            bm.faces.new([l0, l1, r1, r0])
        mesh = bpy.data.meshes.new(ramp_name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(ramp_name, mesh)
        obj.data.materials.append(get_material("ArtificialTurf"))
        link_to_collection(obj, FW, "Hole_7")

    # ---- Exit fairway (last stone to green) ----
    last_stone = stone_positions[-1]
    exit_start = (last_stone[0], last_stone[1], last_stone[2])
    exit_len = green_x - last_stone[0]
    exit_dir_x = (green_x - last_stone[0])
    exit_dir_y = (green_y - last_stone[1])
    exit_length = math.sqrt(exit_dir_x**2 + exit_dir_y**2)
    if exit_length > 0.001:
        exit_dir_norm = (exit_dir_x / exit_length, exit_dir_y / exit_length)
    else:
        exit_dir_norm = (1.0, 0.0)
    exit_drop = green_z - last_stone[2]

    print("  Building exit fairway...")
    create_sloped_fairway(
        f"{H}_Fairway_Exit", FAIRWAY_WIDTH, exit_length,
        exit_start, abs(exit_drop) if exit_drop < 0 else 0,
        exit_dir_norm, "ArtificialTurf", FW, "Hole_7"
    )

    # ---- Japanese garden tree ----
    print("  Building decorative tree...")
    tree_x = pond_center_x + 0.5
    tree_y = pond_center_y + 0.9
    tree_z = tee_z - drop * 0.5

    # Trunk
    create_cylinder(
        f"{H}_TreeTrunk", 0.04, 0.5,
        (tree_x, tree_y, tree_z + 0.25),
        "WoodDark", DC, "Hole_7", segments=8
    )
    # Crown (sphere)
    create_uv_sphere(
        f"{H}_TreeCrown", 0.25,
        (tree_x, tree_y, tree_z + 0.6),
        "ArtificialTurf", DC, "Hole_7", segments=16, rings=12
    )

    # ---- Green ----
    print("  Building green...")
    green_size = 1.0
    create_plane(
        f"{H}_Green", green_size, green_size,
        (green_x, green_y, green_z),
        "PuttingGreen", GR, "Hole_7", subdivisions=2
    )

    # ---- Cup and flag ----
    print("  Building cup and flag...")
    build_cup_and_flag(H, (green_x, green_y, green_z), GR, "Hole_7")

    # ---- Borders (along the overall fairway envelope) ----
    print("  Building borders...")
    build_border_pair(
        H, (tee_x, tee_y), (green_x, green_y), FAIRWAY_WIDTH,
        tee_z, green_z, BD, "Hole_7"
    )

    print("  Hole 7 complete.")


# ---------------------------------------------------------------------------
# HOLE 8 - "The Ravine"
# ---------------------------------------------------------------------------

def build_hole_8():
    """Hole 8: The Ravine (Par 3).

    Ball launches off a ramp across a 0.5m ravine gap.
    Alternative winding path goes around.
    Ravine walls with rock faces, small stream at bottom.

    Start: near H7 green ~(7, 13.5, -2.3)  End: ~(2, 14.5, -2.7)
    Direction: west, length 6m, drop 0.4m.
    """
    print("\n=== Building Hole 8: The Ravine ===")

    H = "Hole_08"
    FW = "H8_Fairway"
    GR = "H8_Green"
    BD = "H8_Borders"
    OB = "H8_Obstacles"
    DC = "H8_Decorations"

    for sub in [FW, GR, BD, OB, DC]:
        get_or_create_collection(sub, "Hole_8")

    tee_x, tee_y, tee_z = 7.0, 13.5, -2.3
    green_x, green_y, green_z = 2.0, 14.5, -2.7
    total_length = 6.0
    drop = 0.4

    # Direction vector
    dir_x = green_x - tee_x
    dir_y = green_y - tee_y
    dir_len = math.sqrt(dir_x**2 + dir_y**2)
    direction = (dir_x / dir_len, dir_y / dir_len)

    # ---- Approach fairway (tee to ramp) ----
    approach_len = 1.8
    print("  Building approach fairway...")
    create_sloped_fairway(
        f"{H}_Fairway_Approach", FAIRWAY_WIDTH, approach_len,
        (tee_x, tee_y, tee_z), drop * (approach_len / total_length),
        direction, "ArtificialTurf", FW, "Hole_8"
    )

    # ---- Launch ramp ----
    ramp_start_x = tee_x + direction[0] * approach_len
    ramp_start_y = tee_y + direction[1] * approach_len
    ramp_z = tee_z - drop * (approach_len / total_length)
    ramp_len = 0.6
    ramp_rise = 0.08  # slight upward angle for launch

    print("  Building launch ramp...")
    ramp_name = f"{H}_LaunchRamp"
    if not bpy.data.objects.get(ramp_name):
        bm = bmesh.new()
        hw = FAIRWAY_WIDTH / 2.0
        px, py = -direction[1], direction[0]
        # Ramp goes slightly upward
        segs = 4
        rows = []
        for i in range(segs + 1):
            t = i / segs
            cx = ramp_start_x + direction[0] * ramp_len * t
            cy = ramp_start_y + direction[1] * ramp_len * t
            # Rise in the first 80%, then flatten for lip
            if t < 0.8:
                cz = ramp_z + ramp_rise * (t / 0.8)
            else:
                cz = ramp_z + ramp_rise
            lv = bm.verts.new((cx + px * hw * 0.5, cy + py * hw * 0.5, cz))
            rv = bm.verts.new((cx - px * hw * 0.5, cy - py * hw * 0.5, cz))
            rows.append((lv, rv))
        for i in range(len(rows) - 1):
            l0, r0 = rows[i]
            l1, r1 = rows[i + 1]
            bm.faces.new([l0, l1, r1, r0])
        mesh = bpy.data.meshes.new(ramp_name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(ramp_name, mesh)
        obj.data.materials.append(get_material("ArtificialTurf"))
        link_to_collection(obj, FW, "Hole_8")

    # ---- Ravine gap ----
    ravine_gap = 0.5
    ravine_x = ramp_start_x + direction[0] * (ramp_len + ravine_gap / 2.0)
    ravine_y = ramp_start_y + direction[1] * (ramp_len + ravine_gap / 2.0)
    ravine_z = ramp_z - 0.3  # ravine floor is lower

    # Stream at bottom of ravine
    print("  Building ravine stream...")
    create_plane(
        f"{H}_RavineStream", ravine_gap + 0.2, 1.0,
        (ravine_x, ravine_y, ravine_z),
        "Water", OB, "Hole_8"
    )

    # Catch net below the ramp lip
    print("  Building catch net...")
    net_name = f"{H}_CatchNet"
    if not bpy.data.objects.get(net_name):
        # Semi-transparent mesh plane angled below the gap
        net_z = ramp_z - 0.1
        create_plane(
            net_name, ravine_gap, FAIRWAY_WIDTH * 0.6,
            (ravine_x, ravine_y, net_z),
            "TransparentTube", OB, "Hole_8"
        )

    # ---- Ravine walls (rock faces) ----
    print("  Building ravine walls...")
    for wall_i, y_offset in enumerate([0.5, -0.5]):
        wall_name = f"{H}_RavineWall_{wall_i}"
        if bpy.data.objects.get(wall_name):
            continue
        bm = bmesh.new()
        # Irregular rock face: a vertical plane with displaced vertices
        wall_w = ravine_gap + 0.4
        wall_h = 0.4
        segs_x, segs_z = 6, 4
        import random
        random.seed(42 + wall_i)
        grid_verts = []
        for iz in range(segs_z + 1):
            row = []
            for ix in range(segs_x + 1):
                tx = ix / segs_x
                tz = iz / segs_z
                x = ravine_x - wall_w / 2.0 + wall_w * tx
                y_base = ravine_y + y_offset
                z = ravine_z + wall_h * tz
                # Displace in Y for rock-face irregularity
                displacement = random.uniform(-0.03, 0.03)
                v = bm.verts.new((x, y_base + displacement, z))
                row.append(v)
            grid_verts.append(row)
        for iz in range(segs_z):
            for ix in range(segs_x):
                v00 = grid_verts[iz][ix]
                v10 = grid_verts[iz][ix + 1]
                v11 = grid_verts[iz + 1][ix + 1]
                v01 = grid_verts[iz + 1][ix]
                bm.faces.new([v00, v10, v11, v01])
        mesh = bpy.data.meshes.new(wall_name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(wall_name, mesh)
        obj.data.materials.append(get_material("NaturalStone"))
        link_to_collection(obj, OB, "Hole_8")

    # ---- Landing pad (after ravine) ----
    landing_x = ramp_start_x + direction[0] * (ramp_len + ravine_gap)
    landing_y = ramp_start_y + direction[1] * (ramp_len + ravine_gap)
    landing_z = ramp_z - drop * (ravine_gap / total_length)
    landing_len = 1.0

    print("  Building landing fairway...")
    create_sloped_fairway(
        f"{H}_Fairway_Landing", FAIRWAY_WIDTH, landing_len,
        (landing_x, landing_y, landing_z),
        drop * (landing_len / total_length),
        direction, "ArtificialTurf", FW, "Hole_8"
    )

    # ---- Alternative winding path (around the ravine) ----
    print("  Building alternative path...")
    alt_name = f"{H}_AltPath"
    if not bpy.data.objects.get(alt_name):
        bm = bmesh.new()
        path_w = 0.4
        # Path curves south around the ravine
        alt_points = [
            (ramp_start_x, ramp_start_y, ramp_z),
            (ramp_start_x + direction[0] * 0.2,
             ramp_start_y - 0.6, ramp_z - 0.02),
            (ravine_x, ravine_y - 0.8, ravine_z + 0.25),
            (landing_x - direction[0] * 0.2,
             landing_y - 0.6, landing_z + 0.02),
            (landing_x, landing_y, landing_z),
        ]
        rows = []
        for i, (ax, ay, az) in enumerate(alt_points):
            # Simple perpendicular based on neighbors
            if i == 0:
                seg_dx = alt_points[1][0] - ax
                seg_dy = alt_points[1][1] - ay
            elif i == len(alt_points) - 1:
                seg_dx = ax - alt_points[i - 1][0]
                seg_dy = ay - alt_points[i - 1][1]
            else:
                seg_dx = alt_points[i + 1][0] - alt_points[i - 1][0]
                seg_dy = alt_points[i + 1][1] - alt_points[i - 1][1]
            seg_len = math.sqrt(seg_dx**2 + seg_dy**2)
            if seg_len < 0.001:
                seg_len = 1.0
            pxn, pyn = -seg_dy / seg_len, seg_dx / seg_len
            hw = path_w / 2.0
            lv = bm.verts.new((ax + pxn * hw, ay + pyn * hw, az))
            rv = bm.verts.new((ax - pxn * hw, ay - pyn * hw, az))
            rows.append((lv, rv))
        for i in range(len(rows) - 1):
            l0, r0 = rows[i]
            l1, r1 = rows[i + 1]
            bm.faces.new([l0, l1, r1, r0])
        mesh = bpy.data.meshes.new(alt_name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(alt_name, mesh)
        obj.data.materials.append(get_material("ArtificialTurf"))
        link_to_collection(obj, FW, "Hole_8")

    # ---- Final fairway to green ----
    final_start_x = landing_x + direction[0] * landing_len
    final_start_y = landing_y + direction[1] * landing_len
    final_start_z = landing_z - drop * (landing_len / total_length)
    remaining = math.sqrt((green_x - final_start_x)**2 +
                          (green_y - final_start_y)**2)
    final_dir_x = (green_x - final_start_x)
    final_dir_y = (green_y - final_start_y)
    if remaining > 0.001:
        final_direction = (final_dir_x / remaining, final_dir_y / remaining)
    else:
        final_direction = direction
    final_drop = abs(green_z - final_start_z)

    print("  Building final fairway...")
    create_sloped_fairway(
        f"{H}_Fairway_Final", FAIRWAY_WIDTH, remaining,
        (final_start_x, final_start_y, final_start_z),
        final_drop, final_direction, "ArtificialTurf", FW, "Hole_8"
    )

    # ---- Green ----
    print("  Building green...")
    green_size = 1.0
    create_plane(
        f"{H}_Green", green_size, green_size,
        (green_x, green_y, green_z),
        "PuttingGreen", GR, "Hole_8", subdivisions=2
    )

    # ---- Cup and flag ----
    print("  Building cup and flag...")
    build_cup_and_flag(H, (green_x, green_y, green_z), GR, "Hole_8")

    # ---- Borders ----
    print("  Building borders...")
    build_border_pair(
        H, (tee_x, tee_y), (green_x, green_y), FAIRWAY_WIDTH,
        tee_z, green_z, BD, "Hole_8"
    )

    print("  Hole 8 complete.")


# ---------------------------------------------------------------------------
# HOLE 9 - "The Grand Finale"
# ---------------------------------------------------------------------------

def build_spinner(name, location, blade_count, blade_length, blade_width,
                  blade_height, post_height, post_radius,
                  collection_name, parent_col, spin_index=0):
    """Build a single pinwheel spinner with rotation driver.

    Returns the empty pivot so the caller can adjust the driver if needed.
    """
    post_name = f"{name}_Post"
    pivot_name = f"{name}_Pivot"
    blade_group_name = f"{name}_Blades"

    px, py, pz = location

    # Post
    create_cylinder(
        post_name, post_radius, post_height,
        (px, py, pz + post_height / 2.0),
        "MetalPin", collection_name, parent_col
    )

    # Pivot empty at top of post
    pivot = create_empty(
        pivot_name,
        (px, py, pz + post_height),
        collection_name, parent_col,
        display_type='PLAIN_AXES', display_size=0.05
    )

    # Build 4 blades as a single mesh, parented to the pivot
    if not bpy.data.objects.get(blade_group_name):
        bm = bmesh.new()
        for b in range(blade_count):
            angle = b * (2.0 * math.pi / blade_count)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            # Each blade: a small flat rectangle extending radially outward
            # Blade lies in the XY plane relative to pivot
            hw = blade_width / 2.0
            hh = blade_height / 2.0
            # Rectangle corners in local pivot space (radial direction)
            # Inner edge at ~0.02m from center, outer edge at blade_length
            inner_r = 0.02
            outer_r = blade_length

            # Four corners of the blade rectangle (in the plane perpendicular
            # to the post axis, i.e. the XY plane since post is along Z)
            # The blade extends radially: along (cos_a, sin_a) direction
            # Width is perpendicular to radial in XY: (-sin_a, cos_a)
            perp_x, perp_y = -sin_a, cos_a
            v0 = bm.verts.new((
                cos_a * inner_r + perp_x * hw,
                sin_a * inner_r + perp_y * hw,
                -hh
            ))
            v1 = bm.verts.new((
                cos_a * outer_r + perp_x * hw,
                sin_a * outer_r + perp_y * hw,
                -hh
            ))
            v2 = bm.verts.new((
                cos_a * outer_r - perp_x * hw,
                sin_a * outer_r - perp_y * hw,
                hh
            ))
            v3 = bm.verts.new((
                cos_a * inner_r - perp_x * hw,
                sin_a * inner_r - perp_y * hw,
                hh
            ))
            bm.faces.new([v0, v1, v2, v3])

        mesh = bpy.data.meshes.new(blade_group_name)
        bm.to_mesh(mesh)
        bm.free()
        blade_obj = bpy.data.objects.new(blade_group_name, mesh)
        blade_obj.location = (px, py, pz + post_height)
        blade_obj.data.materials.append(get_material("WindmillBlade"))
        link_to_collection(blade_obj, collection_name, parent_col)
        # Parent blades to pivot
        blade_obj.parent = pivot

    # ---- Rotation driver on pivot ----
    pivot_obj = bpy.data.objects.get(pivot_name)
    if pivot_obj is not None:
        # Clear existing drivers
        pivot_obj.animation_data_create()
        # Driver on Z rotation
        driver = pivot_obj.driver_add("rotation_euler", 2).driver
        driver.type = 'SCRIPTED'
        var = driver.variables.new()
        var.name = "frame"
        var.type = 'SINGLE_PROP'
        target = var.targets[0]
        target.id_type = 'SCENE'
        target.id = bpy.context.scene
        target.data_path = "frame_current"

        # One revolution per 2 seconds at 30fps = 60 frames per revolution
        # angular_velocity = 2*pi / 60 radians per frame
        # Alternate direction for odd-numbered spinners
        if spin_index % 2 == 0:
            driver.expression = f"frame * (2 * 3.14159 / ({FPS} * 2))"
        else:
            driver.expression = f"-frame * (2 * 3.14159 / ({FPS} * 2))"

    return pivot


def build_hole_9():
    """Hole 9: The Grand Finale (Par 3).

    Straight shot through gauntlet of 4 spinning pinwheel obstacles.
    Slightly raised final green. Bell/gong decoration.

    Start: near H8 green ~(2, 14.5, -2.7)  End: ~(7, 14.5, -2.7)
    Direction: east, length 6m, flat (drop 0.0m).
    """
    print("\n=== Building Hole 9: The Grand Finale ===")

    H = "Hole_09"
    FW = "H9_Fairway"
    GR = "H9_Green"
    BD = "H9_Borders"
    OB = "H9_Obstacles"
    DC = "H9_Decorations"

    for sub in [FW, GR, BD, OB, DC]:
        get_or_create_collection(sub, "Hole_9")

    tee_x, tee_y, tee_z = 2.0, 14.5, -2.7
    green_x, green_y, green_z = 7.0, 14.5, -2.7
    direction = (1.0, 0.0)
    total_length = 6.0

    # ---- Main fairway (full length, flat) ----
    print("  Building main fairway...")
    create_sloped_fairway(
        f"{H}_Fairway", FAIRWAY_WIDTH, total_length,
        (tee_x, tee_y, tee_z), 0.0,  # flat
        direction, "ArtificialTurf", FW, "Hole_9"
    )

    # ---- 4 Spinning pinwheel obstacles ----
    print("  Building spinners...")
    spinner_spacing = total_length / 5.0  # 4 spinners evenly spaced
    spinner_blade_length = 0.18
    spinner_blade_width = 0.04
    spinner_blade_height = 0.005
    spinner_post_height = 0.25
    spinner_post_radius = 0.012

    for i in range(4):
        t = (i + 1) / 5.0
        sx = tee_x + direction[0] * total_length * t
        sy = tee_y + direction[1] * total_length * t
        # Alternate sides: even spinners offset +Y, odd spinners offset -Y
        y_offset = 0.25 if i % 2 == 0 else -0.25
        sy += y_offset
        sz = tee_z

        spinner_name = f"{H}_Spinner_{i}"
        print(f"    Spinner {i} at ({sx:.2f}, {sy:.2f}, {sz:.2f})")
        build_spinner(
            spinner_name, (sx, sy, sz),
            blade_count=4,
            blade_length=spinner_blade_length,
            blade_width=spinner_blade_width,
            blade_height=spinner_blade_height,
            post_height=spinner_post_height,
            post_radius=spinner_post_radius,
            collection_name=OB,
            parent_col="Hole_9",
            spin_index=i
        )

    # ---- Raised green platform ----
    green_raise = 0.05
    print("  Building raised green platform...")
    green_size = 1.2

    # Platform base (slight step up)
    create_cylinder(
        f"{H}_GreenPlatform", green_size / 2.0, green_raise,
        (green_x, green_y, green_z + green_raise / 2.0),
        "StoneBorder", GR, "Hole_9", segments=32
    )

    # Green surface on top
    create_plane(
        f"{H}_Green", green_size, green_size,
        (green_x, green_y, green_z + green_raise),
        "PuttingGreen", GR, "Hole_9", subdivisions=2
    )

    # ---- Cup and flag ----
    cup_z = green_z + green_raise
    print("  Building cup and flag...")
    build_cup_and_flag(H, (green_x, green_y, cup_z), GR, "Hole_9")

    # ---- Bell / gong decoration ----
    print("  Building bell/gong decoration...")
    bell_x = green_x + 0.4
    bell_y = green_y
    bell_z = green_z + green_raise

    # Bell post
    create_cylinder(
        f"{H}_BellPost", 0.02, 0.5,
        (bell_x, bell_y, bell_z + 0.25),
        "MetalPin", DC, "Hole_9", segments=8
    )
    # Crossbar
    create_cylinder(
        f"{H}_BellCrossbar", 0.01, 0.2,
        (bell_x, bell_y, bell_z + 0.5),
        "MetalPin", DC, "Hole_9", segments=8
    )
    # Rotate crossbar to horizontal
    crossbar = bpy.data.objects.get(f"{H}_BellCrossbar")
    if crossbar:
        crossbar.rotation_euler = (0, math.pi / 2.0, 0)

    # Gong (torus)
    create_torus(
        f"{H}_Gong", 0.08, 0.015,
        (bell_x, bell_y, bell_z + 0.42),
        "RedPaint", DC, "Hole_9"
    )

    # ---- Colorful celebration posts along the fairway ----
    print("  Building celebration decorations...")
    celebration_colors = ["RedPaint", "WindmillBlade", "MetalPin", "RedPaint"]
    for i in range(4):
        t = (i + 1) / 5.0
        cx = tee_x + direction[0] * total_length * t
        cy = tee_y
        # Opposite side from spinners
        y_offset = -0.5 if i % 2 == 0 else 0.5
        cy += y_offset
        post_name = f"{H}_CelebPost_{i}"
        create_cylinder(
            post_name, 0.02, 0.35,
            (cx, cy, tee_z + 0.175),
            celebration_colors[i], DC, "Hole_9", segments=8
        )
        # Small sphere on top
        sphere_name = f"{H}_CelebSphere_{i}"
        create_uv_sphere(
            sphere_name, 0.03,
            (cx, cy, tee_z + 0.38),
            celebration_colors[i], DC, "Hole_9", segments=8, rings=6
        )

    # ---- Borders ----
    print("  Building borders...")
    build_border_pair(
        H, (tee_x, tee_y), (green_x, green_y), FAIRWAY_WIDTH,
        tee_z, green_z, BD, "Hole_9"
    )

    print("  Hole 9 complete.")


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  MINI GOLF COURSE - Building Holes 6-9")
    print("=" * 60)

    # Ensure frame rate is set for spinner drivers
    bpy.context.scene.render.fps = FPS

    build_hole_6()
    build_hole_7()
    build_hole_8()
    build_hole_9()

    # Force driver update
    bpy.context.view_layer.update()

    print("\n" + "=" * 60)
    print("  All holes (6-9) built successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    # When executed via Blender's text editor or exec(), run main directly
    main()
