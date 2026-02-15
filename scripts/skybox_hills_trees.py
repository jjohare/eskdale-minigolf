"""Add HDRI-style skybox, extended far hills, scattered trees, and flythrough animation."""
import bpy
import bmesh
import math
import json
import os
import random
import numpy as np
from mathutils import Vector, noise

GISDIR = "/home/devuser/workspace/minigolf/gis_data"
random.seed(54)  # Reproducible

# ── Load metadata ──
with open(os.path.join(GISDIR, "fairfield_blender_meta.json")) as f:
    META = json.load(f)
DEM = np.load(os.path.join(GISDIR, "fairfield_dem.npy"))

TERRAIN_W = 50.0
TERRAIN_H = TERRAIN_W * (META["terrain_height_m"] / META["terrain_width_m"])
M_PER_BU = META["terrain_width_m"] / TERRAIN_W
ERBU = META["elev_range"] / M_PER_BU

# Golf course location
GOLF_CX = 21.07
GOLF_CY = 39.01
GOLF_Z = 1.11


def get_or_create_col(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def elev_z(elev):
    return ((elev - META["elev_min"]) / max(1, META["elev_range"])) * ERBU


def terrain_z_at(x, y):
    """Sample terrain elevation at Blender coords from DEM."""
    col_f = x / TERRAIN_W * (DEM.shape[1] - 1)
    row_f = (1.0 - y / TERRAIN_H) * (DEM.shape[0] - 1)
    r = max(0, min(DEM.shape[0]-1, int(row_f)))
    c = max(0, min(DEM.shape[1]-1, int(col_f)))
    return elev_z(float(DEM[r, c]))


# ═══════════════════════════════════════════
# 1. SKYBOX - Procedural Lake District sky
# ═══════════════════════════════════════════
def create_skybox():
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("EskdaleSky")
        bpy.context.scene.world = world
    world.use_nodes = True
    N = world.node_tree.nodes
    L = world.node_tree.links
    for n in N:
        N.remove(n)

    out = N.new("ShaderNodeOutputWorld"); out.location = (1000, 0)

    # Mix sky + clouds
    mix_shader = N.new("ShaderNodeMixShader"); mix_shader.location = (800, 0)
    L.new(mix_shader.outputs["Shader"], out.inputs["Surface"])

    # Sky gradient
    sky_bg = N.new("ShaderNodeBackground"); sky_bg.location = (500, 100)
    sky_bg.inputs["Strength"].default_value = 1.0

    tc = N.new("ShaderNodeTexCoord"); tc.location = (-600, 0)

    # Separate Z for vertical gradient
    sep = N.new("ShaderNodeSeparateXYZ"); sep.location = (-400, 100)
    L.new(tc.outputs["Generated"], sep.inputs["Vector"])

    # Sky color ramp: horizon warm -> zenith blue
    sky_ramp = N.new("ShaderNodeValToRGB"); sky_ramp.location = (-100, 200)
    sky_ramp.color_ramp.elements[0].position = 0.0
    sky_ramp.color_ramp.elements[0].color = (0.72, 0.75, 0.8, 1)   # Horizon: pale misty
    sky_ramp.color_ramp.elements[1].position = 0.5
    sky_ramp.color_ramp.elements[1].color = (0.28, 0.45, 0.72, 1)  # Zenith: deep blue
    e_warm = sky_ramp.color_ramp.elements.new(0.15)
    e_warm.color = (0.8, 0.78, 0.7, 1)  # Golden band near horizon

    # Map range for Z: the generated coords Z goes 0..1 bottom to top
    mr = N.new("ShaderNodeMapRange"); mr.location = (-250, 200)
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    L.new(sep.outputs["Z"], mr.inputs["Value"])
    L.new(mr.outputs["Result"], sky_ramp.inputs["Fac"])
    L.new(sky_ramp.outputs["Color"], sky_bg.inputs["Color"])

    # Cloud layer
    cloud_bg = N.new("ShaderNodeBackground"); cloud_bg.location = (500, -100)
    cloud_bg.inputs["Color"].default_value = (0.92, 0.93, 0.95, 1)
    cloud_bg.inputs["Strength"].default_value = 1.2

    # Cloud noise
    cloud_noise = N.new("ShaderNodeTexNoise"); cloud_noise.location = (-200, -100)
    cloud_noise.inputs["Scale"].default_value = 3.0
    cloud_noise.inputs["Detail"].default_value = 6.0
    cloud_noise.inputs["Roughness"].default_value = 0.65
    cloud_noise.inputs["Distortion"].default_value = 0.8
    L.new(tc.outputs["Generated"], cloud_noise.inputs["Vector"])

    # Cloud mask: only in upper hemisphere, wispy
    cloud_ramp = N.new("ShaderNodeValToRGB"); cloud_ramp.location = (100, -100)
    cloud_ramp.color_ramp.elements[0].position = 0.45
    cloud_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    cloud_ramp.color_ramp.elements[1].position = 0.55
    cloud_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(cloud_noise.outputs["Fac"], cloud_ramp.inputs["Fac"])

    # Multiply cloud mask with height (only show clouds above horizon)
    cloud_height_mask = N.new("ShaderNodeMath"); cloud_height_mask.location = (250, -50)
    cloud_height_mask.operation = 'MULTIPLY'
    L.new(cloud_ramp.outputs["Color"], cloud_height_mask.inputs[0])

    # Height factor: clouds only above 0.4 in generated Z
    height_ramp = N.new("ShaderNodeValToRGB"); height_ramp.location = (0, -300)
    height_ramp.color_ramp.elements[0].position = 0.35
    height_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    height_ramp.color_ramp.elements[1].position = 0.55
    height_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(sep.outputs["Z"], height_ramp.inputs["Fac"])
    L.new(height_ramp.outputs["Color"], cloud_height_mask.inputs[1])

    # Final cloud factor (reduce to ~30% coverage)
    cloud_factor = N.new("ShaderNodeMath"); cloud_factor.location = (400, -50)
    cloud_factor.operation = 'MULTIPLY'
    cloud_factor.inputs[1].default_value = 0.35
    L.new(cloud_height_mask.outputs["Value"], cloud_factor.inputs[0])

    L.new(cloud_factor.outputs["Value"], mix_shader.inputs["Fac"])
    L.new(sky_bg.outputs["Background"], mix_shader.inputs[1])
    L.new(cloud_bg.outputs["Background"], mix_shader.inputs[2])

    print("Skybox: Lake District sky with wispy clouds")


# ═══════════════════════════════════════════
# 2. FAR HILLS - Extended terrain ring
# ═══════════════════════════════════════════
def create_far_hills():
    col = get_or_create_col("RealTerrain")

    # Create a large ring of procedural hills around the DEM terrain
    # The DEM covers 50x86 BU. We extend to ~200x200 BU with procedural elevation.

    bm = bmesh.new()
    ring_size = 200  # BU
    ring_res = 40    # vertices per side
    center_x = TERRAIN_W / 2
    center_y = TERRAIN_H / 2

    verts_grid = []
    for ri in range(ring_res):
        row = []
        for ci in range(ring_res):
            x = (ci / (ring_res - 1) - 0.5) * ring_size + center_x
            y = (ri / (ring_res - 1) - 0.5) * ring_size + center_y

            # Check if inside DEM bounds - skip (terrain already there)
            in_dem = (0 < x < TERRAIN_W and 0 < y < TERRAIN_H)

            if in_dem:
                # Match DEM edge elevation for seamless blend
                ex = max(0.01, min(0.99, x / TERRAIN_W))
                ey = max(0.01, min(0.99, y / TERRAIN_H))
                dem_r = int((1.0 - ey) * (DEM.shape[0] - 1))
                dem_c = int(ex * (DEM.shape[1] - 1))
                z = elev_z(float(DEM[dem_r, dem_c]))
            else:
                # Procedural hills: use distance from center to ramp up
                dx = (x - center_x) / (ring_size * 0.4)
                dy = (y - center_y) / (ring_size * 0.4)
                dist = math.sqrt(dx*dx + dy*dy)

                # Base elevation matches DEM edge
                base_z = 2.0  # ~36m average edge elevation

                # Add rolling hills that increase with distance
                # Use multiple octaves for natural look
                px = x * 0.05
                py = y * 0.05
                hill = (math.sin(px * 1.3 + 0.5) * math.cos(py * 0.9 + 0.3) * 1.5 +
                        math.sin(px * 2.7 + 1.2) * math.cos(py * 2.1 + 0.7) * 0.8 +
                        math.sin(px * 5.1 + 2.1) * math.cos(py * 4.3 + 1.5) * 0.3)

                # Hills get taller further from center (fells rising)
                # North/NE gets highest (matches real Eskdale geography)
                north_bias = max(0, (y - center_y) / (ring_size * 0.3))
                height_factor = 1.0 + dist * 1.5 + north_bias * 3.0

                z = base_z + hill * height_factor

                # Minimum elevation (don't go below sea level)
                z = max(0.2, z)

            v = bm.verts.new((x, y, z))
            row.append(v)
        verts_grid.append(row)

    bm.verts.ensure_lookup_table()

    for ri in range(ring_res - 1):
        for ci in range(ring_res - 1):
            v1 = verts_grid[ri][ci]
            v2 = verts_grid[ri][ci + 1]
            v3 = verts_grid[ri + 1][ci + 1]
            v4 = verts_grid[ri + 1][ci]
            bm.faces.new([v1, v2, v3, v4])

    mesh = bpy.data.meshes.new("FarHills_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("FarHills", mesh)
    col.objects.link(obj)
    for p in obj.data.polygons:
        p.use_smooth = True

    sub = obj.modifiers.new("Subsurf", 'SUBSURF')
    sub.levels = 1
    sub.render_levels = 2

    # Material: match terrain but more muted (atmospheric perspective)
    mat = bpy.data.materials.new("FarHills_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        nodes.remove(n)

    out = nodes.new("ShaderNodeOutputMaterial"); out.location = (800, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (500, 0)
    bsdf.inputs["Roughness"].default_value = 0.9
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord"); tc.location = (-500, 0)
    sep = nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-300, -100)
    links.new(tc.outputs["Object"], sep.inputs["Vector"])

    mr = nodes.new("ShaderNodeMapRange"); mr.location = (-100, -100)
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 12.0
    links.new(sep.outputs["Z"], mr.inputs["Value"])

    ramp = nodes.new("ShaderNodeValToRGB"); ramp.location = (100, -100)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.15, 0.28, 0.08, 1)  # Valley green
    ramp.color_ramp.elements[1].position = 0.3
    ramp.color_ramp.elements[1].color = (0.22, 0.3, 0.12, 1)   # Bracken
    e2 = ramp.color_ramp.elements.new(0.55)
    e2.color = (0.35, 0.2, 0.32, 1)                              # Heather
    e3 = ramp.color_ramp.elements.new(0.8)
    e3.color = (0.45, 0.42, 0.4, 1)                              # Fell grey
    e4 = ramp.color_ramp.elements.new(1.0)
    e4.color = (0.55, 0.53, 0.5, 1)                              # High scree
    links.new(mr.outputs["Result"], ramp.inputs["Fac"])

    # Atmospheric haze: blend with sky color based on distance from camera
    cam_pos = nodes.new("ShaderNodeCameraData"); cam_pos.location = (-300, -300)
    haze_mr = nodes.new("ShaderNodeMapRange"); haze_mr.location = (-100, -300)
    haze_mr.inputs["From Min"].default_value = 20.0
    haze_mr.inputs["From Max"].default_value = 120.0
    links.new(cam_pos.outputs["View Z Depth"], haze_mr.inputs["Value"])

    haze_mix = nodes.new("ShaderNodeMixRGB"); haze_mix.location = (300, 0)
    haze_mix.blend_type = 'MIX'
    links.new(haze_mr.outputs["Result"], haze_mix.inputs["Fac"])
    links.new(ramp.outputs["Color"], haze_mix.inputs["Color1"])
    haze_mix.inputs["Color2"].default_value = (0.6, 0.65, 0.72, 1)  # Haze color
    links.new(haze_mix.outputs["Color"], bsdf.inputs["Base Color"])

    obj.data.materials.append(mat)
    print(f"Far hills: {len(obj.data.vertices)} verts, {ring_size}x{ring_size} BU extent")
    return obj


# ═══════════════════════════════════════════
# 3. TREES scattered on terrain
# ═══════════════════════════════════════════
def scatter_trees():
    col = get_or_create_col("RealTerrain")

    # Bark material
    bark = bpy.data.materials.new("TreeBark_Mat")
    bark.use_nodes = True
    bsdf_b = bark.node_tree.nodes["Principled BSDF"]
    bsdf_b.inputs["Base Color"].default_value = (0.12, 0.08, 0.05, 1)
    bsdf_b.inputs["Roughness"].default_value = 0.95

    # Create several canopy color variants
    canopy_mats = []
    canopy_colors = [
        (0.05, 0.15, 0.03, 1),  # Dark oak
        (0.08, 0.2, 0.04, 1),   # Medium green
        (0.12, 0.25, 0.06, 1),  # Light birch
        (0.06, 0.12, 0.04, 1),  # Dark spruce
        (0.15, 0.22, 0.05, 1),  # Autumn-tinge
    ]
    for i, cc in enumerate(canopy_colors):
        m = bpy.data.materials.new(f"Canopy_{i}_Mat")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = cc
        b.inputs["Roughness"].default_value = 0.85
        canopy_mats.append(m)

    # Generate tree positions - avoid golf course area and stay on terrain
    trees_placed = 0
    max_trees = 120

    # Weighted distribution: more trees in valleys, fewer on high fells
    attempts = 0
    while trees_placed < max_trees and attempts < max_trees * 5:
        attempts += 1
        x = random.uniform(1, TERRAIN_W - 1)
        y = random.uniform(1, TERRAIN_H - 1)

        # Skip if near golf course
        dx = x - GOLF_CX
        dy = y - GOLF_CY
        if math.sqrt(dx*dx + dy*dy) < 4:
            continue

        z = terrain_z_at(x, y)

        # Trees mostly below 80m ASL (z ~ 3.4 BU), sparse above
        real_elev = META["elev_min"] + (z / ERBU) * META["elev_range"]
        if real_elev > 100:  # Very few trees above 100m
            if random.random() > 0.1:
                continue
        elif real_elev > 70:  # Sparse above 70m
            if random.random() > 0.4:
                continue

        # Tree size varies with elevation (smaller higher up)
        size_factor = max(0.3, 1.0 - (real_elev - 30) / 120)
        trunk_h = random.uniform(0.15, 0.35) * size_factor
        canopy_r = random.uniform(0.1, 0.25) * size_factor

        # Trunk
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, segments=6, radius1=0.015 * size_factor,
                              radius2=0.008 * size_factor, depth=trunk_h)
        mesh = bpy.data.meshes.new(f"Trunk_{trees_placed}")
        bm.to_mesh(mesh); bm.free()
        trunk = bpy.data.objects.new(f"ScatTree_{trees_placed}_Trunk", mesh)
        trunk.location = (x, y, z + trunk_h / 2)
        trunk.data.materials.append(bark)
        col.objects.link(trunk)

        # Canopy
        bm = bmesh.new()
        # Mix of shapes: spheres for deciduous, cones for conifers
        if random.random() < 0.6:
            # Deciduous (sphere)
            bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=canopy_r)
            for v in bm.verts:
                v.co.z *= 0.7  # Slightly flattened
                # Random deformation for organic look
                v.co.x *= random.uniform(0.85, 1.15)
                v.co.y *= random.uniform(0.85, 1.15)
        else:
            # Conifer (cone)
            bmesh.ops.create_cone(bm, segments=8, radius1=canopy_r * 0.8,
                                  radius2=0, depth=canopy_r * 2.5)

        mesh = bpy.data.meshes.new(f"Canopy_{trees_placed}")
        bm.to_mesh(mesh); bm.free()
        canopy = bpy.data.objects.new(f"ScatTree_{trees_placed}_Canopy", mesh)
        canopy.location = (x, y, z + trunk_h + canopy_r * 0.3)
        canopy.rotation_euler.z = random.uniform(0, math.pi * 2)
        canopy.data.materials.append(random.choice(canopy_mats))
        col.objects.link(canopy)

        trees_placed += 1

    print(f"Scattered {trees_placed} trees across terrain")


# ═══════════════════════════════════════════
# 4. FLYTHROUGH ANIMATION
# ═══════════════════════════════════════════
def create_flythrough():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 480  # 16 seconds at 30fps
    scene.render.fps = 30

    cam = bpy.data.objects.get("TerrainCamera")
    if not cam:
        cam_data = bpy.data.cameras.new("TerrainCam")
        cam = bpy.data.objects.new("TerrainCamera", cam_data)
        bpy.context.scene.collection.objects.link(cam)
    cam.animation_data_clear()
    cam.data.lens = 28
    cam.data.clip_end = 500
    scene.camera = cam

    # Track target at golf course
    tracker = bpy.data.objects.get("TerrainTracker")
    if not tracker:
        tracker = bpy.data.objects.new("TerrainTracker", None)
        bpy.context.scene.collection.objects.link(tracker)
    tracker.animation_data_clear()

    # Remove old constraints
    for c in cam.constraints:
        cam.constraints.remove(c)
    track = cam.constraints.new('TRACK_TO')
    track.target = tracker
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    # Cinematic orbit + approach + pullback
    # Start wide, spiral in, fly low over course, pull back to wide
    cx, cy, cz = GOLF_CX, GOLF_CY, GOLF_Z

    waypoints = [
        # (frame, cam_x, cam_y, cam_z, look_x, look_y, look_z, lens)
        (1,    cx+25, cy-25, 18,   cx, cy, cz,    24),   # Wide SE, high
        (60,   cx+20, cy-10, 12,   cx, cy, cz,    28),   # Orbiting E
        (120,  cx+10, cy+15, 8,    cx, cy, cz,    32),   # NE, descending
        (180,  cx-5,  cy+10, 4,    cx, cy, cz+0.5, 35),  # Close N, low
        (220,  cx-2,  cy,    2.2,  cx+1, cy+1, cz, 40),  # Eye level, on course
        (260,  cx+3,  cy-3,  2.5,  cx, cy+2, cz,   38),  # Across course
        (320,  cx-15, cy-5,  6,    cx, cy, cz,    30),   # Pull back W
        (380,  cx-20, cy+20, 14,   cx, cy, cz,    26),   # Wide NW, rising
        (440,  cx+15, cy+25, 20,   cx, cy, cz,    24),   # Wide NE, high
        (480,  cx+25, cy-25, 18,   cx, cy, cz,    24),   # Back to start
    ]

    for frame, cam_x, cam_y, cam_z, lx, ly, lz, lens in waypoints:
        cam.location = (cam_x, cam_y, cam_z)
        cam.keyframe_insert('location', frame=frame)
        cam.data.lens = lens
        cam.data.keyframe_insert('lens', frame=frame)
        tracker.location = (lx, ly, lz)
        tracker.keyframe_insert('location', frame=frame)

    print(f"Flythrough: {scene.frame_end} frames, {scene.frame_end/scene.render.fps:.0f}s at {scene.render.fps}fps")
    print(f"{len(waypoints)} waypoints, orbit + low pass + pullback")


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════
if __name__ == "__main__":
    import sys
    sys.path = [p for p in sys.path if 'python3.14' not in p]

    print("=== Adding skybox, far hills, trees, flythrough ===")

    print("\n--- Skybox ---")
    create_skybox()

    print("\n--- Far hills ---")
    create_far_hills()

    print("\n--- Trees ---")
    scatter_trees()

    print("\n--- Flythrough animation ---")
    create_flythrough()

    bpy.ops.wm.save_mainfile()
    print(f"\nDone: {len(bpy.data.objects)} objects, {len(bpy.data.materials)} materials")
