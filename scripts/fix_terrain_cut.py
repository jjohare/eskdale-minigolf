"""Fix golf course visibility: aggressively cut terrain to sit below all golf objects.

The terrain has 38809 verts (subsurf applied) but the previous cut was too narrow.
Golf objects range Z=0.30 (holes 8-9) to Z=1.21 (hole 1), and 271 of 384 terrain
verts in the golf bbox are ABOVE the lowest golf objects.

Fix: sloped elliptical cut matching the course's internal slope profile.
"""
import bpy
import bmesh
import math

# ── Golf footprint from scene analysis ──
# Hole 1 (high, SE):  ~(21.7, 37.0, Z=1.1)
# Hole 8-9 (low, NW): ~(20.0, 40.0, Z=0.3)
GOLF_CENTER = (20.85, 38.5)  # Center of golf footprint
GOLF_HIGH = (21.7, 37.0)     # Hole 1 end
GOLF_LOW = (20.0, 40.0)      # Hole 9 end

# Cut zone radii (very generous to cover entire golf bbox + margin)
CUT_RX = 6.5   # X radius (golf spans ~4 BU in X)
CUT_RY = 7.5   # Y radius (golf spans ~5 BU in Y)

# Cut depth: terrain Z will be set to (golf local min Z - CLEARANCE)
CLEARANCE = 0.12  # BU below local golf Z

# Slope parameters - cut Z follows the course slope
CUT_Z_HIGH = 0.90   # Cut Z near hole 1 (golf Z there ~1.1, so 0.2 BU below)
CUT_Z_LOW = 0.10    # Cut Z near hole 9 (golf Z there ~0.3, so 0.2 BU below)


def slope_direction():
    """Unit vector from high end to low end of course."""
    dx = GOLF_LOW[0] - GOLF_HIGH[0]
    dy = GOLF_LOW[1] - GOLF_HIGH[1]
    length = math.sqrt(dx * dx + dy * dy)
    return (dx / length, dy / length, length)


def smoothstep(t):
    """Hermite smoothstep for smooth blend."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def cut_mesh(obj, name="mesh"):
    """Cut terrain/hills mesh in the golf area with sloped target Z."""
    slope_dx, slope_dy, slope_len = slope_direction()
    cx, cy = GOLF_CENTER

    bm_obj = bmesh.new()
    bm_obj.from_mesh(obj.data)
    bm_obj.verts.ensure_lookup_table()

    modified = 0
    for v in bm_obj.verts:
        # Elliptical distance from golf center
        ex = (v.co.x - cx) / CUT_RX
        ey = (v.co.y - cy) / CUT_RY
        dist = math.sqrt(ex * ex + ey * ey)

        if dist >= 1.0:
            continue

        # Slope parameter: project onto high→low direction
        # t=0 at high end (hole 1), t=1 at low end (hole 9)
        px = v.co.x - GOLF_HIGH[0]
        py = v.co.y - GOLF_HIGH[1]
        t_slope = (px * slope_dx + py * slope_dy) / slope_len
        t_slope = max(0.0, min(1.0, t_slope))

        # Target cut Z follows the course slope
        target_z = CUT_Z_HIGH + t_slope * (CUT_Z_LOW - CUT_Z_HIGH)

        # Blend factor: full cut in inner zone, smooth transition at edge
        if dist < 0.55:
            blend = 1.0
        else:
            blend = 1.0 - smoothstep((dist - 0.55) / 0.45)

        # Only cut DOWN, never raise terrain
        new_z = v.co.z * (1.0 - blend) + target_z * blend
        if new_z < v.co.z:
            v.co.z = new_z
            modified += 1

    bm_obj.to_mesh(obj.data)
    bm_obj.free()
    obj.data.update()
    return modified


def rebuild_retaining_walls():
    """Replace old retaining walls with new ones matching the cut."""
    # Remove old walls
    for obj in list(bpy.data.objects):
        if obj.name.startswith("RetainingWall"):
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
    slope_dx, slope_dy, slope_len = slope_direction()

    # Create retaining wall as a ring of short walls around the cut zone
    segments = 32
    wall_thickness = 0.03
    bm_wall = bmesh.new()

    for i in range(segments):
        angle = 2 * math.pi * i / segments
        next_angle = 2 * math.pi * (i + 1) / segments

        # Point on ellipse edge (at dist=0.65 - inside the blend zone)
        x1 = cx + CUT_RX * 0.65 * math.cos(angle)
        y1 = cy + CUT_RY * 0.65 * math.sin(angle)
        x2 = cx + CUT_RX * 0.65 * math.cos(next_angle)
        y2 = cy + CUT_RY * 0.65 * math.sin(next_angle)

        # Wall height: taller where terrain is higher (uphill side)
        # Use slope parameter for height
        t1 = ((x1 - GOLF_HIGH[0]) * slope_dx + (y1 - GOLF_HIGH[1]) * slope_dy) / slope_len
        t1 = max(0.0, min(1.0, t1))
        cut_z1 = CUT_Z_HIGH + t1 * (CUT_Z_LOW - CUT_Z_HIGH)

        t2 = ((x2 - GOLF_HIGH[0]) * slope_dx + (y2 - GOLF_HIGH[1]) * slope_dy) / slope_len
        t2 = max(0.0, min(1.0, t2))
        cut_z2 = CUT_Z_HIGH + t2 * (CUT_Z_LOW - CUT_Z_HIGH)

        # Wall goes from cut_z to cut_z + wall_height
        # Only show wall on uphill sides (where terrain would be higher than cut)
        # Skip walls on downhill side
        wh1 = max(0.02, 0.25 - t1 * 0.2)  # Taller walls at high end
        wh2 = max(0.02, 0.25 - t2 * 0.2)

        # Inner and outer edge
        nx = math.cos(angle)
        ny = math.sin(angle)
        nx2 = math.cos(next_angle)
        ny2 = math.sin(next_angle)

        v1 = bm_wall.verts.new((x1 - nx * wall_thickness, y1 - ny * wall_thickness, cut_z1))
        v2 = bm_wall.verts.new((x1 + nx * wall_thickness, y1 + ny * wall_thickness, cut_z1))
        v3 = bm_wall.verts.new((x1 + nx * wall_thickness, y1 + ny * wall_thickness, cut_z1 + wh1))
        v4 = bm_wall.verts.new((x1 - nx * wall_thickness, y1 - ny * wall_thickness, cut_z1 + wh1))

        v5 = bm_wall.verts.new((x2 - nx2 * wall_thickness, y2 - ny2 * wall_thickness, cut_z2))
        v6 = bm_wall.verts.new((x2 + nx2 * wall_thickness, y2 + ny2 * wall_thickness, cut_z2))
        v7 = bm_wall.verts.new((x2 + nx2 * wall_thickness, y2 + ny2 * wall_thickness, cut_z2 + wh2))
        v8 = bm_wall.verts.new((x2 - nx2 * wall_thickness, y2 - ny2 * wall_thickness, cut_z2 + wh2))

        # Outer face
        bm_wall.faces.new([v2, v6, v7, v3])
        # Inner face
        bm_wall.faces.new([v1, v4, v8, v5])
        # Top face
        bm_wall.faces.new([v4, v3, v7, v8])

    mesh = bpy.data.meshes.new("RetainingWalls_Mesh")
    bm_wall.to_mesh(mesh)
    bm_wall.free()

    wall_obj = bpy.data.objects.new("RetainingWall_Ring", mesh)
    wall_obj.data.materials.append(mat)
    col.objects.link(wall_obj)
    for p in wall_obj.data.polygons:
        p.use_smooth = True

    print(f"Retaining wall: {len(wall_obj.data.polygons)} faces, {segments} segments")


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════
if __name__ == "__main__":
    import sys
    sys.path = [p for p in sys.path if 'python3.14' not in p]

    print("=== Fixing terrain cut for golf visibility ===")

    # 1. Cut terrain
    terrain = bpy.data.objects.get("RealTerrain")
    if terrain:
        ncut = cut_mesh(terrain, "RealTerrain")
        print(f"Terrain: cut {ncut} verts (of {len(terrain.data.vertices)})")
    else:
        print("ERROR: No RealTerrain object found")

    # 2. Cut far hills
    far_hills = bpy.data.objects.get("FarHills")
    if far_hills:
        # Apply subsurf first if present
        for mod in list(far_hills.modifiers):
            if mod.type == 'SUBSURF':
                bpy.context.view_layer.objects.active = far_hills
                bpy.ops.object.modifier_apply(modifier=mod.name)
                print(f"Applied {mod.name} on FarHills: now {len(far_hills.data.vertices)} verts")

        ncut_fh = cut_mesh(far_hills, "FarHills")
        print(f"FarHills: cut {ncut_fh} verts (of {len(far_hills.data.vertices)})")

    # 3. Rebuild retaining walls
    print("\n--- Retaining walls ---")
    rebuild_retaining_walls()

    # 4. Verify
    print("\n--- Verification ---")
    if terrain:
        import bmesh as bm_mod
        bm_v = bm_mod.new()
        bm_v.from_mesh(terrain.data)
        bm_v.verts.ensure_lookup_table()
        golf_tverts = [v.co.z for v in bm_v.verts if 18 <= v.co.x <= 24 and 35 <= v.co.y <= 42]
        bm_v.free()
        if golf_tverts:
            print(f"Terrain Z in golf bbox: {min(golf_tverts):.3f} to {max(golf_tverts):.3f}")
            above_030 = sum(1 for z in golf_tverts if z > 0.30)
            print(f"Terrain verts above Z=0.30: {above_030}/{len(golf_tverts)}")

    # Golf object stats
    skip_pfx = ['RealTerrain', 'FarHills', 'ScatTree', 'TerrainSun', 'TerrainCamera',
                'TerrainTracker', 'RetainingWall', 'AccessPath', 'Camera', 'Sun', 'Light']
    golf_zs = []
    for obj in bpy.data.objects:
        skip = any(obj.name.startswith(p) for p in skip_pfx)
        if not skip and 18 <= obj.location.x <= 24 and 35 <= obj.location.y <= 42:
            golf_zs.append(obj.location.z)
    if golf_zs:
        print(f"Golf Z range (spatial filter): {min(golf_zs):.3f} to {max(golf_zs):.3f}")

    # 5. Save
    bpy.ops.wm.save_mainfile()
    print(f"\nDone. {len(bpy.data.objects)} objects")
