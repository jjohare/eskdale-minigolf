"""Reposition and rescale golf course: correct scale, 100m downhill of Randlehow, cut into hillside."""
import bpy
import bmesh
import math
import json
import os
import numpy as np
from mathutils import Vector, Matrix, Euler

GISDIR = "/home/devuser/workspace/minigolf/gis_data"


def load_meta():
    with open(os.path.join(GISDIR, "fairfield_blender_meta.json")) as f:
        meta = json.load(f)
    return meta


def get_terrain_params(meta):
    terrain_w_bu = 50.0
    terrain_h_bu = terrain_w_bu * (meta["terrain_height_m"] / meta["terrain_width_m"])
    m_per_bu = meta["terrain_width_m"] / terrain_w_bu  # 18 m/BU
    elev_range_bu = meta["elev_range"] / m_per_bu
    return terrain_w_bu, terrain_h_bu, m_per_bu, elev_range_bu


def collect_golf_objects():
    """Get all objects that are part of the golf course (not terrain infrastructure)."""
    terrain_collection_names = {"RealTerrain"}
    golf_objs = []
    for obj in bpy.data.objects:
        # Skip terrain objects
        is_terrain = False
        for col in obj.users_collection:
            if col.name in terrain_collection_names:
                is_terrain = True
                break
        # Skip terrain-specific objects by name
        terrain_names = ["RealTerrain", "GardenGround", "GardenWall_", "Driveway",
                         "Fairfield_", "Tree_", "TerrainSun", "TerrainCamera",
                         "TerrainTracker"]
        for tn in terrain_names:
            if obj.name.startswith(tn):
                is_terrain = True
                break
        if obj.name == "TerrainWorld":
            is_terrain = True

        if not is_terrain and obj.type in ('MESH', 'LIGHT', 'EMPTY', 'CAMERA'):
            golf_objs.append(obj)
    return golf_objs


def remove_old_terrain_furniture():
    """Remove old garden ground, walls, trees, house, driveway (will be rebuilt at new position)."""
    to_remove = []
    for obj in bpy.data.objects:
        for prefix in ["GardenGround", "GardenWall_", "Driveway", "Fairfield_", "Tree_"]:
            if obj.name.startswith(prefix):
                to_remove.append(obj)
                break
    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)
    print(f"Removed {len(to_remove)} old terrain furniture objects")


def rescale_and_reposition_golf(golf_objs, meta, target_center, target_z, rotation_z):
    """Undo previous positioning, rescale to real-world size, reposition and rotate."""
    tw, th, m_per_bu, erbu = get_terrain_params(meta)

    # The previous script moved golf by (20.5, 34.9, 1.7)
    # Original golf was at X=0-9.05, Y=0-16, Z=-2.75 to 0.74
    # Current golf center is at approximately (25, 43, 1.7)
    # First undo the old move to get back to original positions
    old_dx, old_dy, old_dz = 20.5, 34.9, 1.7

    # Original golf center
    orig_cx = 4.525  # midpoint of 0-9.05
    orig_cy = 8.0    # midpoint of 0-16

    # Scale factor: current golf is ~9x16 BU, needs to be ~2.2x3.3 BU
    scale = 40.0 / (9.05 * m_per_bu)  # 40m / (9.05 * 18m) = 0.2456

    target_cx, target_cy = target_center

    for obj in golf_objs:
        # Step 1: Undo old translation
        obj.location.x -= old_dx
        obj.location.y -= old_dy
        obj.location.z -= old_dz

        # Step 2: Scale relative to original golf center
        rx = obj.location.x - orig_cx
        ry = obj.location.y - orig_cy
        rz = obj.location.z  # Z relative to ground (0)

        obj.location.x = orig_cx + rx * scale
        obj.location.y = orig_cy + ry * scale
        obj.location.z = rz * scale

        # Scale the object itself
        obj.scale *= scale

        # Step 3: Rotate around the scaled golf center
        # New golf center after scale
        scaled_cx = orig_cx  # center stays at same point
        scaled_cy = orig_cy

        cos_r = math.cos(rotation_z)
        sin_r = math.sin(rotation_z)
        dx = obj.location.x - scaled_cx
        dy = obj.location.y - scaled_cy
        obj.location.x = scaled_cx + dx * cos_r - dy * sin_r
        obj.location.y = scaled_cy + dx * sin_r + dy * cos_r

        # Add rotation to object
        obj.rotation_euler.z += rotation_z

        # Step 4: Translate to target position
        obj.location.x += (target_cx - scaled_cx)
        obj.location.y += (target_cy - scaled_cy)
        obj.location.z += target_z

    return scale


def cut_terrain_for_golf(target_center, target_z, golf_radius_bu, meta):
    """Depress the terrain mesh at the golf location to create a cut-in shelf."""
    tw, th, m_per_bu, erbu = get_terrain_params(meta)

    terrain_obj = bpy.data.objects.get("RealTerrain")
    if not terrain_obj:
        print("No RealTerrain object found")
        return

    # Get the mesh in edit mode
    bm = bmesh.new()
    bm.from_mesh(terrain_obj.data)
    bm.verts.ensure_lookup_table()

    cx, cy = target_center
    rx = golf_radius_bu * 1.3  # slightly larger than golf extents
    ry = golf_radius_bu * 1.8

    modified = 0
    for vert in bm.verts:
        # World position (terrain is at origin)
        wx = vert.co.x
        wy = vert.co.y
        wz = vert.co.z

        # Distance from golf center (elliptical)
        dx = (wx - cx) / rx
        dy = (wy - cy) / ry
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 1.0:
            # Inside the golf area: flatten to target_z with gentle blend
            if dist < 0.7:
                # Inner area: flat at target_z
                blend = 1.0
            else:
                # Transition zone: smooth blend from terrain to flat
                blend = 1.0 - ((dist - 0.7) / 0.3)
                blend = blend * blend * (3 - 2 * blend)  # smoothstep

            new_z = wz * (1.0 - blend) + target_z * blend
            if new_z != wz:
                vert.co.z = new_z
                modified += 1

    bm.to_mesh(terrain_obj.data)
    bm.free()
    terrain_obj.data.update()
    print(f"Modified {modified} terrain vertices for golf cut-in")


def create_retaining_walls(target_center, target_z, golf_half_w, golf_half_h, rotation_z, meta):
    """Create stone retaining walls where the golf course cuts into the hillside."""
    tw, th, m_per_bu, erbu = get_terrain_params(meta)

    terrain_col = bpy.data.collections.get("RealTerrain")
    if not terrain_col:
        return

    # Retaining wall material - Cumbrian slate/stone
    wall_mat = bpy.data.materials.get("RetainingWall_Mat")
    if not wall_mat:
        wall_mat = bpy.data.materials.new("RetainingWall_Mat")
        wall_mat.use_nodes = True
        nodes = wall_mat.node_tree.nodes
        links = wall_mat.node_tree.links
        for n in nodes:
            nodes.remove(n)

        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (300, 0)
        bsdf.inputs["Roughness"].default_value = 0.92
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        tc = nodes.new("ShaderNodeTexCoord")
        tc.location = (-400, 0)
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-100, 0)
        noise.inputs["Scale"].default_value = 40.0
        noise.inputs["Detail"].default_value = 8.0
        links.new(tc.outputs["Object"], noise.inputs["Vector"])

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (100, 0)
        ramp.color_ramp.elements[0].color = (0.25, 0.24, 0.22, 1)
        ramp.color_ramp.elements[1].color = (0.42, 0.40, 0.36, 1)
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        bump_node = nodes.new("ShaderNodeBump")
        bump_node.location = (100, -200)
        bump_node.inputs["Strength"].default_value = 0.7
        links.new(noise.outputs["Fac"], bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])

    cx, cy = target_center
    cos_r = math.cos(rotation_z)
    sin_r = math.sin(rotation_z)

    # Wall on the uphill side (NE) - this is where the cut is deepest
    # The uphill side in our rotated frame is the +X, +Y side
    wall_height = 0.15  # ~2.7m real
    wall_thickness = 0.03

    # Create walls along NE and E sides (uphill)
    wall_segments = [
        # local coords relative to golf center: (start_lx, start_ly, end_lx, end_ly)
        (-golf_half_w, golf_half_h, golf_half_w, golf_half_h),   # North side
        (golf_half_w, -golf_half_h, golf_half_w, golf_half_h),   # East side
        (-golf_half_w, -golf_half_h * 0.3, -golf_half_w, golf_half_h),  # West upper
    ]

    for i, (lx1, ly1, lx2, ly2) in enumerate(wall_segments):
        # Rotate local coords to world
        wx1 = cx + lx1 * cos_r - ly1 * sin_r
        wy1 = cy + lx1 * sin_r + ly1 * cos_r
        wx2 = cx + lx2 * cos_r - ly2 * sin_r
        wy2 = cy + lx2 * sin_r + ly2 * cos_r

        length = math.sqrt((wx2-wx1)**2 + (wy2-wy1)**2)
        mid_x = (wx1 + wx2) / 2
        mid_y = (wy1 + wy2) / 2
        angle = math.atan2(wy2-wy1, wx2-wx1)

        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= length
            v.co.y *= wall_thickness
            v.co.z *= wall_height
        mesh = bpy.data.meshes.new(f"RetainWall_{i}_Mesh")
        bm.to_mesh(mesh)
        bm.free()

        wall = bpy.data.objects.new(f"RetainingWall_{i}", mesh)
        wall.location = (mid_x, mid_y, target_z + wall_height / 2)
        wall.rotation_euler.z = angle
        wall.data.materials.append(wall_mat)
        terrain_col.objects.link(wall)

    print(f"Created {len(wall_segments)} retaining wall segments")


def create_access_path(target_center, target_z, rotation_z, meta):
    """Create a gravel path leading down from Randlehow to the golf course."""
    tw, th, m_per_bu, erbu = get_terrain_params(meta)
    terrain_col = bpy.data.collections.get("RealTerrain")
    if not terrain_col:
        return

    path_mat = bpy.data.materials.get("GravelPath_Mat")
    if not path_mat:
        path_mat = bpy.data.materials.new("GravelPath_Mat")
        path_mat.use_nodes = True
        nodes = path_mat.node_tree.nodes
        links = path_mat.node_tree.links
        for n in nodes:
            nodes.remove(n)

        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (300, 0)
        bsdf.inputs["Roughness"].default_value = 0.95
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        tc = nodes.new("ShaderNodeTexCoord")
        tc.location = (-400, 0)
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-100, 0)
        noise.inputs["Scale"].default_value = 80.0
        noise.inputs["Detail"].default_value = 12.0
        links.new(tc.outputs["Object"], noise.inputs["Vector"])

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (100, 0)
        ramp.color_ramp.elements[0].color = (0.42, 0.39, 0.34, 1)
        ramp.color_ramp.elements[1].color = (0.55, 0.52, 0.46, 1)
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        bump_node = nodes.new("ShaderNodeBump")
        bump_node.location = (100, -200)
        bump_node.inputs["Strength"].default_value = 0.5
        links.new(noise.outputs["Fac"], bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])

    cx, cy = target_center
    # Randlehow is at (25.0, 42.95)
    randlehow_x, randlehow_y = 25.0, tw * (meta["terrain_height_m"] / meta["terrain_width_m"]) / 2
    randlehow_z = ((meta["fairfield_elev"] - meta["elev_min"]) / max(1, meta["elev_range"])) * erbu

    # Path from Randlehow to golf course entrance
    path_width = 0.06  # ~1m real
    bm_path = bmesh.new()

    # Path points from Randlehow down to golf
    points = [
        (randlehow_x, randlehow_y, randlehow_z + 0.01),
        ((randlehow_x + cx) * 0.7 + cx * 0.3, (randlehow_y + cy) * 0.7 + cy * 0.3,
         (randlehow_z + target_z) * 0.5 + 0.01),
        (cx + 0.5, cy - 0.3, target_z + 0.01),
    ]

    # Create path as a series of quads
    for j in range(len(points) - 1):
        x1, y1, z1 = points[j]
        x2, y2, z2 = points[j + 1]
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        # Perpendicular
        px = -dy / length * path_width
        py = dx / length * path_width

        v1 = bm_path.verts.new((x1 + px, y1 + py, z1))
        v2 = bm_path.verts.new((x1 - px, y1 - py, z1))
        v3 = bm_path.verts.new((x2 - px, y2 - py, z2))
        v4 = bm_path.verts.new((x2 + px, y2 + py, z2))
        bm_path.faces.new([v1, v2, v3, v4])

    mesh = bpy.data.meshes.new("AccessPath_Mesh")
    bm_path.to_mesh(mesh)
    bm_path.free()

    path_obj = bpy.data.objects.new("AccessPath", mesh)
    path_obj.data.materials.append(path_mat)
    terrain_col.objects.link(path_obj)
    print("Access path from Randlehow created")


def update_camera(target_center, target_z, meta):
    """Reposition camera for the new golf location."""
    tw, th, m_per_bu, erbu = get_terrain_params(meta)
    cx, cy = target_center

    cam = bpy.data.objects.get("TerrainCamera")
    if cam:
        cam.animation_data_clear()
        cam.location = (cx - 8, cy - 10, target_z + 8)
        direction = Vector((cx, cy, target_z)) - cam.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot_quat.to_euler()
        cam.data.lens = 32

        # Remove constraint
        for c in cam.constraints:
            cam.constraints.remove(c)

    tracker = bpy.data.objects.get("TerrainTracker")
    if tracker:
        tracker.animation_data_clear()
        tracker.location = (cx, cy, target_z)


if __name__ == "__main__":
    import sys
    sys.path = [p for p in sys.path if 'python3.14' not in p]

    print("=== Repositioning Golf Course: 100m Downhill of Randlehow ===")

    meta = load_meta()
    tw, th, m_per_bu, erbu = get_terrain_params(meta)

    # Load DEM for elevation lookup
    dem = np.load(os.path.join(GISDIR, "fairfield_dem.npy"))

    # Target position: 100m SW of Randlehow
    randlehow_x = 25.0
    randlehow_y = th / 2  # ~42.95

    # 100m SW: direction 225 degrees from north
    offset_m = 100
    angle_from_north = 225  # SW
    dx_m = offset_m * math.sin(math.radians(angle_from_north))  # -70.7m
    dy_m = offset_m * math.cos(math.radians(angle_from_north))  # -70.7m

    target_cx = randlehow_x + dx_m / m_per_bu
    target_cy = randlehow_y + dy_m / m_per_bu

    # Get elevation at target from DEM
    dem_row = int((1.0 - target_cy / th) * (dem.shape[0] - 1))
    dem_col = int((target_cx / tw) * (dem.shape[1] - 1))
    dem_row = max(0, min(dem.shape[0]-1, dem_row))
    dem_col = max(0, min(dem.shape[1]-1, dem_col))
    target_elev = float(dem[dem_row, dem_col])
    target_z = ((target_elev - meta["elev_min"]) / max(1, meta["elev_range"])) * erbu

    print(f"Randlehow: ({randlehow_x:.1f}, {randlehow_y:.1f}) BU, elev {meta['fairfield_elev']}m")
    print(f"Target: ({target_cx:.2f}, {target_cy:.2f}) BU, elev {target_elev:.0f}m, Z={target_z:.2f} BU")
    print(f"Scale: 1 BU = {m_per_bu:.1f}m")

    # Rotation: align course NW-SE along contours (~45 degrees from X axis)
    rotation_z = math.radians(45)

    # Step 1: Remove old terrain furniture
    print("\n--- Removing old garden objects ---")
    remove_old_terrain_furniture()

    # Step 2: Collect golf objects
    golf_objs = collect_golf_objects()
    print(f"\n--- Rescaling and repositioning {len(golf_objs)} golf objects ---")

    # Step 3: Rescale and reposition
    scale = rescale_and_reposition_golf(
        golf_objs, meta,
        (target_cx, target_cy), target_z, rotation_z
    )
    print(f"Scale factor: {scale:.4f}")

    # Golf half-extents after scaling
    golf_half_w = 9.05 / 2 * scale  # ~1.11 BU
    golf_half_h = 16.0 / 2 * scale  # ~1.96 BU
    print(f"Golf extents: {golf_half_w*2:.2f} x {golf_half_h*2:.2f} BU = {golf_half_w*2*m_per_bu:.0f}m x {golf_half_h*2*m_per_bu:.0f}m")

    # Step 4: Cut terrain
    print("\n--- Cutting terrain for golf course ---")
    cut_terrain_for_golf((target_cx, target_cy), target_z,
                         max(golf_half_w, golf_half_h), meta)

    # Step 5: Retaining walls
    print("\n--- Building retaining walls ---")
    create_retaining_walls(
        (target_cx, target_cy), target_z,
        golf_half_w * 1.2, golf_half_h * 1.2,
        rotation_z, meta
    )

    # Step 6: Access path
    print("\n--- Creating access path ---")
    create_access_path((target_cx, target_cy), target_z, rotation_z, meta)

    # Step 7: Camera
    print("\n--- Updating camera ---")
    update_camera((target_cx, target_cy), target_z, meta)

    # Save
    bpy.ops.wm.save_mainfile()

    print(f"\n=== Repositioning complete ===")
    print(f"Objects: {len(bpy.data.objects)}")
    print(f"Golf at: ({target_cx:.2f}, {target_cy:.2f}, {target_z:.2f}) BU")
    print(f"Real-world: 100m SW of Randlehow, elev ~{target_elev:.0f}m ASL")
    print(f"Golf size: ~{golf_half_w*2*m_per_bu:.0f}m x {golf_half_h*2*m_per_bu:.0f}m")
    print(f"Rotated {math.degrees(rotation_z):.0f} degrees (NW-SE alignment)")
