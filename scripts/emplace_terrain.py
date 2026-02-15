"""Import real-world DEM terrain into Blender, texture it, and emplace the mini golf at Fairfield's garden."""
import bpy
import bmesh
import json
import os
import math
import numpy as np
from mathutils import Vector

GISDIR = "/home/devuser/workspace/minigolf/gis_data"


def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        if parent:
            parent.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col


def load_metadata():
    with open(os.path.join(GISDIR, "fairfield_blender_meta.json")) as f:
        meta = json.load(f)
    with open(os.path.join(GISDIR, "fairfield_coords.json")) as f:
        coords = json.load(f)
    return meta, coords


def create_terrain_mesh(dem, meta, terrain_col):
    """Create a subdivided plane mesh displaced by real DEM elevation data."""
    rows, cols = dem.shape

    # Scale: the golf course spans ~10x16 Blender units
    # Real terrain is ~900m x 1546m
    # We want the golf course (~50m real garden) to sit at about 10x16 BU
    # So 1 BU = ~5m real-world (garden is ~50x80m for 9 holes)
    # Terrain at this scale: 900/5 = 180 BU wide, 1546/5 = 309 BU tall
    # That's too large. Instead, let's make the terrain a backdrop.

    # Golf course is 10x16 BU. Real garden ~60x100m.
    # Scale: 1 BU = ~6m. Terrain = 900/6 = 150 x 1546/6 = 258 BU.
    # Still large. Let's use a tighter crop: the golf sits at center,
    # we show ~300m radius around it = 600m / 6 = 100 BU terrain.

    # Actually: keep it manageable. Make terrain 40x40 BU centered on golf.
    # That represents ~240m x 240m of real terrain around Fairfield.

    terrain_width_bu = 50.0   # BU width (E-W)
    terrain_height_bu = 85.0  # BU height (N-S), proportional to real dims

    # The real terrain is 900m x 1546m, ratio ~1:1.72
    terrain_height_bu = terrain_width_bu * (meta["terrain_height_m"] / meta["terrain_width_m"])

    # Elevation scaling: range is 19-142m = 123m
    # In BU at 1BU=~18m/BU (900m/50BU): 123m = ~6.8 BU
    m_per_bu = meta["terrain_width_m"] / terrain_width_bu
    elev_range_bu = meta["elev_range"] / m_per_bu

    # Create subdivided grid mesh
    bm = bmesh.new()

    # Sample every N pixels for reasonable mesh density
    step = max(1, min(rows, cols) // 50)  # ~50x50 verts max
    sample_rows = list(range(0, rows, step))
    sample_cols = list(range(0, cols, step))
    if sample_rows[-1] != rows - 1:
        sample_rows.append(rows - 1)
    if sample_cols[-1] != cols - 1:
        sample_cols.append(cols - 1)

    sr = len(sample_rows)
    sc = len(sample_cols)

    # Create vertices
    verts = []
    for ri, r in enumerate(sample_rows):
        for ci, c in enumerate(sample_cols):
            x = (ci / (sc - 1)) * terrain_width_bu
            y = (1.0 - ri / (sr - 1)) * terrain_height_bu  # Flip: row 0 = north = top
            elev = float(dem[r, c])
            z = ((elev - meta["elev_min"]) / max(1, meta["elev_range"])) * elev_range_bu
            v = bm.verts.new((x, y, z))
            verts.append(v)

    bm.verts.ensure_lookup_table()

    # Create faces
    for ri in range(sr - 1):
        for ci in range(sc - 1):
            v1 = verts[ri * sc + ci]
            v2 = verts[ri * sc + ci + 1]
            v3 = verts[(ri + 1) * sc + ci + 1]
            v4 = verts[(ri + 1) * sc + ci]
            bm.faces.new([v1, v2, v3, v4])

    # UV unwrap - project from top
    uv_layer = bm.loops.layers.uv.new("TerrainUV")
    for face in bm.faces:
        for loop in face.loops:
            u = loop.vert.co.x / terrain_width_bu
            v = loop.vert.co.y / terrain_height_bu
            loop[uv_layer].uv = (u, v)

    mesh = bpy.data.meshes.new("RealTerrain_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    terrain_obj = bpy.data.objects.new("RealTerrain", mesh)
    terrain_col.objects.link(terrain_obj)

    # Smooth shading
    for poly in terrain_obj.data.polygons:
        poly.use_smooth = True

    # Add subdivision surface for smoothness
    subsurf = terrain_obj.modifiers.new("Subsurf", 'SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    return terrain_obj, terrain_width_bu, terrain_height_bu, m_per_bu, elev_range_bu


def create_terrain_material(terrain_obj):
    """Create PBR material with satellite texture, heightmap-based coloring, and detail."""
    mat = bpy.data.materials.new("RealTerrain_PBR")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear defaults
    for n in nodes:
        nodes.remove(n)

    # Output
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (1200, 0)

    # Principled BSDF
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (800, 0)
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # === Satellite texture ===
    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-800, 200)

    # Terrain texture image
    tex_path = os.path.join(GISDIR, "fairfield_terrain_texture.png")
    if os.path.exists(tex_path):
        img = bpy.data.images.load(tex_path)
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        tex_node.location = (-400, 300)
        links.new(tex_coord.outputs["UV"], tex_node.inputs["Vector"])

    # === Procedural detail layers ===
    # Noise for grass variation
    noise1 = nodes.new("ShaderNodeTexNoise")
    noise1.location = (-400, 0)
    noise1.inputs["Scale"].default_value = 80.0
    noise1.inputs["Detail"].default_value = 8.0
    noise1.inputs["Roughness"].default_value = 0.6
    links.new(tex_coord.outputs["Object"], noise1.inputs["Vector"])

    # Grass green color ramp
    grass_ramp = nodes.new("ShaderNodeValToRGB")
    grass_ramp.location = (-100, -50)
    grass_ramp.color_ramp.elements[0].position = 0.3
    grass_ramp.color_ramp.elements[0].color = (0.08, 0.18, 0.04, 1)  # Dark grass
    grass_ramp.color_ramp.elements[1].position = 0.7
    grass_ramp.color_ramp.elements[1].color = (0.15, 0.35, 0.08, 1)  # Light grass
    links.new(noise1.outputs["Fac"], grass_ramp.inputs["Fac"])

    # === Height-based coloring ===
    # Separate Z for altitude-based blending
    sep_xyz = nodes.new("ShaderNodeSeparateXYZ")
    sep_xyz.location = (-600, -200)
    links.new(tex_coord.outputs["Object"], sep_xyz.inputs["Vector"])

    # Map altitude to 0-1
    map_range = nodes.new("ShaderNodeMapRange")
    map_range.location = (-400, -250)
    map_range.inputs["From Min"].default_value = 0.0
    map_range.inputs["From Max"].default_value = 7.0  # elev_range_bu approx
    links.new(sep_xyz.outputs["Z"], map_range.inputs["Value"])

    # Altitude color ramp: valley green -> bracken -> fell grey -> heather purple
    alt_ramp = nodes.new("ShaderNodeValToRGB")
    alt_ramp.location = (-100, -250)
    elems = alt_ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = (0.12, 0.25, 0.06, 1)   # Valley: lush green
    elems[1].position = 0.35
    elems[1].color = (0.2, 0.3, 0.08, 1)     # Lower fell: bracken
    e2 = alt_ramp.color_ramp.elements.new(0.6)
    e2.color = (0.35, 0.18, 0.35, 1)          # Mid fell: heather purple
    e3 = alt_ramp.color_ramp.elements.new(0.85)
    e3.color = (0.4, 0.38, 0.35, 1)           # Upper fell: grey scree
    links.new(map_range.outputs["Result"], alt_ramp.inputs["Fac"])

    # === Mix satellite with procedural ===
    # Mix grass noise with altitude colors
    mix_proc = nodes.new("ShaderNodeMixRGB")
    mix_proc.location = (200, -100)
    mix_proc.blend_type = 'MIX'
    mix_proc.inputs["Fac"].default_value = 0.5
    links.new(grass_ramp.outputs["Color"], mix_proc.inputs["Color1"])
    links.new(alt_ramp.outputs["Color"], mix_proc.inputs["Color2"])

    if os.path.exists(tex_path):
        # Mix satellite texture with procedural
        mix_final = nodes.new("ShaderNodeMixRGB")
        mix_final.location = (450, 100)
        mix_final.blend_type = 'MULTIPLY'
        mix_final.inputs["Fac"].default_value = 0.6
        links.new(tex_node.outputs["Color"], mix_final.inputs["Color1"])
        links.new(mix_proc.outputs["Color"], mix_final.inputs["Color2"])

        # Brighten the multiply blend
        brighten = nodes.new("ShaderNodeMixRGB")
        brighten.location = (650, 100)
        brighten.blend_type = 'ADD'
        brighten.inputs["Fac"].default_value = 0.3
        links.new(mix_final.outputs["Color"], brighten.inputs["Color1"])
        links.new(mix_proc.outputs["Color"], brighten.inputs["Color2"])

        links.new(brighten.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        links.new(mix_proc.outputs["Color"], bsdf.inputs["Base Color"])

    # === Bump from noise for micro detail ===
    bump_noise = nodes.new("ShaderNodeTexNoise")
    bump_noise.location = (200, -400)
    bump_noise.inputs["Scale"].default_value = 200.0
    bump_noise.inputs["Detail"].default_value = 6.0
    links.new(tex_coord.outputs["Object"], bump_noise.inputs["Vector"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (500, -400)
    bump.inputs["Strength"].default_value = 0.15
    links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    terrain_obj.data.materials.append(mat)
    return mat


def create_garden_ground(golf_center, garden_size, terrain_col, ground_z):
    """Create a flat garden ground plane where the golf course sits."""
    bm = bmesh.new()

    hw = garden_size[0] / 2
    hh = garden_size[1] / 2
    cx, cy = golf_center

    # Slightly larger than golf bounds with soft edges
    verts = [
        bm.verts.new((cx - hw - 2, cy - hh - 2, ground_z - 0.05)),
        bm.verts.new((cx + hw + 2, cy - hh - 2, ground_z - 0.05)),
        bm.verts.new((cx + hw + 2, cy + hh + 2, ground_z - 0.05)),
        bm.verts.new((cx - hw - 2, cy + hh + 2, ground_z - 0.05)),
    ]
    bm.faces.new(verts)

    # UV
    uv_layer = bm.loops.layers.uv.new("GardenUV")
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = (
                (loop.vert.co.x - (cx - hw - 2)) / (garden_size[0] + 4),
                (loop.vert.co.y - (cy - hh - 2)) / (garden_size[1] + 4)
            )

    mesh = bpy.data.meshes.new("GardenGround_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("GardenGround", mesh)
    terrain_col.objects.link(obj)

    # Rich lawn material
    mat = bpy.data.materials.new("GardenLawn_PBR")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    lnk = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (800, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (500, 0)
    bsdf.inputs["Roughness"].default_value = 0.95
    lnk.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # Grass noise
    tc = nodes.new("ShaderNodeTexCoord")
    tc.location = (-600, 0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-300, 100)
    noise.inputs["Scale"].default_value = 150.0
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 0.7
    lnk.new(tc.outputs["Object"], noise.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (0, 100)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.05, 0.15, 0.02, 1)  # Dark lawn
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = (0.1, 0.3, 0.04, 1)    # Bright lawn
    lnk.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    lnk.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # Grass bump
    bn = nodes.new("ShaderNodeTexNoise")
    bn.location = (-300, -200)
    bn.inputs["Scale"].default_value = 400.0
    bn.inputs["Detail"].default_value = 8.0
    lnk.new(tc.outputs["Object"], bn.inputs["Vector"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (200, -200)
    bump.inputs["Strength"].default_value = 0.3
    lnk.new(bn.outputs["Fac"], bump.inputs["Height"])
    lnk.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    obj.data.materials.append(mat)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj


def create_garden_boundary(golf_center, garden_size, terrain_col, ground_z):
    """Create stone wall boundary around the garden (Cumbrian dry stone wall)."""
    cx, cy = golf_center
    hw = garden_size[0] / 2 + 1.5
    hh = garden_size[1] / 2 + 1.5

    wall_mat = bpy.data.materials.new("DryStoneWall_Mat")
    wall_mat.use_nodes = True
    nodes = wall_mat.node_tree.nodes
    lnk = wall_mat.node_tree.links
    for n in nodes:
        nodes.remove(n)

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value = 0.9
    lnk.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    tc.location = (-400, 0)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-100, 0)
    noise.inputs["Scale"].default_value = 30.0
    noise.inputs["Detail"].default_value = 5.0
    lnk.new(tc.outputs["Object"], noise.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (100, 0)
    ramp.color_ramp.elements[0].color = (0.3, 0.28, 0.25, 1)  # Dark stone
    ramp.color_ramp.elements[1].color = (0.5, 0.48, 0.45, 1)  # Light stone
    lnk.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    lnk.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (100, -200)
    bump.inputs["Strength"].default_value = 0.5
    lnk.new(noise.outputs["Fac"], bump.inputs["Height"])
    lnk.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Wall segments (4 sides)
    wall_h = 0.15  # Low wall height
    wall_w = 0.08  # Wall thickness

    segments = [
        # (start_x, start_y, end_x, end_y)
        (cx - hw, cy - hh, cx + hw, cy - hh),  # South
        (cx + hw, cy - hh, cx + hw, cy + hh),  # East
        (cx + hw, cy + hh, cx - hw, cy + hh),  # North
        (cx - hw, cy + hh, cx - hw, cy - hh),  # West
    ]

    for i, (x1, y1, x2, y2) in enumerate(segments):
        length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        angle = math.atan2(y2 - y1, x2 - x1)

        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= length
            v.co.y *= wall_w
            v.co.z *= wall_h
        mesh_data = bpy.data.meshes.new(f"Wall_{i}_Mesh")
        bm.to_mesh(mesh_data)
        bm.free()

        wall = bpy.data.objects.new(f"GardenWall_{i}", mesh_data)
        wall.location = (mx, my, ground_z + wall_h / 2)
        wall.rotation_euler.z = angle
        wall.data.materials.append(wall_mat)
        terrain_col.objects.link(wall)

    # Gate opening (gap in south wall) - just visual, skip one segment section


def add_trees_around_garden(golf_center, garden_size, terrain_col, ground_z):
    """Add trees (oaks, birches) around the garden perimeter."""
    cx, cy = golf_center
    hw = garden_size[0] / 2 + 3
    hh = garden_size[1] / 2 + 3

    # Tree trunk material
    bark_mat = bpy.data.materials.new("OakBark_Mat")
    bark_mat.use_nodes = True
    bsdf = bark_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.15, 0.1, 0.06, 1)
    bsdf.inputs["Roughness"].default_value = 0.95

    # Canopy material
    canopy_mat = bpy.data.materials.new("TreeCanopy_Mat")
    canopy_mat.use_nodes = True
    nodes = canopy_mat.node_tree.nodes
    lnk = canopy_mat.node_tree.links
    for n in nodes:
        nodes.remove(n)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (600, 0)
    bsdf_c = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_c.location = (300, 0)
    bsdf_c.inputs["Roughness"].default_value = 0.85
    lnk.new(bsdf_c.outputs["BSDF"], output.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    tc.location = (-400, 0)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-100, 0)
    noise.inputs["Scale"].default_value = 25.0
    noise.inputs["Detail"].default_value = 6.0
    lnk.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (100, 0)
    ramp.color_ramp.elements[0].color = (0.04, 0.12, 0.02, 1)
    ramp.color_ramp.elements[1].color = (0.08, 0.22, 0.04, 1)
    lnk.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    lnk.new(ramp.outputs["Color"], bsdf_c.inputs["Base Color"])

    # Tree positions around garden
    positions = [
        (cx - hw, cy - hh + 3), (cx - hw, cy), (cx - hw, cy + hh - 3),
        (cx + hw, cy - hh + 3), (cx + hw, cy), (cx + hw, cy + hh - 3),
        (cx - hw + 3, cy + hh), (cx, cy + hh), (cx + hw - 3, cy + hh),
        (cx - hw + 3, cy - hh), (cx, cy - hh), (cx + hw - 3, cy - hh),
    ]

    import random
    random.seed(42)

    for i, (tx, ty) in enumerate(positions):
        # Randomize slightly
        tx += random.uniform(-1, 1)
        ty += random.uniform(-1, 1)
        trunk_h = random.uniform(0.4, 0.7)
        canopy_r = random.uniform(0.3, 0.6)

        # Trunk
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, segments=8, radius1=0.05, radius2=0.03, depth=trunk_h)
        mesh = bpy.data.meshes.new(f"TreeTrunk_{i}_Mesh")
        bm.to_mesh(mesh)
        bm.free()
        trunk = bpy.data.objects.new(f"Tree_{i}_Trunk", mesh)
        trunk.location = (tx, ty, ground_z + trunk_h / 2)
        trunk.data.materials.append(bark_mat)
        terrain_col.objects.link(trunk)

        # Canopy (sphere)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=canopy_r)
        for v in bm.verts:
            v.co.z *= 0.7  # Slightly flattened
        mesh = bpy.data.meshes.new(f"TreeCanopy_{i}_Mesh")
        bm.to_mesh(mesh)
        bm.free()
        canopy = bpy.data.objects.new(f"Tree_{i}_Canopy", mesh)
        canopy.location = (tx, ty, ground_z + trunk_h + canopy_r * 0.4)
        canopy.data.materials.append(canopy_mat)
        terrain_col.objects.link(canopy)


def create_fairfield_house(golf_center, terrain_col, ground_z):
    """Create a representation of Fairfield house - large detached Lake District house."""
    cx, cy = golf_center
    # House to the side of the garden (north-east corner)
    hx = cx + 7.0
    hy = cy + 10.0

    # Whitewashed walls
    wall_mat = bpy.data.materials.new("Fairfield_Walls")
    wall_mat.use_nodes = True
    bsdf = wall_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.92, 0.9, 0.85, 1)
    bsdf.inputs["Roughness"].default_value = 0.88

    # Slate roof
    roof_mat = bpy.data.materials.new("Fairfield_SlateRoof")
    roof_mat.use_nodes = True
    bsdf_r = roof_mat.node_tree.nodes["Principled BSDF"]
    bsdf_r.inputs["Base Color"].default_value = (0.25, 0.27, 0.32, 1)
    bsdf_r.inputs["Roughness"].default_value = 0.7

    # Main house body
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 1.2
        v.co.y *= 0.8
        v.co.z *= 0.5
    mesh = bpy.data.meshes.new("Fairfield_Walls_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    house = bpy.data.objects.new("Fairfield_Walls", mesh)
    house.location = (hx, hy, ground_z + 0.25)
    house.data.materials.append(wall_mat)
    terrain_col.objects.link(house)

    # Roof (cone/prism shape)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=4, radius1=0.9, radius2=0.0, depth=0.4)
    mesh = bpy.data.meshes.new("Fairfield_Roof_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    roof = bpy.data.objects.new("Fairfield_Roof", mesh)
    roof.location = (hx, hy, ground_z + 0.55)
    roof.rotation_euler.z = math.radians(45)
    roof.scale = (1.35, 0.9, 1.0)
    roof.data.materials.append(roof_mat)
    terrain_col.objects.link(roof)

    # Chimney
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.08
        v.co.y *= 0.08
        v.co.z *= 0.25
    mesh = bpy.data.meshes.new("Fairfield_Chimney_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    chimney = bpy.data.objects.new("Fairfield_Chimney", mesh)
    chimney.location = (hx + 0.4, hy, ground_z + 0.8)
    chimney.data.materials.append(wall_mat)
    terrain_col.objects.link(chimney)

    # Windows (dark recesses)
    win_mat = bpy.data.materials.new("Fairfield_Windows")
    win_mat.use_nodes = True
    bsdf_w = win_mat.node_tree.nodes["Principled BSDF"]
    bsdf_w.inputs["Base Color"].default_value = (0.1, 0.12, 0.15, 1)
    bsdf_w.inputs["Roughness"].default_value = 0.3
    bsdf_w.inputs["Specular IOR Level"].default_value = 0.8

    for wi, (wx, wy) in enumerate([(-0.3, 0.41), (0.0, 0.41), (0.3, 0.41), (-0.3, -0.41), (0.3, -0.41)]):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= 0.12
            v.co.y *= 0.01
            v.co.z *= 0.15
        mesh = bpy.data.meshes.new(f"Fairfield_Win_{wi}_Mesh")
        bm.to_mesh(mesh)
        bm.free()
        win = bpy.data.objects.new(f"Fairfield_Window_{wi}", mesh)
        win.location = (hx + wx, hy + wy, ground_z + 0.3)
        win.data.materials.append(win_mat)
        terrain_col.objects.link(win)

    # Front door
    door_mat = bpy.data.materials.new("Fairfield_Door")
    door_mat.use_nodes = True
    bsdf_d = door_mat.node_tree.nodes["Principled BSDF"]
    bsdf_d.inputs["Base Color"].default_value = (0.15, 0.05, 0.02, 1)
    bsdf_d.inputs["Roughness"].default_value = 0.6

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.1
        v.co.y *= 0.01
        v.co.z *= 0.22
    mesh = bpy.data.meshes.new("Fairfield_Door_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    door = bpy.data.objects.new("Fairfield_Door", mesh)
    door.location = (hx, hy + 0.41, ground_z + 0.15)
    door.data.materials.append(door_mat)
    terrain_col.objects.link(door)


def create_driveway(golf_center, terrain_col, ground_z):
    """Create a gravel driveway leading to Fairfield house."""
    cx, cy = golf_center

    gravel_mat = bpy.data.materials.new("Gravel_Mat")
    gravel_mat.use_nodes = True
    nodes = gravel_mat.node_tree.nodes
    lnk = gravel_mat.node_tree.links
    for n in nodes:
        nodes.remove(n)

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value = 0.95
    lnk.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    tc.location = (-400, 0)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-100, 0)
    noise.inputs["Scale"].default_value = 60.0
    noise.inputs["Detail"].default_value = 12.0
    lnk.new(tc.outputs["Object"], noise.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (100, 0)
    ramp.color_ramp.elements[0].color = (0.45, 0.42, 0.38, 1)
    ramp.color_ramp.elements[1].color = (0.6, 0.57, 0.52, 1)
    lnk.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    lnk.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (100, -200)
    bump.inputs["Strength"].default_value = 0.6
    lnk.new(noise.outputs["Fac"], bump.inputs["Height"])
    lnk.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Driveway path
    bm = bmesh.new()
    verts = [
        bm.verts.new((cx + 7, cy + 8, ground_z + 0.01)),
        bm.verts.new((cx + 8.5, cy + 8, ground_z + 0.01)),
        bm.verts.new((cx + 8.5, cy - 5, ground_z + 0.01)),
        bm.verts.new((cx + 7, cy - 5, ground_z + 0.01)),
    ]
    bm.faces.new(verts)
    mesh = bpy.data.meshes.new("Driveway_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    drive = bpy.data.objects.new("Driveway", mesh)
    drive.data.materials.append(gravel_mat)
    terrain_col.objects.link(drive)


def position_golf_on_terrain(meta, terrain_width_bu, terrain_height_bu, m_per_bu, elev_range_bu):
    """Move all existing golf course objects to sit on the terrain at Fairfield's location."""
    # Golf course currently at X=0-9, Y=0-16
    # Fairfield is at the center of the terrain (golf_x_norm=0.5, golf_y_norm=0.5)

    # Golf position on terrain
    golf_terrain_x = meta["golf_x_norm"] * terrain_width_bu
    golf_terrain_y = meta["golf_y_norm"] * terrain_height_bu

    # Fairfield elevation: 49m. Elev min: 19m. Range: 123m.
    # In BU: (49-19)/123 * elev_range_bu
    fairfield_z = ((meta["fairfield_elev"] - meta["elev_min"]) / max(1, meta["elev_range"])) * elev_range_bu

    # Current golf center
    golf_cx = 4.5  # midpoint of X=0-9
    golf_cy = 8.0  # midpoint of Y=0-16

    # Offset to move golf to terrain position
    dx = golf_terrain_x - golf_cx
    dy = golf_terrain_y - golf_cy
    dz = fairfield_z  # Golf Z currently around 0, move up to terrain elevation

    # Move all existing objects that aren't in the Terrain collection
    terrain_names = {"RealTerrain", "GardenGround", "GardenWall", "Driveway",
                     "Fairfield_", "Tree_"}

    moved = 0
    for obj in bpy.data.objects:
        # Skip terrain objects (by checking if in Terrain collection)
        is_terrain = False
        for col in obj.users_collection:
            if "Terrain" in col.name:
                is_terrain = True
                break
        if is_terrain:
            continue

        obj.location.x += dx
        obj.location.y += dy
        obj.location.z += dz
        moved += 1

    return dx, dy, dz, moved, golf_terrain_x, golf_terrain_y, fairfield_z


def setup_terrain_lighting():
    """Set up sun light for Lake District atmosphere."""
    # Remove existing sun lights
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT' and 'Sun' in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Add warm afternoon sun (NW England, late summer)
    sun_data = bpy.data.lights.new("TerrainSun", 'SUN')
    sun_data.energy = 4.0
    sun_data.color = (1.0, 0.95, 0.85)  # Warm golden
    sun_data.angle = 0.03  # Soft shadows

    sun_obj = bpy.data.objects.new("TerrainSun", sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(55), math.radians(15), math.radians(-30))

    # World: Lake District sky
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("TerrainWorld")
        bpy.context.scene.world = world

    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for n in nodes:
        nodes.remove(n)

    output = nodes.new("ShaderNodeOutputWorld")
    output.location = (400, 0)

    bg = nodes.new("ShaderNodeBackground")
    bg.location = (200, 0)
    bg.inputs["Strength"].default_value = 0.8
    links.new(bg.outputs["Background"], output.inputs["Surface"])

    # Sky gradient
    tc = nodes.new("ShaderNodeTexCoord")
    tc.location = (-400, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-200, 0)
    links.new(tc.outputs["Generated"], mapping.inputs["Vector"])

    gradient = nodes.new("ShaderNodeTexGradient")
    gradient.location = (-50, 0)
    links.new(mapping.outputs["Vector"], gradient.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (50, 0)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.55, 0.65, 0.8, 1)  # Horizon: pale blue
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = (0.35, 0.5, 0.75, 1)  # Zenith: deeper blue
    # Add hint of clouds
    e2 = ramp.color_ramp.elements.new(0.3)
    e2.color = (0.7, 0.75, 0.82, 1)  # Wisps of cloud

    links.new(gradient.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bg.inputs["Color"])


def setup_overview_camera(golf_center, terrain_width_bu, terrain_height_bu, fairfield_z):
    """Set up a camera looking down at the golf course on the terrain."""
    cx, cy = golf_center

    cam_data = bpy.data.cameras.new("TerrainCam")
    cam_data.lens = 35
    cam_data.clip_end = 500

    cam_obj = bpy.data.objects.new("TerrainCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    # Elevated view looking down at golf course
    cam_obj.location = (cx - 15, cy - 20, fairfield_z + 18)

    # Point at golf center
    direction = Vector((cx, cy, fairfield_z)) - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    bpy.context.scene.camera = cam_obj


if __name__ == "__main__":
    import sys
    sys.path = [p for p in sys.path if 'python3.14' not in p]

    print("=== Emplacing Mini Golf at Fairfield, Eskdale Green ===")

    meta, coords = load_metadata()
    print(f"Terrain: {meta['terrain_width_m']:.0f}m x {meta['terrain_height_m']:.0f}m")
    print(f"Elevation: {meta['elev_min']}-{meta['elev_max']}m (range: {meta['elev_range']}m)")
    print(f"Fairfield elevation: {meta['fairfield_elev']}m")

    # Load DEM
    dem = np.load(os.path.join(GISDIR, "fairfield_dem.npy"))
    print(f"DEM loaded: {dem.shape}")

    # Create terrain collection
    terrain_col = get_or_create_collection("RealTerrain")

    # 1. Create terrain mesh from DEM
    print("\n--- Creating terrain mesh ---")
    terrain_obj, tw, th, m_per_bu, erbu = create_terrain_mesh(dem, meta, terrain_col)
    print(f"Terrain: {tw:.1f} x {th:.1f} BU (1 BU = {m_per_bu:.1f}m)")

    # 2. Apply rich PBR terrain material
    print("\n--- Applying terrain material ---")
    create_terrain_material(terrain_obj)

    # 3. Position golf course on terrain
    print("\n--- Positioning golf course ---")
    dx, dy, dz, moved, gcx, gcy, gz = position_golf_on_terrain(meta, tw, th, m_per_bu, erbu)
    print(f"Moved {moved} objects by ({dx:.1f}, {dy:.1f}, {dz:.1f})")
    print(f"Golf center now at ({gcx:.1f}, {gcy:.1f}, {gz:.1f})")

    # 4. Create garden ground
    print("\n--- Creating garden ---")
    garden_size = (13, 20)  # Slightly larger than golf course
    create_garden_ground((gcx, gcy), garden_size, terrain_col, gz)

    # 5. Garden boundary walls
    create_garden_boundary((gcx, gcy), garden_size, terrain_col, gz)

    # 6. Trees around garden
    print("\n--- Adding trees ---")
    add_trees_around_garden((gcx, gcy), garden_size, terrain_col, gz)

    # 7. Fairfield house
    print("\n--- Building Fairfield house ---")
    create_fairfield_house((gcx, gcy), terrain_col, gz)

    # 8. Driveway
    create_driveway((gcx, gcy), terrain_col, gz)

    # 9. Lighting
    print("\n--- Setting up lighting ---")
    setup_terrain_lighting()

    # 10. Camera
    setup_overview_camera((gcx, gcy), tw, th, gz)

    # Save
    bpy.ops.wm.save_mainfile()

    print(f"\n=== Terrain emplacement complete ===")
    print(f"Objects: {len(bpy.data.objects)}")
    print(f"Materials: {len(bpy.data.materials)}")
    print(f"Collections: {len(bpy.data.collections)}")
