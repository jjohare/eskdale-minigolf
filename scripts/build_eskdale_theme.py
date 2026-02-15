"""
Eskdale Green / West Cumbria themed decorative features for a mini golf course.

Adds culturally authentic Cumbrian landmarks and details:
  1. The Woolpack Inn (miniature pub)
  2. Herdwick Sheep (scattered flock)
  3. La'al Ratty Train (Ravenglass & Eskdale Railway)
  4. Hardknott Roman Fort walls
  5. Sellafield Atom Model
  6. Boot Watermill (with animated wheel)
  7. Muncaster Castle Tower
  8. Dry Stone Walls

All objects are collected under an 'EskdaleTheme' collection with sub-collections.

Run inside Blender:
    exec(open("/home/devuser/workspace/minigolf/scripts/build_eskdale_theme.py").read(),
         {"__name__": "__main__"})
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PI = math.pi


# ===========================================================================
# Helper functions
# ===========================================================================

def get_or_create_material(name, base_color, metallic=0.0, roughness=0.5,
                           emission_strength=0.0):
    """Return existing material or create a Principled BSDF material."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = base_color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission_strength > 0:
            bsdf.inputs["Emission Color"].default_value = base_color
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def ensure_collection(name, parent_name=None):
    """Get or create a collection, optionally parented."""
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
    """Link object exclusively to named collection."""
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


def remove_existing(name):
    """Remove object and orphaned mesh."""
    obj = bpy.data.objects.get(name)
    if obj:
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def add_cube(name, location, scale, material_name, collection_name):
    """Create a cube primitive, position, scale, assign material."""
    remove_existing(name)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if obj.data:
        obj.data.name = name + "_mesh"
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    link_to_collection(obj, collection_name)
    return obj


def add_cylinder(name, location, radius, depth, material_name, collection_name,
                 rotation=(0, 0, 0), vertices=24):
    """Create a cylinder primitive."""
    remove_existing(name)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, vertices=vertices, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    if obj.data:
        obj.data.name = name + "_mesh"
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    link_to_collection(obj, collection_name)
    return obj


def add_uv_sphere(name, location, radius, material_name, collection_name,
                  scale=None, segments=16, ring_count=8):
    """Create a UV sphere primitive."""
    remove_existing(name)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, segments=segments, ring_count=ring_count,
        location=location)
    obj = bpy.context.active_object
    obj.name = name
    if scale:
        obj.scale = scale
    if obj.data:
        obj.data.name = name + "_mesh"
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    link_to_collection(obj, collection_name)
    return obj


def add_cone(name, location, radius1, radius2, depth, material_name,
             collection_name, vertices=24):
    """Create a cone primitive."""
    remove_existing(name)
    bpy.ops.mesh.primitive_cone_add(
        radius1=radius1, radius2=radius2, depth=depth,
        vertices=vertices, location=location)
    obj = bpy.context.active_object
    obj.name = name
    if obj.data:
        obj.data.name = name + "_mesh"
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    link_to_collection(obj, collection_name)
    return obj


def add_torus(name, location, major_radius, minor_radius, material_name,
              collection_name, rotation=(0, 0, 0), major_segments=48,
              minor_segments=12):
    """Create a torus primitive."""
    remove_existing(name)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius, minor_radius=minor_radius,
        major_segments=major_segments, minor_segments=minor_segments,
        location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    if obj.data:
        obj.data.name = name + "_mesh"
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    link_to_collection(obj, collection_name)
    return obj


def add_plane(name, location, size, material_name, collection_name,
              rotation=(0, 0, 0), scale=None):
    """Create a plane primitive."""
    remove_existing(name)
    bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    if scale:
        obj.scale = scale
    if obj.data:
        obj.data.name = name + "_mesh"
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    link_to_collection(obj, collection_name)
    return obj


def add_ico_sphere(name, location, radius, material_name, collection_name,
                   subdivisions=2):
    """Create an icosphere primitive."""
    remove_existing(name)
    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=radius, subdivisions=subdivisions, location=location)
    obj = bpy.context.active_object
    obj.name = name
    if obj.data:
        obj.data.name = name + "_mesh"
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    link_to_collection(obj, collection_name)
    return obj


def parent_to(child, parent):
    """Set parent-child relationship preserving transforms."""
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


# ===========================================================================
# Materials
# ===========================================================================

def create_materials():
    """Create all Cumbrian-themed materials."""
    print("[EskdaleTheme] Creating materials...")
    get_or_create_material("CumbrianSlate",
                           (0.25, 0.27, 0.3, 1.0), roughness=0.85)
    get_or_create_material("Whitewash",
                           (0.9, 0.88, 0.85, 1.0), roughness=0.8)
    get_or_create_material("CumbrianStone",
                           (0.55, 0.52, 0.48, 1.0), roughness=0.9)
    get_or_create_material("OldTimber",
                           (0.2, 0.12, 0.06, 1.0), roughness=0.7)
    get_or_create_material("SteelGrey",
                           (0.5, 0.5, 0.5, 1.0), metallic=0.8, roughness=0.3)
    get_or_create_material("HerdwickWool",
                           (0.7, 0.68, 0.65, 1.0), roughness=1.0)
    get_or_create_material("HerdwickFace",
                           (0.15, 0.15, 0.15, 1.0), roughness=0.9)
    get_or_create_material("TrainRed",
                           (0.6, 0.05, 0.02, 1.0), roughness=0.4)
    get_or_create_material("TrainGreen",
                           (0.05, 0.3, 0.1, 1.0), roughness=0.4)
    get_or_create_material("AtomBlue",
                           (0.1, 0.3, 0.8, 1.0), metallic=0.5, roughness=0.2,
                           emission_strength=0.3)
    get_or_create_material("CopperRoof",
                           (0.2, 0.45, 0.35, 1.0), metallic=0.6, roughness=0.4)
    # Light material for pub windows
    get_or_create_material("WindowGlass",
                           (0.85, 0.8, 0.6, 1.0), roughness=0.1)
    print("[EskdaleTheme] Materials created.")


# ===========================================================================
# Collections
# ===========================================================================

def setup_collections():
    """Create EskdaleTheme parent and sub-collections."""
    print("[EskdaleTheme] Setting up collections...")
    ensure_collection("EskdaleTheme")
    sub_cols = [
        "ET_WoolpackInn",
        "ET_HerdwickSheep",
        "ET_LaAlRatty",
        "ET_RomanFort",
        "ET_AtomModel",
        "ET_BootMill",
        "ET_MuncasterTower",
        "ET_DryStoneWalls",
    ]
    for name in sub_cols:
        ensure_collection(name, parent_name="EskdaleTheme")
    print("[EskdaleTheme] Collections ready.")


# ===========================================================================
# 1. THE WOOLPACK INN
# ===========================================================================

def build_woolpack_inn():
    """Build a miniature Cumbrian pub near Hole 1 entrance."""
    print("[EskdaleTheme] Building Woolpack Inn...")
    col = "ET_WoolpackInn"
    bx, by, bz = 0.5, 0.5, 0.05

    # Main building body
    wall_w, wall_d, wall_h = 0.4, 0.3, 0.25
    walls = add_cube("Woolpack_Inn_Walls", (bx, by, bz + wall_h / 2),
                     (wall_w, wall_d, wall_h), "Whitewash", col)

    # Slate roof - two angled planes meeting at ridge
    roof_half_w = wall_w / 2 + 0.02
    roof_depth = wall_d / 2 + 0.02
    ridge_y = bz + wall_h + 0.08
    # Left roof plane
    add_plane("Woolpack_Inn_RoofL",
              (bx - roof_half_w / 2.2, by, ridge_y - 0.02),
              0.25, "CumbrianSlate", col,
              rotation=(0, -0.45, 0),
              scale=(0.55, 1.05, 1.0))
    # Right roof plane
    add_plane("Woolpack_Inn_RoofR",
              (bx + roof_half_w / 2.2, by, ridge_y - 0.02),
              0.25, "CumbrianSlate", col,
              rotation=(0, 0.45, 0),
              scale=(0.55, 1.05, 1.0))

    # Chimneys
    ch_h = 0.06
    add_cube("Woolpack_Inn_ChimneyL",
             (bx - wall_w * 0.35, by, bz + wall_h + 0.08 + ch_h / 2),
             (0.035, 0.035, ch_h), "CumbrianStone", col)
    add_cube("Woolpack_Inn_ChimneyR",
             (bx + wall_w * 0.35, by, bz + wall_h + 0.08 + ch_h / 2),
             (0.035, 0.035, ch_h), "CumbrianStone", col)

    # Front door
    door_h = 0.1
    door_w_val = 0.04
    add_cube("Woolpack_Inn_Door",
             (bx, by - wall_d / 2 - 0.001, bz + door_h / 2),
             (door_w_val, 0.005, door_h), "OldTimber", col)

    # Ground-floor windows (flanking door)
    win_size = 0.035
    for i, xoff in enumerate([-0.1, 0.1]):
        add_cube(f"Woolpack_Inn_WinG{i}",
                 (bx + xoff, by - wall_d / 2 - 0.001, bz + 0.08),
                 (win_size, 0.004, win_size), "WindowGlass", col)

    # Upstairs window (centered)
    add_cube("Woolpack_Inn_WinUp",
             (bx, by - wall_d / 2 - 0.001, bz + 0.19),
             (win_size, 0.004, win_size), "WindowGlass", col)

    # Pub sign post
    post_h = 0.12
    add_cylinder("Woolpack_Inn_SignPost",
                 (bx + 0.18, by - wall_d / 2 - 0.04, bz + post_h / 2),
                 0.004, post_h, "OldTimber", col, vertices=8)
    # Sign board
    add_cube("Woolpack_Inn_Sign",
             (bx + 0.18, by - wall_d / 2 - 0.04, bz + post_h + 0.015),
             (0.06, 0.005, 0.04), "OldTimber", col)

    print("[EskdaleTheme] Woolpack Inn complete.")


# ===========================================================================
# 2. HERDWICK SHEEP
# ===========================================================================

def build_herdwick_sheep():
    """Build 4 Herdwick sheep scattered on the hillside."""
    print("[EskdaleTheme] Building Herdwick Sheep...")
    col = "ET_HerdwickSheep"
    positions = [
        (1.0, 5.0, -0.3),
        (8.0, 7.0, -1.0),
        (9.0, 3.0, 0.0),
        (2.0, 12.0, -2.0),
    ]
    rotations = [0.3, -0.5, 1.2, 2.8]  # Y-axis facing variety

    for idx, (sx, sy, sz) in enumerate(positions):
        n = idx + 1
        prefix = f"Herdwick_Sheep_{n}"
        rot_z = rotations[idx]

        # Body
        body = add_uv_sphere(
            f"{prefix}_Body", (sx, sy, sz + 0.04),
            0.04, "HerdwickWool", col,
            scale=(1.0, 1.5, 1.0), segments=12, ring_count=8)
        body.rotation_euler.z = rot_z

        # Head
        add_uv_sphere(
            f"{prefix}_Head",
            (sx + math.sin(rot_z) * 0.055,
             sy + math.cos(rot_z) * 0.055,
             sz + 0.05),
            0.02, "HerdwickFace", col,
            segments=10, ring_count=6)

        # Legs
        leg_offsets = [
            (-0.015, -0.025), (0.015, -0.025),
            (-0.015, 0.025), (0.015, 0.025),
        ]
        for li, (lx, ly) in enumerate(leg_offsets):
            rx = sx + lx * math.cos(rot_z) - ly * math.sin(rot_z)
            ry = sy + lx * math.sin(rot_z) + ly * math.cos(rot_z)
            add_cylinder(
                f"{prefix}_Leg{li}",
                (rx, ry, sz + 0.015),
                0.005, 0.03, "HerdwickFace", col, vertices=6)

    print("[EskdaleTheme] Herdwick Sheep complete (4 sheep).")


# ===========================================================================
# 3. LA'AL RATTY TRAIN
# ===========================================================================

def build_laal_ratty():
    """Build La'al Ratty miniature steam train near Hole 9."""
    print("[EskdaleTheme] Building La'al Ratty Train...")
    col = "ET_LaAlRatty"
    ox, oy, oz = 6.0, 14.5, -2.67

    # -- Locomotive --
    # Boiler
    add_cylinder("LaAlRatty_Boiler",
                 (ox, oy, oz + 0.04),
                 0.03, 0.12, "TrainGreen", col,
                 rotation=(PI / 2, 0, 0))

    # Cab
    add_cube("LaAlRatty_Cab",
             (ox, oy - 0.085, oz + 0.04),
             (0.05, 0.04, 0.06), "TrainGreen", col)

    # Smokestack
    add_cylinder("LaAlRatty_Smokestack",
                 (ox, oy + 0.05, oz + 0.085),
                 0.01, 0.03, "SteelGrey", col, vertices=12)

    # Locomotive wheels (3 pairs)
    for i, yoff in enumerate([-0.03, 0.0, 0.03]):
        for side, xoff in [("L", -0.025), ("R", 0.025)]:
            add_cylinder(
                f"LaAlRatty_LocoWheel_{side}{i}",
                (ox + xoff, oy + yoff, oz + 0.008),
                0.008, 0.004, "SteelGrey", col,
                rotation=(0, PI / 2, 0), vertices=12)

    # -- Carriage --
    car_y = oy - 0.17
    add_cube("LaAlRatty_Carriage",
             (ox, car_y, oz + 0.035),
             (0.04, 0.1, 0.025), "TrainRed", col)

    # Carriage wheels (2 pairs)
    for i, yoff in enumerate([-0.03, 0.03]):
        for side, xoff in [("L", -0.025), ("R", 0.025)]:
            add_cylinder(
                f"LaAlRatty_CarWheel_{side}{i}",
                (ox + xoff, car_y + yoff, oz + 0.008),
                0.007, 0.004, "SteelGrey", col,
                rotation=(0, PI / 2, 0), vertices=12)

    # -- Track rails --
    rail_len = 0.35
    for side, xoff in [("L", -0.02), ("R", 0.02)]:
        add_cube(f"LaAlRatty_Rail_{side}",
                 (ox + xoff, oy - 0.07, oz),
                 (0.004, rail_len, 0.004), "SteelGrey", col)

    # Rail ties (sleepers)
    for i in range(8):
        ty = oy + 0.1 - i * 0.045
        add_cube(f"LaAlRatty_Tie_{i}",
                 (ox, ty, oz - 0.002),
                 (0.06, 0.01, 0.003), "OldTimber", col)

    print("[EskdaleTheme] La'al Ratty Train complete.")


# ===========================================================================
# 4. HARDKNOTT ROMAN FORT WALLS
# ===========================================================================

def build_roman_fort():
    """Build miniature Roman fort wall section near Hole 4."""
    print("[EskdaleTheme] Building Hardknott Roman Fort...")
    col = "ET_RomanFort"
    ox, oy, oz = 3.5, 7.5, -0.85

    wall_len = 0.3
    wall_h = 0.1
    wall_t = 0.03

    # Wall segment A (along +X)
    add_cube("RomanFort_WallA",
             (ox + wall_len / 2, oy, oz + wall_h / 2),
             (wall_len, wall_t, wall_h), "CumbrianStone", col)

    # Wall segment B (along +Y) - with gateway gap
    # Split into two sections with a gap in the middle
    gap_w = 0.06
    seg_len = (wall_len - gap_w) / 2

    add_cube("RomanFort_WallB_Left",
             (ox, oy + seg_len / 2 + gap_w / 2, oz + wall_h / 2),
             (wall_t, seg_len, wall_h), "CumbrianStone", col)
    add_cube("RomanFort_WallB_Right",
             (ox, oy - seg_len / 2 - gap_w / 2, oz + wall_h / 2),
             (wall_t, seg_len, wall_h), "CumbrianStone", col)

    # Gateway arch lintel over the gap
    add_cube("RomanFort_Lintel",
             (ox, oy, oz + wall_h - 0.01),
             (wall_t + 0.005, gap_w + 0.02, 0.015), "CumbrianStone", col)

    # Corner tower at junction
    tower_size = 0.05
    tower_h = 0.12
    add_cube("RomanFort_Tower",
             (ox, oy, oz + tower_h / 2),
             (tower_size, tower_size, tower_h), "CumbrianStone", col)

    # Tower crenellations
    cren_size = 0.015
    cren_h = 0.02
    offsets = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    for i, (dx, dy) in enumerate(offsets):
        add_cube(f"RomanFort_Cren_{i}",
                 (ox + dx * tower_size * 0.4,
                  oy + dy * tower_size * 0.4,
                  oz + tower_h + cren_h / 2),
                 (cren_size, cren_size, cren_h), "CumbrianStone", col)

    print("[EskdaleTheme] Hardknott Roman Fort complete.")


# ===========================================================================
# 5. SELLAFIELD ATOM MODEL
# ===========================================================================

def build_atom_model():
    """Build a Bohr-model atom sculpture near Hole 6."""
    print("[EskdaleTheme] Building Sellafield Atom Model...")
    col = "ET_AtomModel"
    ox, oy, oz = 3.0, 13.0, -1.8

    # Support stand
    add_cylinder("Atom_Stand",
                 (ox, oy, oz + 0.05),
                 0.01, 0.1, "SteelGrey", col, vertices=12)

    # Central nucleus
    nuc_z = oz + 0.15
    add_ico_sphere("Atom_Nucleus",
                   (ox, oy, nuc_z),
                   0.03, "SteelGrey", col, subdivisions=2)

    # Electron orbits (3 tori at different tilts)
    orbit_params = [
        ("Atom_Orbit_1", 0.08, (0, 0, 0)),
        ("Atom_Orbit_2", 0.12, (PI / 4, 0, 0)),
        ("Atom_Orbit_3", 0.15, (0, 0, PI / 2)),
    ]
    for name, radius, rot in orbit_params:
        add_torus(name,
                  (ox, oy, nuc_z),
                  radius, 0.003, "AtomBlue", col,
                  rotation=rot, major_segments=48, minor_segments=8)

    # Electrons on orbits
    electron_positions = [
        (ox + 0.08, oy, nuc_z),        # on orbit 1
        (ox, oy + 0.085, nuc_z + 0.085),  # on orbit 2 (tilted 45)
        (ox, oy, nuc_z + 0.15),        # on orbit 3 (vertical)
    ]
    for i, pos in enumerate(electron_positions):
        add_uv_sphere(f"Atom_Electron_{i}",
                      pos, 0.01, "AtomBlue", col,
                      segments=10, ring_count=6)

    print("[EskdaleTheme] Sellafield Atom Model complete.")


# ===========================================================================
# 6. BOOT WATERMILL
# ===========================================================================

def build_boot_mill():
    """Build a miniature watermill near Hole 5 with animated wheel."""
    print("[EskdaleTheme] Building Boot Watermill...")
    col = "ET_BootMill"
    ox, oy, oz = 3.0, 10.0, -1.2

    bw, bd, bh = 0.25, 0.2, 0.2

    # Building walls
    add_cube("BootMill_Walls",
             (ox, oy, oz + bh / 2),
             (bw, bd, bh), "CumbrianStone", col)

    # Slate roof
    roof_z = oz + bh + 0.04
    add_plane("BootMill_RoofL",
              (ox - bw / 4.5, oy, roof_z),
              0.18, "CumbrianSlate", col,
              rotation=(0, -0.5, 0),
              scale=(0.42, 0.65, 1.0))
    add_plane("BootMill_RoofR",
              (ox + bw / 4.5, oy, roof_z),
              0.18, "CumbrianSlate", col,
              rotation=(0, 0.5, 0),
              scale=(0.42, 0.65, 1.0))

    # Door
    add_cube("BootMill_Door",
             (ox, oy - bd / 2 - 0.001, oz + 0.05),
             (0.04, 0.004, 0.08), "OldTimber", col)

    # Window
    add_cube("BootMill_Window",
             (ox + 0.06, oy - bd / 2 - 0.001, oz + 0.12),
             (0.03, 0.004, 0.03), "WindowGlass", col)

    # Waterwheel (on the right side of the building)
    wheel_x = ox + bw / 2 + 0.015
    wheel_z = oz + 0.08
    wheel = add_torus("BootMill_Wheel",
                      (wheel_x, oy, wheel_z),
                      0.08, 0.01, "OldTimber", col,
                      rotation=(0, PI / 2, 0),
                      major_segments=32, minor_segments=8)

    # Wheel paddles (8 around circumference)
    paddle_r = 0.08
    for i in range(8):
        angle = i * PI / 4
        py = oy + paddle_r * math.cos(angle)
        pz = wheel_z + paddle_r * math.sin(angle)
        paddle = add_cube(
            f"BootMill_Paddle_{i}",
            (wheel_x, py, pz),
            (0.005, 0.025, 0.025), "OldTimber", col)
        paddle.rotation_euler.x = angle
        parent_to(paddle, wheel)

    # Rotation driver on the waterwheel: 1 revolution per 6 seconds
    wheel.rotation_euler = (0, PI / 2, 0)
    # Use a driver for continuous rotation (skip fcurves - Blender 5.0 compat)
    driver = wheel.driver_add("rotation_euler", 0).driver
    driver.type = 'SCRIPTED'
    var = driver.variables.new()
    var.name = "frame"
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'SCENE'
    var.targets[0].id = bpy.context.scene
    var.targets[0].data_path = "frame_current"
    driver.expression = "frame * (2 * 3.14159 / 180)"

    # Water channel leading to the wheel
    ch_len = 0.2
    # Ensure Water material exists
    get_or_create_material("Water", (0.1, 0.3, 0.5, 0.8), roughness=0.1)
    add_cube("BootMill_WaterChannel",
             (wheel_x + 0.02, oy + ch_len / 2 + 0.05, oz + 0.01),
             (0.04, ch_len, 0.015), "Water", col)

    print("[EskdaleTheme] Boot Watermill complete.")


# ===========================================================================
# 7. MUNCASTER CASTLE TOWER
# ===========================================================================

def build_muncaster_tower():
    """Build a miniature castle tower near Hole 8."""
    print("[EskdaleTheme] Building Muncaster Castle Tower...")
    col = "ET_MuncasterTower"
    ox, oy, oz = 1.0, 14.0, -2.5

    tower_r = 0.06
    tower_h = 0.3

    # Tower cylinder
    add_cylinder("MuncasterTower_Body",
                 (ox, oy, oz + tower_h / 2),
                 tower_r, tower_h, "CumbrianStone", col)

    # Crenellations (4 cubes on the rim)
    cren_s = 0.02
    cren_h = 0.03
    for i in range(4):
        angle = i * PI / 2
        cx = ox + (tower_r - 0.005) * math.cos(angle)
        cy = oy + (tower_r - 0.005) * math.sin(angle)
        add_cube(f"MuncasterTower_Cren_{i}",
                 (cx, cy, oz + tower_h + cren_h / 2),
                 (cren_s, cren_s, cren_h), "CumbrianStone", col)

    # Conical roof
    roof_h = 0.08
    add_cone("MuncasterTower_Roof",
             (ox, oy, oz + tower_h + cren_h + roof_h / 2),
             0.07, 0.005, roof_h, "CopperRoof", col)

    # Slit windows (thin dark rectangles on the surface)
    for i, zoff in enumerate([0.1, 0.2]):
        angle = PI / 4 + i * PI / 2
        wx = ox + (tower_r + 0.001) * math.cos(angle)
        wy = oy + (tower_r + 0.001) * math.sin(angle)
        slit = add_cube(f"MuncasterTower_Slit_{i}",
                        (wx, wy, oz + zoff),
                        (0.008, 0.003, 0.025), "OldTimber", col)
        slit.rotation_euler.z = angle

    print("[EskdaleTheme] Muncaster Castle Tower complete.")


# ===========================================================================
# 8. DRY STONE WALLS
# ===========================================================================

def build_dry_stone_walls():
    """Build 4 dry stone wall sections between tiers."""
    print("[EskdaleTheme] Building Dry Stone Walls...")
    col = "ET_DryStoneWalls"

    wall_specs = [
        # (position, rotation_z, length)
        ((2.0, 3.5, 0.0), 0.2, 0.5),
        ((7.0, 6.0, -0.6), -0.3, 0.45),
        ((1.5, 9.5, -1.2), 0.0, 0.55),
        ((5.0, 13.0, -2.0), 0.5, 0.4),
    ]

    for idx, ((wx, wy, wz), rot_z, length) in enumerate(wall_specs):
        n = idx + 1
        wall_h = 0.08
        wall_t = 0.04
        name = f"DryStoneWall_{n}"

        # Main wall body with vertex displacement for irregularity
        remove_existing(name)
        bpy.ops.mesh.primitive_cube_add(size=1.0,
                                        location=(wx, wy, wz + wall_h / 2))
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (length, wall_t, wall_h)
        obj.rotation_euler.z = rot_z
        if obj.data:
            obj.data.name = name + "_mesh"
        mat = bpy.data.materials.get("CumbrianStone")
        if mat:
            obj.data.materials.clear()
            obj.data.materials.append(mat)
        link_to_collection(obj, col)

        # Apply scale so displacement works in local space
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)

        # Displace vertices slightly for irregularity
        import random
        random.seed(42 + idx)
        me = obj.data
        for v in me.vertices:
            v.co.x += random.uniform(-0.01, 0.01)
            v.co.y += random.uniform(-0.005, 0.005)
            v.co.z += random.uniform(-0.003, 0.003)
        me.update()
        obj.select_set(False)

        # Cap stones (slightly wider thin box on top)
        cap_name = f"DryStoneWall_{n}_Cap"
        cap = add_cube(cap_name,
                       (wx, wy, wz + wall_h + 0.008),
                       (length + 0.02, wall_t + 0.01, 0.012),
                       "CumbrianStone", col)
        cap.rotation_euler.z = rot_z

    print("[EskdaleTheme] Dry Stone Walls complete (4 sections).")


# ===========================================================================
# Main execution
# ===========================================================================

def main():
    """Build all Eskdale Green themed features."""
    print("=" * 60)
    print("[EskdaleTheme] Starting Eskdale Green theme build...")
    print("=" * 60)

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    create_materials()
    setup_collections()

    build_woolpack_inn()
    build_herdwick_sheep()
    build_laal_ratty()
    build_roman_fort()
    build_atom_model()
    build_boot_mill()
    build_muncaster_tower()
    build_dry_stone_walls()

    # Deselect all after building
    bpy.ops.object.select_all(action='DESELECT')

    # Save the blend file
    print("[EskdaleTheme] Saving blend file...")
    bpy.ops.wm.save_mainfile()

    print("=" * 60)
    print("[EskdaleTheme] Eskdale Green theme build COMPLETE.")
    print("=" * 60)


if __name__ == "__main__":
    main()
