"""Single-pass: create DEM terrain, scale golf to real-world size, cut into hillside 100m SW of Randlehow."""
import bpy
import bmesh
import math
import json
import os
import numpy as np
from mathutils import Vector, Matrix

GISDIR = "/home/devuser/workspace/minigolf/gis_data"

# ──────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────
TERRAIN_W_BU = 50.0       # Terrain width in Blender units (E-W)
GOLF_REAL_WIDTH_M = 40.0  # Real-world width of a mini golf course (meters)
OFFSET_M = 100.0          # Distance downhill from Randlehow
OFFSET_BEARING = 225.0    # Degrees from north (SW = 225)
COURSE_ROTATION = 45.0    # Degrees CCW, align NW-SE with contours


def load_data():
    with open(os.path.join(GISDIR, "fairfield_blender_meta.json")) as f:
        meta = json.load(f)
    with open(os.path.join(GISDIR, "fairfield_coords.json")) as f:
        coords = json.load(f)
    dem = np.load(os.path.join(GISDIR, "fairfield_dem.npy"))
    return meta, coords, dem


def get_or_create_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def compute_params(meta):
    th = TERRAIN_W_BU * (meta["terrain_height_m"] / meta["terrain_width_m"])
    m_per_bu = meta["terrain_width_m"] / TERRAIN_W_BU
    erbu = meta["elev_range"] / m_per_bu
    return th, m_per_bu, erbu


def elev_to_z(elev, meta, erbu):
    return ((elev - meta["elev_min"]) / max(1, meta["elev_range"])) * erbu


def create_terrain_mesh(dem, meta, col):
    th, m_per_bu, erbu = compute_params(meta)
    rows, cols = dem.shape

    bm = bmesh.new()
    step = 1  # full resolution since only 50x50
    sample_r = list(range(0, rows, step))
    sample_c = list(range(0, cols, step))
    sr, sc = len(sample_r), len(sample_c)

    verts = []
    for ri, r in enumerate(sample_r):
        for ci, c in enumerate(sample_c):
            x = (ci / (sc - 1)) * TERRAIN_W_BU
            y = (1.0 - ri / (sr - 1)) * th
            z = elev_to_z(float(dem[r, c]), meta, erbu)
            verts.append(bm.verts.new((x, y, z)))

    bm.verts.ensure_lookup_table()

    for ri in range(sr - 1):
        for ci in range(sc - 1):
            v1 = verts[ri * sc + ci]
            v2 = verts[ri * sc + ci + 1]
            v3 = verts[(ri + 1) * sc + ci + 1]
            v4 = verts[(ri + 1) * sc + ci]
            bm.faces.new([v1, v2, v3, v4])

    uv_layer = bm.loops.layers.uv.new("TerrainUV")
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = (loop.vert.co.x / TERRAIN_W_BU, loop.vert.co.y / th)

    mesh = bpy.data.meshes.new("RealTerrain_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("RealTerrain", mesh)
    col.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True

    sub = obj.modifiers.new("Subsurf", 'SUBSURF')
    sub.levels = 2
    sub.render_levels = 3

    return obj


def apply_terrain_material(obj):
    mat = bpy.data.materials.new("RealTerrain_PBR")
    mat.use_nodes = True
    N = mat.node_tree.nodes
    L = mat.node_tree.links
    for n in N:
        N.remove(n)

    out = N.new("ShaderNodeOutputMaterial"); out.location = (1200, 0)
    bsdf = N.new("ShaderNodeBsdfPrincipled"); bsdf.location = (800, 0)
    bsdf.inputs["Roughness"].default_value = 0.85
    L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = N.new("ShaderNodeTexCoord"); tc.location = (-800, 200)

    tex_path = os.path.join(GISDIR, "fairfield_terrain_texture.png")
    if os.path.exists(tex_path):
        img = bpy.data.images.load(tex_path)
        tex = N.new("ShaderNodeTexImage"); tex.image = img; tex.location = (-400, 300)
        L.new(tc.outputs["UV"], tex.inputs["Vector"])

    # Height-based procedural coloring
    sep = N.new("ShaderNodeSeparateXYZ"); sep.location = (-600, -200)
    L.new(tc.outputs["Object"], sep.inputs["Vector"])

    mr = N.new("ShaderNodeMapRange"); mr.location = (-400, -250)
    mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 7.0
    L.new(sep.outputs["Z"], mr.inputs["Value"])

    ar = N.new("ShaderNodeValToRGB"); ar.location = (-100, -250)
    ar.color_ramp.elements[0].position = 0.0; ar.color_ramp.elements[0].color = (0.12, 0.25, 0.06, 1)
    ar.color_ramp.elements[1].position = 0.35; ar.color_ramp.elements[1].color = (0.2, 0.3, 0.08, 1)
    e2 = ar.color_ramp.elements.new(0.6); e2.color = (0.35, 0.18, 0.35, 1)
    e3 = ar.color_ramp.elements.new(0.85); e3.color = (0.4, 0.38, 0.35, 1)
    L.new(mr.outputs["Result"], ar.inputs["Fac"])

    if os.path.exists(tex_path):
        mx = N.new("ShaderNodeMixRGB"); mx.location = (450, 100)
        mx.blend_type = 'MULTIPLY'; mx.inputs["Fac"].default_value = 0.5
        L.new(tex.outputs["Color"], mx.inputs["Color1"])
        L.new(ar.outputs["Color"], mx.inputs["Color2"])

        br = N.new("ShaderNodeMixRGB"); br.location = (650, 100)
        br.blend_type = 'ADD'; br.inputs["Fac"].default_value = 0.35
        L.new(mx.outputs["Color"], br.inputs["Color1"])
        L.new(ar.outputs["Color"], br.inputs["Color2"])
        L.new(br.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        L.new(ar.outputs["Color"], bsdf.inputs["Base Color"])

    bn = N.new("ShaderNodeTexNoise"); bn.location = (200, -400)
    bn.inputs["Scale"].default_value = 200.0; bn.inputs["Detail"].default_value = 6.0
    L.new(tc.outputs["Object"], bn.inputs["Vector"])
    bump = N.new("ShaderNodeBump"); bump.location = (500, -400)
    bump.inputs["Strength"].default_value = 0.15
    L.new(bn.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    obj.data.materials.append(mat)


def cut_terrain(terrain_obj, center, target_z, rx, ry):
    """Depress terrain verts into a smooth shelf for the golf course."""
    bm = bmesh.new()
    bm.from_mesh(terrain_obj.data)
    bm.verts.ensure_lookup_table()

    cx, cy = center
    modified = 0
    for v in bm.verts:
        dx = (v.co.x - cx) / rx
        dy = (v.co.y - cy) / ry
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1.0:
            if dist < 0.6:
                blend = 1.0
            else:
                t = (dist - 0.6) / 0.4
                blend = 1.0 - t * t * (3 - 2 * t)
            v.co.z = v.co.z * (1.0 - blend) + target_z * blend
            modified += 1

    bm.to_mesh(terrain_obj.data)
    bm.free()
    terrain_obj.data.update()
    return modified


def rescale_and_place_golf(meta, dem, target_center, target_z, rotation_rad):
    """Scale all existing golf objects and place on terrain."""
    th, m_per_bu, erbu = compute_params(meta)

    # Original golf spans X=0 to 9.05, Y=0 to 16
    orig_cx = 4.525
    orig_cy = 8.0

    scale = GOLF_REAL_WIDTH_M / (9.05 * m_per_bu)
    tx, ty = target_center
    cos_r = math.cos(rotation_rad)
    sin_r = math.sin(rotation_rad)

    terrain_col_names = {"RealTerrain"}
    terrain_prefixes = ["RealTerrain", "TerrainSun", "TerrainCamera", "TerrainTracker",
                        "RetainingWall", "AccessPath"]

    moved = 0
    for obj in bpy.data.objects:
        skip = False
        for c in obj.users_collection:
            if c.name in terrain_col_names:
                skip = True
        for pfx in terrain_prefixes:
            if obj.name.startswith(pfx):
                skip = True
        if skip:
            continue

        # Position relative to original center
        rx = obj.location.x - orig_cx
        ry = obj.location.y - orig_cy
        rz = obj.location.z

        # Scale
        rx *= scale
        ry *= scale
        rz *= scale

        # Rotate
        new_rx = rx * cos_r - ry * sin_r
        new_ry = rx * sin_r + ry * cos_r

        # Translate to target
        obj.location.x = tx + new_rx
        obj.location.y = ty + new_ry
        obj.location.z = target_z + rz

        # Scale the object mesh
        obj.scale *= scale

        # Rotate object
        obj.rotation_euler.z += rotation_rad

        moved += 1

    return moved, scale


def build_retaining_walls(center, target_z, half_w, half_h, rotation_rad, col):
    """Stone retaining walls on uphill sides."""
    mat = bpy.data.materials.new("RetainingWall_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.35, 0.33, 0.3, 1)
    bsdf.inputs["Roughness"].default_value = 0.92

    cx, cy = center
    cos_r = math.cos(rotation_rad)
    sin_r = math.sin(rotation_rad)
    wh = 0.12  # wall height
    wt = 0.025

    segs = [
        (-half_w, half_h, half_w, half_h),     # Uphill (N in local)
        (half_w, -half_h * 0.5, half_w, half_h),  # Right/E (partial)
        (-half_w, 0, -half_w, half_h),          # Left/W (upper half)
    ]

    for i, (lx1, ly1, lx2, ly2) in enumerate(segs):
        wx1 = cx + lx1 * cos_r - ly1 * sin_r
        wy1 = cy + lx1 * sin_r + ly1 * cos_r
        wx2 = cx + lx2 * cos_r - ly2 * sin_r
        wy2 = cy + lx2 * sin_r + ly2 * cos_r

        length = math.sqrt((wx2 - wx1)**2 + (wy2 - wy1)**2)
        angle = math.atan2(wy2 - wy1, wx2 - wx1)

        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= length; v.co.y *= wt; v.co.z *= wh
        mesh = bpy.data.meshes.new(f"RetainWall_{i}_Mesh")
        bm.to_mesh(mesh); bm.free()

        wall = bpy.data.objects.new(f"RetainingWall_{i}", mesh)
        wall.location = ((wx1+wx2)/2, (wy1+wy2)/2, target_z + wh/2)
        wall.rotation_euler.z = angle
        wall.data.materials.append(mat)
        col.objects.link(wall)


def build_access_path(center, target_z, meta, erbu, col):
    """Gravel path from Randlehow to the golf course."""
    th, m_per_bu, _ = compute_params(meta)
    cx, cy = center
    rx = TERRAIN_W_BU / 2
    ry = th / 2
    rz = elev_to_z(meta["fairfield_elev"], meta, erbu)

    mat = bpy.data.materials.new("GravelPath_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.5, 0.47, 0.42, 1)
    bsdf.inputs["Roughness"].default_value = 0.95

    pw = 0.04
    pts = [(rx, ry, rz+0.01), ((rx+cx)/2, (ry+cy)/2, (rz+target_z)/2+0.01), (cx, cy-0.3, target_z+0.01)]

    bm = bmesh.new()
    for j in range(len(pts)-1):
        x1, y1, z1 = pts[j]; x2, y2, z2 = pts[j+1]
        d = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        px, py = -(y2-y1)/d * pw, (x2-x1)/d * pw
        v1 = bm.verts.new((x1+px, y1+py, z1))
        v2 = bm.verts.new((x1-px, y1-py, z1))
        v3 = bm.verts.new((x2-px, y2-py, z2))
        v4 = bm.verts.new((x2+px, y2+py, z2))
        bm.faces.new([v1, v2, v3, v4])

    mesh = bpy.data.meshes.new("AccessPath_Mesh")
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new("AccessPath", mesh)
    obj.data.materials.append(mat)
    col.objects.link(obj)


def setup_lighting():
    for ob in list(bpy.data.objects):
        if ob.type == 'LIGHT' and 'Sun' in ob.name:
            bpy.data.objects.remove(ob, do_unlink=True)

    sun = bpy.data.lights.new("TerrainSun", 'SUN')
    sun.energy = 4.0; sun.color = (1.0, 0.95, 0.85); sun.angle = 0.03
    sobj = bpy.data.objects.new("TerrainSun", sun)
    bpy.context.scene.collection.objects.link(sobj)
    sobj.rotation_euler = (math.radians(55), math.radians(15), math.radians(-30))

    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("TerrainWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes; links = world.node_tree.links
    for n in nodes: nodes.remove(n)

    out = nodes.new("ShaderNodeOutputWorld"); out.location = (400, 0)
    bg = nodes.new("ShaderNodeBackground"); bg.location = (200, 0)
    bg.inputs["Strength"].default_value = 0.8
    bg.inputs["Color"].default_value = (0.45, 0.55, 0.72, 1)
    links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_camera(center, target_z):
    cx, cy = center
    cam_data = bpy.data.cameras.new("TerrainCam")
    cam_data.lens = 32; cam_data.clip_end = 500
    cam = bpy.data.objects.new("TerrainCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (cx - 6, cy - 8, target_z + 6)
    direction = Vector((cx, cy, target_z)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam


# ──────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path = [p for p in sys.path if 'python3.14' not in p]

    meta, coords, dem = load_data()
    th, m_per_bu, erbu = compute_params(meta)

    print("=== Terrain + Golf Emplacement (Single Pass) ===")
    print(f"Terrain: {TERRAIN_W_BU:.0f} x {th:.1f} BU ({meta['terrain_width_m']:.0f}m x {meta['terrain_height_m']:.0f}m)")
    print(f"1 BU = {m_per_bu:.1f}m")

    # Randlehow position on terrain
    rh_x = TERRAIN_W_BU / 2  # center X
    rh_y = th / 2             # center Y
    rh_z = elev_to_z(meta["fairfield_elev"], meta, erbu)

    # 100m downhill (SW)
    dx_m = OFFSET_M * math.sin(math.radians(OFFSET_BEARING))
    dy_m = OFFSET_M * math.cos(math.radians(OFFSET_BEARING))
    target_cx = rh_x + dx_m / m_per_bu
    target_cy = rh_y + dy_m / m_per_bu

    # Elevation at target
    dem_r = int((1.0 - target_cy / th) * (dem.shape[0] - 1))
    dem_c = int((target_cx / TERRAIN_W_BU) * (dem.shape[1] - 1))
    dem_r = max(0, min(dem.shape[0]-1, dem_r))
    dem_c = max(0, min(dem.shape[1]-1, dem_c))
    target_elev = float(dem[dem_r, dem_c])
    target_z = elev_to_z(target_elev, meta, erbu)

    print(f"Randlehow: ({rh_x:.1f}, {rh_y:.1f}, {rh_z:.2f}) elev={meta['fairfield_elev']}m")
    print(f"Target: ({target_cx:.2f}, {target_cy:.2f}, {target_z:.2f}) elev={target_elev:.0f}m")

    rot_rad = math.radians(COURSE_ROTATION)

    # 1. Terrain mesh
    print("\n--- Building terrain ---")
    tcol = get_or_create_collection("RealTerrain")
    tobj = create_terrain_mesh(dem, meta, tcol)
    apply_terrain_material(tobj)
    print(f"Terrain mesh: {len(tobj.data.vertices)} verts, {len(tobj.data.polygons)} faces")

    # 2. Scale + place golf
    print("\n--- Scaling and placing golf course ---")
    moved, scale = rescale_and_place_golf(meta, dem, (target_cx, target_cy), target_z, rot_rad)
    golf_hw = 9.05 / 2 * scale  # half-width in BU
    golf_hh = 16.0 / 2 * scale  # half-height in BU
    print(f"Moved {moved} objects, scale={scale:.4f}")
    print(f"Course size: {golf_hw*2:.2f} x {golf_hh*2:.2f} BU = {golf_hw*2*m_per_bu:.0f}m x {golf_hh*2*m_per_bu:.0f}m")

    # 3. Cut terrain
    print("\n--- Cutting terrain ---")
    cut_rx = golf_hw * 1.5
    cut_ry = golf_hh * 1.5
    ncut = cut_terrain(tobj, (target_cx, target_cy), target_z, cut_rx, cut_ry)
    print(f"Cut {ncut} terrain vertices")

    # 4. Retaining walls
    print("\n--- Retaining walls ---")
    build_retaining_walls((target_cx, target_cy), target_z, golf_hw*1.1, golf_hh*1.1, rot_rad, tcol)

    # 5. Access path
    print("\n--- Access path ---")
    build_access_path((target_cx, target_cy), target_z, meta, erbu, tcol)

    # 6. Lighting
    print("\n--- Lighting ---")
    setup_lighting()

    # 7. Camera
    setup_camera((target_cx, target_cy), target_z)

    # Save to original location
    bpy.ops.wm.save_as_mainfile(filepath="/home/devuser/workspace/minigolf/minigolf_course.blend")

    print(f"\n=== Complete ===")
    print(f"Objects: {len(bpy.data.objects)}")
    print(f"Materials: {len(bpy.data.materials)}")
    print(f"Golf at ({target_cx:.2f}, {target_cy:.2f}) - 100m SW of Randlehow")
    print(f"Elevation: {target_elev:.0f}m ASL (Randlehow: {meta['fairfield_elev']}m)")
    print(f"Course: {golf_hw*2*m_per_bu:.0f}m x {golf_hh*2*m_per_bu:.0f}m, rotated {COURSE_ROTATION}deg")
