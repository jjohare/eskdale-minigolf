"""
Shared utility functions for building mini golf hole geometry in Blender.

Provides helpers for:
- Material management
- Collection management
- Mesh creation (fairways, borders, greens, cups, flags)
- Curve interpolation (Catmull-Rom)
- Path-based mesh generation with banking support
"""

import bpy
import bmesh
import math
from mathutils import Vector


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def lerp(a, b, t):
    """Linear interpolation between two scalar values."""
    return a + (b - a) * t


def lerp_vec(a, b, t):
    """Linear interpolation between two Vector instances."""
    return Vector((lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)))


def catmull_rom(p0, p1, p2, p3, t, alpha=0.5):
    """Catmull-Rom spline interpolation for a single component."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1) +
        (-p0 + p2) * t +
        (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 +
        (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def catmull_rom_chain(points, segments_per_span=12):
    """Generate a smooth curve through control points using Catmull-Rom splines.

    Args:
        points: List of Vector control points.
        segments_per_span: Number of interpolated points between each pair.

    Returns:
        List of Vector points forming the smooth curve.
    """
    if len(points) < 2:
        return list(points)
    result = []
    pts = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(pts) - 2):
        for s in range(segments_per_span):
            t = s / segments_per_span
            px = catmull_rom(pts[i-1][0], pts[i][0], pts[i+1][0], pts[i+2][0], t)
            py = catmull_rom(pts[i-1][1], pts[i][1], pts[i+1][1], pts[i+2][1], t)
            pz = catmull_rom(pts[i-1][2], pts[i][2], pts[i+1][2], pts[i+2][2], t)
            result.append(Vector((px, py, pz)))
    result.append(Vector(pts[-2]))
    return result


# ---------------------------------------------------------------------------
# Material helpers
# ---------------------------------------------------------------------------

def get_or_create_material(name, base_color=None, metallic=0.0, roughness=0.5):
    """Return an existing material by name, or create a simple Principled BSDF."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf and base_color:
        bsdf.inputs["Base Color"].default_value = base_color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def ensure_materials():
    """Ensure all required materials exist with sensible fallback values."""
    materials = {
        "ArtificialTurf": ((0.15, 0.45, 0.08, 1.0), 0.0, 0.85),
        "PuttingGreen": ((0.1, 0.35, 0.06, 1.0), 0.0, 0.8),
        "StoneBorder": ((0.45, 0.42, 0.38, 1.0), 0.0, 0.9),
        "NaturalStone": ((0.5, 0.48, 0.43, 1.0), 0.0, 0.85),
        "WoodRail": ((0.55, 0.35, 0.15, 1.0), 0.0, 0.7),
        "WoodDark": ((0.3, 0.18, 0.08, 1.0), 0.0, 0.75),
        "Water": ((0.1, 0.3, 0.5, 0.8), 0.0, 0.1),
        "DirtSoil": ((0.35, 0.25, 0.15, 1.0), 0.0, 0.95),
        "PathwayConcrete": ((0.6, 0.58, 0.55, 1.0), 0.0, 0.9),
        "CupBlack": ((0.02, 0.02, 0.02, 1.0), 0.0, 0.95),
        "MetalPin": ((0.7, 0.7, 0.7, 1.0), 1.0, 0.3),
        "RedPaint": ((0.8, 0.05, 0.05, 1.0), 0.0, 0.5),
        "GullyDirt": ((0.25, 0.18, 0.1, 1.0), 0.0, 0.95),
    }
    for mat_name, (color, metal, rough) in materials.items():
        get_or_create_material(mat_name, base_color=color, metallic=metal, roughness=rough)


# ---------------------------------------------------------------------------
# Collection helpers
# ---------------------------------------------------------------------------

def ensure_collection(name, parent_name=None):
    """Get or create a collection, optionally under a parent."""
    col = bpy.data.collections.get(name)
    if col is not None:
        return col
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


def link_to_collection(obj, collection_name):
    """Link an object to a named collection, removing from all others."""
    col = bpy.data.collections.get(collection_name)
    if col is None:
        col = ensure_collection(collection_name)
    if obj.name not in col.objects:
        col.objects.link(obj)
    if obj.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(obj)
    for c in bpy.data.collections:
        if c != col and obj.name in c.objects:
            c.objects.unlink(obj)


# ---------------------------------------------------------------------------
# Object helpers
# ---------------------------------------------------------------------------

def remove_existing(name):
    """Remove an existing object and its orphaned mesh data."""
    obj = bpy.data.objects.get(name)
    if obj:
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def create_mesh_object(name, collection_name, material_name=None):
    """Create a new empty mesh object, link to collection, assign material."""
    remove_existing(name)
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    link_to_collection(obj, collection_name)
    if material_name:
        mat = bpy.data.materials.get(material_name)
        if mat:
            obj.data.materials.append(mat)
    return obj


# ---------------------------------------------------------------------------
# Geometry builders
# ---------------------------------------------------------------------------

def build_path_mesh(obj, centerline, width, uv=True):
    """Build a fairway/path ribbon mesh from a centerline with given width.

    Creates a strip of quads along the centerline, offset perpendicular
    by width/2 on each side.
    """
    bm = bmesh.new()
    half_w = width / 2.0
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
        left = pt + perp * half_w
        right = pt - perp * half_w
        left.z = pt.z
        right.z = pt.z

        vl = bm.verts.new(left)
        vr = bm.verts.new(right)
        verts_left.append(vl)
        verts_right.append(vr)

    bm.verts.ensure_lookup_table()

    for i in range(len(centerline) - 1):
        try:
            bm.faces.new([
                verts_left[i], verts_right[i],
                verts_right[i+1], verts_left[i+1]
            ])
        except ValueError:
            pass

    if uv:
        uv_layer = bm.loops.layers.uv.new("UVMap")
        bm.faces.ensure_lookup_table()
        for face in bm.faces:
            for loop in face.loops:
                co = loop.vert.co
                loop[uv_layer].uv = (co.x * 2.0, co.y * 2.0)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def build_border_rail(obj, centerline, width, height=0.1, thickness=0.05, side='both'):
    """Build border rails along a centerline path.

    Creates thin raised box extrusions along left and/or right edges.
    """
    bm = bmesh.new()
    half_w = width / 2.0
    ht = thickness / 2.0

    sides = []
    if side in ('both', 'left'):
        sides.append(1)
    if side in ('both', 'right'):
        sides.append(-1)

    for sign in sides:
        prev_verts = None
        for i, pt in enumerate(centerline):
            if i == 0:
                tangent = (centerline[1] - centerline[0]).normalized()
            elif i == len(centerline) - 1:
                tangent = (centerline[-1] - centerline[-2]).normalized()
            else:
                tangent = (centerline[i+1] - centerline[i-1]).normalized()

            perp = Vector((-tangent.y, tangent.x, 0)).normalized()
            base = pt + perp * sign * half_w

            inner = base - perp * sign * ht
            outer = base + perp * sign * ht

            v0 = bm.verts.new(Vector((inner.x, inner.y, pt.z)))
            v1 = bm.verts.new(Vector((outer.x, outer.y, pt.z)))
            v2 = bm.verts.new(Vector((outer.x, outer.y, pt.z + height)))
            v3 = bm.verts.new(Vector((inner.x, inner.y, pt.z + height)))

            curr_verts = (v0, v1, v2, v3)

            if prev_verts is not None:
                pv = prev_verts
                cv = curr_verts
                try:
                    bm.faces.new([pv[1], cv[1], cv[2], pv[2]])
                except ValueError:
                    pass
                try:
                    bm.faces.new([cv[0], pv[0], pv[3], cv[3]])
                except ValueError:
                    pass
                try:
                    bm.faces.new([pv[3], pv[2], cv[2], cv[3]])
                except ValueError:
                    pass
                try:
                    bm.faces.new([pv[0], cv[0], cv[1], pv[1]])
                except ValueError:
                    pass

            prev_verts = curr_verts

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def build_cup(name, position, collection_name, depth=0.1):
    """Build a cup cylinder (108mm diameter) at the given position."""
    obj = create_mesh_object(name, collection_name, "CupBlack")
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=24,
        radius1=0.054,
        radius2=0.054,
        depth=depth,
    )
    bm.to_mesh(obj.data)
    bm.free()
    obj.location = Vector((position.x, position.y, position.z - depth / 2))
    obj.data.update()
    return obj


def build_flag(name_prefix, position, collection_name, flag_height=0.4):
    """Build a flag pin (thin cylinder) and triangular flag at the given position."""
    pin_name = name_prefix + "_Pin"
    pin = create_mesh_object(pin_name, collection_name, "MetalPin")
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=8,
        radius1=0.004,
        radius2=0.004,
        depth=flag_height,
    )
    bm.to_mesh(pin.data)
    bm.free()
    pin.location = Vector((position.x, position.y, position.z + flag_height / 2))
    pin.data.update()

    flag_name = name_prefix + "_Flag"
    flag = create_mesh_object(flag_name, collection_name, "RedPaint")
    bm = bmesh.new()
    v0 = bm.verts.new(Vector((0, 0, 0)))
    v1 = bm.verts.new(Vector((0.08, 0, -0.02)))
    v2 = bm.verts.new(Vector((0.08, 0, -0.06)))
    v3 = bm.verts.new(Vector((0, 0, -0.08)))
    bm.faces.new([v0, v1, v2, v3])
    bm.to_mesh(flag.data)
    bm.free()
    flag.location = Vector((position.x, position.y, position.z + flag_height - 0.02))
    flag.data.update()

    return pin, flag


def build_green_surface(name, center, radius, z, collection_name, segments=24):
    """Build an elliptical green surface mesh with PuttingGreen material."""
    obj = create_mesh_object(name, collection_name, "PuttingGreen")
    bm = bmesh.new()

    center_v = bm.verts.new(Vector((center.x, center.y, z)))
    ring_verts = []
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        x = center.x + radius * 1.2 * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        v = bm.verts.new(Vector((x, y, z)))
        ring_verts.append(v)

    for i in range(segments):
        next_i = (i + 1) % segments
        try:
            bm.faces.new([center_v, ring_verts[i], ring_verts[next_i]])
        except ValueError:
            pass

    uv_layer = bm.loops.layers.uv.new("UVMap")
    bm.faces.ensure_lookup_table()
    for face in bm.faces:
        for loop in face.loops:
            co = loop.vert.co
            loop[uv_layer].uv = (co.x * 3.0, co.y * 3.0)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def build_tee_marker(name, position, collection_name):
    """Build a small rectangular tee marker at the given position."""
    obj = create_mesh_object(name, collection_name, "PathwayConcrete")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.15
        v.co.y *= 0.2
        v.co.z *= 0.01
    bm.to_mesh(obj.data)
    bm.free()
    obj.location = Vector((position.x, position.y, position.z + 0.005))
    obj.data.update()
    return obj
