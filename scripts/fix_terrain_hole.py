"""Delete terrain faces in the golf footprint and replace with a ground plane.

Previous vertex-displacement cuts left terrain faces spanning between cut and uncut
vertices, still occluding golf objects. This script removes those faces entirely
and adds a properly-leveled ground plane underneath the course.
"""
import bpy
import bmesh
import math
from mathutils import Vector

# Golf spatial footprint (from scene analysis)
GOLF_CENTER = (20.85, 38.5)
GOLF_HIGH = (21.7, 37.0)   # Hole 1 end (Z~1.1)
GOLF_LOW = (20.0, 40.0)    # Hole 9 end (Z~0.3)

# Hole region - any face with a vertex inside this gets deleted
HOLE_RX = 3.0   # Just cover the golf footprint
HOLE_RY = 3.5
# Wider blend zone for the surrounding terrain depression
CUT_RX = 7.0
CUT_RY = 8.0

CUT_Z_HIGH = 0.85  # Near hole 1
CUT_Z_LOW = 0.05   # Near hole 9

GROUND_Z_HIGH = 0.95  # Ground plane Z at hole 1 end
GROUND_Z_LOW = 0.15   # Ground plane Z at hole 9 end


def slope_direction():
    dx = GOLF_LOW[0] - GOLF_HIGH[0]
    dy = GOLF_LOW[1] - GOLF_HIGH[1]
    length = math.sqrt(dx * dx + dy * dy)
    return (dx / length, dy / length, length)


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def slope_param(x, y):
    """Returns 0 at hole 1 (high), 1 at hole 9 (low)."""
    sdx, sdy, slen = slope_direction()
    px = x - GOLF_HIGH[0]
    py = y - GOLF_HIGH[1]
    return max(0.0, min(1.0, (px * sdx + py * sdy) / slen))


def ellipse_dist(x, y, rx, ry):
    cx, cy = GOLF_CENTER
    return math.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)


def delete_faces_in_hole(obj):
    """Delete terrain faces overlapping the golf area."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    faces_to_delete = []
    for face in bm.faces:
        # Delete face if ANY vertex is inside the hole zone
        for v in face.verts:
            d = ellipse_dist(v.co.x, v.co.y, HOLE_RX, HOLE_RY)
            if d < 0.85:  # Inside the hole (with some margin)
                faces_to_delete.append(face)
                break

    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(faces_to_delete)


def depress_surrounding_terrain(obj):
    """Smoothly depress terrain around the hole so it transitions to the cut edge."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    modified = 0
    for v in bm.verts:
        d = ellipse_dist(v.co.x, v.co.y, CUT_RX, CUT_RY)
        if d >= 1.0:
            continue

        t = slope_param(v.co.x, v.co.y)
        target_z = CUT_Z_HIGH + t * (CUT_Z_LOW - CUT_Z_HIGH)

        # Blend: full depression near hole edge, tapering to original at cut boundary
        if d < 0.5:
            blend = 1.0
        else:
            blend = 1.0 - smoothstep((d - 0.5) / 0.5)

        new_z = v.co.z * (1.0 - blend) + target_z * blend
        if new_z < v.co.z:
            v.co.z = new_z
            modified += 1

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return modified


def create_ground_plane():
    """Create a sloped ground plane inside the terrain hole."""
    cx, cy = GOLF_CENTER
    sdx, sdy, slen = slope_direction()

    # Ground plane covers the hole with some margin
    bm = bmesh.new()
    res = 16  # subdivisions for smooth slope

    verts_grid = []
    for ri in range(res + 1):
        row = []
        for ci in range(res + 1):
            # Local coordinates in ellipse space
            u = ci / res * 2.0 - 1.0  # -1 to 1
            v_coord = ri / res * 2.0 - 1.0

            x = cx + u * HOLE_RX * 0.9
            y = cy + v_coord * HOLE_RY * 0.9

            # Z follows the slope
            t = slope_param(x, y)
            z = GROUND_Z_LOW + (1.0 - t) * (GROUND_Z_HIGH - GROUND_Z_LOW)

            # Slight depression toward center for drainage look
            center_dist = math.sqrt(u * u + v_coord * v_coord)
            z -= 0.02 * max(0, 1.0 - center_dist)

            vert = bm.verts.new((x, y, z))
            row.append(vert)
        verts_grid.append(row)

    bm.verts.ensure_lookup_table()

    for ri in range(res):
        for ci in range(res):
            v1 = verts_grid[ri][ci]
            v2 = verts_grid[ri][ci + 1]
            v3 = verts_grid[ri + 1][ci + 1]
            v4 = verts_grid[ri + 1][ci]
            bm.faces.new([v1, v2, v3, v4])

    # UV layer
    uv = bm.loops.layers.uv.new("GroundUV")
    for face in bm.faces:
        for loop in face.loops:
            loop[uv].uv = (
                (loop.vert.co.x - cx + HOLE_RX) / (2 * HOLE_RX),
                (loop.vert.co.y - cy + HOLE_RY) / (2 * HOLE_RY)
            )

    mesh = bpy.data.meshes.new("GolfGround_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("GolfGround", mesh)
    for p in obj.data.polygons:
        p.use_smooth = True

    # Green grass material
    mat = bpy.data.materials.new("GolfGround_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9

    # Add grass-like noise texture
    tc = nodes.new("ShaderNodeTexCoord"); tc.location = (-500, 0)
    noise = nodes.new("ShaderNodeTexNoise"); noise.location = (-300, 0)
    noise.inputs["Scale"].default_value = 80.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.7
    links.new(tc.outputs["Object"], noise.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB"); ramp.location = (-100, 0)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.06, 0.18, 0.03, 1)  # Dark grass
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.12, 0.28, 0.06, 1)  # Light grass
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # Bump for grass texture
    bump = nodes.new("ShaderNodeBump"); bump.location = (100, -200)
    bump.inputs["Strength"].default_value = 0.08
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    obj.data.materials.append(mat)

    col = bpy.data.collections.get("RealTerrain")
    if col:
        col.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)

    return obj


def rebuild_retaining_walls():
    """Dry stone retaining walls around the terrain hole."""
    for obj in list(bpy.data.objects):
        if "RetainingWall" in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)

    col = bpy.data.collections.get("RealTerrain")
    if not col:
        return

    mat = bpy.data.materials.get("RetainingWall_Mat")
    if not mat:
        mat = bpy.data.materials.new("RetainingWall_Mat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.35, 0.33, 0.3, 1)
        bsdf.inputs["Roughness"].default_value = 0.92

    cx, cy = GOLF_CENTER
    segments = 48
    wall_thick = 0.04
    bm = bmesh.new()

    for i in range(segments):
        a1 = 2 * math.pi * i / segments
        a2 = 2 * math.pi * (i + 1) / segments

        # Ellipse at hole edge
        x1 = cx + HOLE_RX * 0.92 * math.cos(a1)
        y1 = cy + HOLE_RY * 0.92 * math.sin(a1)
        x2 = cx + HOLE_RX * 0.92 * math.cos(a2)
        y2 = cy + HOLE_RY * 0.92 * math.sin(a2)

        # Wall base Z = ground plane Z at this point
        t1 = slope_param(x1, y1)
        t2 = slope_param(x2, y2)
        z_base1 = GROUND_Z_LOW + (1.0 - t1) * (GROUND_Z_HIGH - GROUND_Z_LOW)
        z_base2 = GROUND_Z_LOW + (1.0 - t2) * (GROUND_Z_HIGH - GROUND_Z_LOW)

        # Wall height varies: taller on uphill side
        wh1 = 0.15 + (1.0 - t1) * 0.15  # 0.15-0.30 BU
        wh2 = 0.15 + (1.0 - t2) * 0.15

        # Normal direction (outward from center)
        nx1, ny1 = math.cos(a1), math.sin(a1)
        nx2, ny2 = math.cos(a2), math.sin(a2)

        # Inner verts (course side)
        vi1 = bm.verts.new((x1 - nx1 * wall_thick, y1 - ny1 * wall_thick, z_base1))
        vi2 = bm.verts.new((x1 - nx1 * wall_thick, y1 - ny1 * wall_thick, z_base1 + wh1))
        vi3 = bm.verts.new((x2 - nx2 * wall_thick, y2 - ny2 * wall_thick, z_base2))
        vi4 = bm.verts.new((x2 - nx2 * wall_thick, y2 - ny2 * wall_thick, z_base2 + wh2))

        # Outer verts (terrain side)
        vo1 = bm.verts.new((x1 + nx1 * wall_thick, y1 + ny1 * wall_thick, z_base1))
        vo2 = bm.verts.new((x1 + nx1 * wall_thick, y1 + ny1 * wall_thick, z_base1 + wh1))
        vo3 = bm.verts.new((x2 + nx2 * wall_thick, y2 + ny2 * wall_thick, z_base2))
        vo4 = bm.verts.new((x2 + nx2 * wall_thick, y2 + ny2 * wall_thick, z_base2 + wh2))

        # Outer face
        bm.faces.new([vo1, vo3, vo4, vo2])
        # Inner face
        bm.faces.new([vi1, vi2, vi4, vi3])
        # Top
        bm.faces.new([vi2, vo2, vo4, vi4])

    mesh = bpy.data.meshes.new("RetainingWalls_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    wall = bpy.data.objects.new("RetainingWall_Ring", mesh)
    wall.data.materials.append(mat)
    col.objects.link(wall)
    for p in wall.data.polygons:
        p.use_smooth = True
    return wall


# ═══════════════════════════════════════════
if __name__ == "__main__":
    import sys
    sys.path = [p for p in sys.path if 'python3.14' not in p]

    print("=== Terrain hole fix: delete faces + ground plane ===")

    # Remove old ground plane if exists
    old_ground = bpy.data.objects.get("GolfGround")
    if old_ground:
        bpy.data.objects.remove(old_ground, do_unlink=True)

    # 1. Delete terrain faces in golf area
    terrain = bpy.data.objects.get("RealTerrain")
    if terrain:
        ndel = delete_faces_in_hole(terrain)
        print(f"Terrain: deleted {ndel} faces")

        # Depress surrounding terrain smoothly
        nmod = depress_surrounding_terrain(terrain)
        print(f"Terrain: depressed {nmod} surrounding verts")

    # 2. Same for far hills
    far_hills = bpy.data.objects.get("FarHills")
    if far_hills:
        # Apply subsurf if present
        for mod in list(far_hills.modifiers):
            if mod.type == 'SUBSURF':
                bpy.context.view_layer.objects.active = far_hills
                bpy.ops.object.modifier_apply(modifier=mod.name)

        ndel_fh = delete_faces_in_hole(far_hills)
        print(f"FarHills: deleted {ndel_fh} faces")

        nmod_fh = depress_surrounding_terrain(far_hills)
        print(f"FarHills: depressed {nmod_fh} surrounding verts")

    # 3. Ground plane
    print("\n--- Ground plane ---")
    gp = create_ground_plane()
    print(f"Ground plane: {len(gp.data.polygons)} faces, Z range {GROUND_Z_LOW:.2f}-{GROUND_Z_HIGH:.2f}")

    # 4. Retaining walls
    print("\n--- Retaining walls ---")
    rebuild_retaining_walls()

    # 5. Save
    bpy.ops.wm.save_mainfile()

    # Stats
    print(f"\nDone. {len(bpy.data.objects)} objects, {len(bpy.data.materials)} materials")

    # Verify: terrain verts in golf bbox
    if terrain:
        bm_v = bmesh.new()
        bm_v.from_mesh(terrain.data)
        bm_v.verts.ensure_lookup_table()
        in_bbox = [v.co.z for v in bm_v.verts if 18 <= v.co.x <= 24 and 35 <= v.co.y <= 42]
        bm_v.free()
        if in_bbox:
            print(f"Remaining terrain verts in golf bbox: {len(in_bbox)}")
            print(f"  Z range: {min(in_bbox):.3f} to {max(in_bbox):.3f}")
            above = sum(1 for z in in_bbox if z > 0.25)
            print(f"  Above Z=0.25: {above}")
