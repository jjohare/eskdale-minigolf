"""
Hole 5: "The Windmill" (Par 4) - SIGNATURE HOLE
=================================================
Blender Python script to build the centerpiece hole of the mini golf course.

Ball path: TEE -> uphill ramp -> loop-de-loop -> windmill passage -> downhill -> green

Prerequisites:
  - Collections: Hole_5, H5_Fairway, H5_Green, H5_Borders, H5_Obstacles, H5_Decorations
  - Materials: ArtificialTurf, PuttingGreen, StoneBorder, WindmillBlade, WindmillBody,
               WoodDark, TransparentTube, MetalPin, RedPaint, CupBlack

Run inside Blender's Python environment.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOLE_NUM = 5
PREFIX = "H5"

# Origin / layout (ball travels roughly in +Y direction)
TEE_X = 5.0
TEE_Y = 8.0
TEE_Z = -1.1

GREEN_X = 5.0
GREEN_Y = 16.0          # 8 m from tee
GREEN_Z = -1.6          # 0.5 m drop

FAIRWAY_WIDTH = 1.2
BORDER_HEIGHT = 0.06
BORDER_THICKNESS = 0.05

# Ramp
RAMP_LENGTH = 1.0
RAMP_RISE = 0.15

# Loop-de-loop
LOOP_DIAMETER = 0.6
LOOP_RADIUS = LOOP_DIAMETER / 2.0
LOOP_TUBE_WIDTH = 0.15
LOOP_TUBE_DEPTH = 0.04   # channel depth
LOOP_ARC_DEG = 310       # degrees of torus arc

# Windmill
WM_BASE_RADIUS = 0.2     # half-width of octagonal base
WM_BASE_HEIGHT = 0.8
WM_UPPER_HEIGHT = 0.45
WM_UPPER_TOP_RADIUS = 0.12
WM_ROOF_HEIGHT = 0.25
WM_TOTAL_HEIGHT = WM_BASE_HEIGHT + WM_UPPER_HEIGHT + WM_ROOF_HEIGHT  # ~1.5m
WM_OPENING_WIDTH = 0.15
WM_OPENING_HEIGHT = 0.10
WM_BLADE_LENGTH = 0.6
WM_BLADE_WIDTH = 0.15
WM_BLADE_THICKNESS = 0.015
WM_HUB_HEIGHT = 0.9      # blade hub center height
WM_HUB_RADIUS = 0.04

# Animation
FPS = 30
REVOLUTION_SECONDS = 4
REVOLUTION_FRAMES = FPS * REVOLUTION_SECONDS  # 120 frames

# Segment layout along Y axis from TEE
SEG_RAMP_START = 0.0
SEG_RAMP_END = RAMP_LENGTH                        # 1.0
SEG_LOOP_CENTER_Y = SEG_RAMP_END + LOOP_RADIUS + 0.15  # ~1.45
SEG_WINDMILL_Y = SEG_LOOP_CENTER_Y + LOOP_RADIUS + 0.8  # ~2.55
SEG_DOWNHILL_START = SEG_WINDMILL_Y + 0.5
SEG_GREEN_CENTER_Y = GREEN_Y - TEE_Y               # 8.0

# Cup position on green
CUP_X = GREEN_X
CUP_Y = GREEN_Y - 0.4
CUP_Z = GREEN_Z


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_collection(name):
    """Return an existing collection by name."""
    col = bpy.data.collections.get(name)
    if col is None:
        raise RuntimeError(f"Collection '{name}' not found. Create it before running this script.")
    return col


def get_material(name):
    """Return an existing material by name, or a fallback default."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        print(f"  WARNING: Material '{name}' not found, creating placeholder.")
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
    return mat


def link_to_collection(obj, col_name):
    """Link an object to the named sub-collection and unlink from Scene Collection."""
    col = get_collection(col_name)
    if obj.name not in col.objects:
        col.objects.link(obj)
    scene_col = bpy.context.scene.collection
    if obj.name in scene_col.objects:
        scene_col.objects.unlink(obj)


def assign_material(obj, mat_name):
    """Assign material to object (first slot)."""
    mat = get_material(mat_name)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def object_exists(name):
    """Check if an object already exists in the scene."""
    return name in bpy.data.objects


def safe_name(base):
    """Create a prefixed object name."""
    return f"{PREFIX}_{base}"


def remove_if_exists(name):
    """Remove an existing object so we can recreate it."""
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        bpy.data.objects.remove(obj, do_unlink=True)


def create_object_from_bmesh(bm, name, location=(0, 0, 0)):
    """Finalize a bmesh into a new mesh object at the given location."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(location)
    return obj


# ---------------------------------------------------------------------------
# Fairway sections
# ---------------------------------------------------------------------------

def build_tee_area():
    """Build the tee pad at the start of hole 5."""
    name = safe_name("Tee")
    remove_if_exists(name)
    print(f"  Building {name}...")

    bm = bmesh.new()
    w = FAIRWAY_WIDTH / 2.0
    pad_len = 0.5
    verts = [
        bm.verts.new((-w, 0, 0)),
        bm.verts.new((w, 0, 0)),
        bm.verts.new((w, pad_len, 0)),
        bm.verts.new((-w, pad_len, 0)),
    ]
    bm.faces.new(verts)
    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (TEE_X, TEE_Y, TEE_Z))
    assign_material(obj, "ArtificialTurf")
    link_to_collection(obj, f"{PREFIX}_Fairway")
    return obj


def build_ramp():
    """Build the uphill ramp from tee to loop entry."""
    name = safe_name("Ramp")
    remove_if_exists(name)
    print(f"  Building {name}...")

    bm = bmesh.new()
    w = FAIRWAY_WIDTH / 2.0
    y0 = 0.5  # after tee pad
    y1 = y0 + RAMP_LENGTH
    z_rise = RAMP_RISE

    verts = [
        bm.verts.new((-w, y0, 0)),
        bm.verts.new((w, y0, 0)),
        bm.verts.new((w, y1, z_rise)),
        bm.verts.new((-w, y1, z_rise)),
    ]
    bm.faces.new(verts)
    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (TEE_X, TEE_Y, TEE_Z))
    assign_material(obj, "ArtificialTurf")
    link_to_collection(obj, f"{PREFIX}_Fairway")
    return obj


def build_flat_fairway_section(y_start, y_end, z_start, z_end, suffix):
    """Build a flat or sloped fairway section."""
    name = safe_name(f"Fairway_{suffix}")
    remove_if_exists(name)
    print(f"  Building {name}...")

    bm = bmesh.new()
    w = FAIRWAY_WIDTH / 2.0
    verts = [
        bm.verts.new((-w, y_start, z_start)),
        bm.verts.new((w, y_start, z_start)),
        bm.verts.new((w, y_end, z_end)),
        bm.verts.new((-w, y_end, z_end)),
    ]
    bm.faces.new(verts)
    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (TEE_X, TEE_Y, 0))
    assign_material(obj, "ArtificialTurf")
    link_to_collection(obj, f"{PREFIX}_Fairway")
    return obj


def build_downhill_section():
    """Build the downhill slope from windmill area to green."""
    y_start_local = SEG_DOWNHILL_START
    y_end_local = SEG_GREEN_CENTER_Y - 1.0
    z_start = TEE_Z + RAMP_RISE - 0.05  # slight drop from loop exit
    z_end = GREEN_Z

    name = safe_name("Fairway_Downhill")
    remove_if_exists(name)
    print(f"  Building {name}...")

    bm = bmesh.new()
    w = FAIRWAY_WIDTH / 2.0
    verts = [
        bm.verts.new((-w, y_start_local, z_start - TEE_Z)),
        bm.verts.new((w, y_start_local, z_start - TEE_Z)),
        bm.verts.new((w, y_end_local, z_end - TEE_Z)),
        bm.verts.new((-w, y_end_local, z_end - TEE_Z)),
    ]
    bm.faces.new(verts)
    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (TEE_X, TEE_Y, TEE_Z))
    assign_material(obj, "ArtificialTurf")
    link_to_collection(obj, f"{PREFIX}_Fairway")
    return obj


# ---------------------------------------------------------------------------
# Borders
# ---------------------------------------------------------------------------

def build_border_segment(y_start, y_end, z_start, z_end, side, suffix):
    """Build a stone border rail along the fairway edge."""
    name = safe_name(f"Border_{side}_{suffix}")
    remove_if_exists(name)

    bm = bmesh.new()
    w = FAIRWAY_WIDTH / 2.0
    t = BORDER_THICKNESS
    h = BORDER_HEIGHT
    x_offset = w if side == "R" else -w - t

    # 4 bottom verts, 4 top verts -> 6 faces (box)
    v = [
        bm.verts.new((x_offset, y_start, z_start)),
        bm.verts.new((x_offset + t, y_start, z_start)),
        bm.verts.new((x_offset + t, y_end, z_end)),
        bm.verts.new((x_offset, y_end, z_end)),
        bm.verts.new((x_offset, y_start, z_start + h)),
        bm.verts.new((x_offset + t, y_start, z_start + h)),
        bm.verts.new((x_offset + t, y_end, z_end + h)),
        bm.verts.new((x_offset, y_end, z_end + h)),
    ]

    # bottom, top, front, back, left, right
    bm.faces.new([v[0], v[1], v[2], v[3]])
    bm.faces.new([v[4], v[7], v[6], v[5]])
    bm.faces.new([v[0], v[4], v[5], v[1]])
    bm.faces.new([v[2], v[6], v[7], v[3]])
    bm.faces.new([v[0], v[3], v[7], v[4]])
    bm.faces.new([v[1], v[5], v[6], v[2]])
    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (TEE_X, TEE_Y, 0))
    assign_material(obj, "StoneBorder")
    link_to_collection(obj, f"{PREFIX}_Borders")
    return obj


def build_all_borders():
    """Build border rails along the full fairway length."""
    print("  Building border rails...")
    segments = [
        # (y_start, y_end, z_start, z_end, suffix)
        (0.0, SEG_RAMP_END + 0.5, TEE_Z, TEE_Z, "Tee"),
        (SEG_RAMP_END + 0.5, SEG_RAMP_END + RAMP_LENGTH,
         TEE_Z, TEE_Z + RAMP_RISE, "Ramp"),
        (SEG_DOWNHILL_START, SEG_GREEN_CENTER_Y - 1.0,
         TEE_Z + RAMP_RISE - 0.05, GREEN_Z, "Downhill"),
    ]
    for y0, y1, z0, z1, suffix in segments:
        for side in ("L", "R"):
            build_border_segment(y0, y1, z0, z1, side, suffix)


# ---------------------------------------------------------------------------
# Loop-de-loop
# ---------------------------------------------------------------------------

def build_loop_de_loop():
    """
    Build a transparent loop-de-loop track (torus channel segment).

    The loop is a partial torus (~310 degrees) oriented so the ball enters
    from below traveling in +Y, arcs upward and over, then exits heading
    toward the windmill.
    """
    name = safe_name("LoopDeLoop")
    remove_if_exists(name)
    print(f"  Building {name}...")

    # Torus parameters
    major_r = LOOP_RADIUS            # 0.3 m center-of-tube to center-of-torus
    minor_r = LOOP_TUBE_WIDTH / 2.0  # 0.075 m tube radius (half channel width)
    arc_rad = math.radians(LOOP_ARC_DEG)

    seg_major = 48   # segments around the loop arc
    seg_minor = 12   # segments around the tube cross-section

    bm = bmesh.new()

    # Build the torus segment ring by ring
    rings = []
    for i in range(seg_major + 1):
        angle = (i / seg_major) * arc_rad
        # Center of this ring on the torus
        cx = 0.0
        cy = major_r * math.sin(angle)
        cz = major_r * math.cos(angle)

        ring_verts = []
        for j in range(seg_minor):
            theta = (j / seg_minor) * 2.0 * math.pi
            # Local offset in the cross-section plane
            # The cross-section plane normal points along the torus tangent
            # We need the radial and "up" directions at this point on the torus
            # Radial direction (outward from torus center)
            rad_y = math.sin(angle)
            rad_z = math.cos(angle)
            # "Up" direction perpendicular to radial and X
            # tangent along torus = d/dangle of (0, R*sin(a), R*cos(a))
            # = (0, R*cos(a), -R*sin(a)) -- we don't need tangent, we need
            # the two cross-section axes: radial and X
            r_offset = minor_r * math.cos(theta)
            x_offset = minor_r * math.sin(theta)

            vx = cx + x_offset
            vy = cy + r_offset * rad_y
            vz = cz + r_offset * rad_z

            ring_verts.append(bm.verts.new((vx, vy, vz)))
        rings.append(ring_verts)

    # Create faces between consecutive rings
    for i in range(len(rings) - 1):
        for j in range(seg_minor):
            j_next = (j + 1) % seg_minor
            v1 = rings[i][j]
            v2 = rings[i][j_next]
            v3 = rings[i + 1][j_next]
            v4 = rings[i + 1][j]
            bm.faces.new([v1, v2, v3, v4])

    bm.normal_update()

    # Position: loop center is at (TEE_X, TEE_Y + SEG_LOOP_CENTER_Y, TEE_Z + RAMP_RISE + LOOP_RADIUS)
    loop_x = TEE_X
    loop_y = TEE_Y + SEG_LOOP_CENTER_Y
    loop_z = TEE_Z + RAMP_RISE + LOOP_RADIUS

    obj = create_object_from_bmesh(bm, name, (loop_x, loop_y, loop_z))

    # Rotate so the loop plane is perpendicular to the Y axis (ball travels in +Y)
    # The torus was built in the YZ plane with entry at the bottom
    obj.rotation_euler = (math.radians(90), 0, 0)

    assign_material(obj, "TransparentTube")

    # Make the material semi-transparent if possible
    mat = get_material("TransparentTube")
    if mat.use_nodes:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            # Set transmission for glass-like transparency
            if hasattr(bsdf.inputs, 'get'):
                trans_input = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
                if trans_input:
                    trans_input.default_value = 0.85
                alpha_input = bsdf.inputs.get("Alpha")
                if alpha_input:
                    alpha_input.default_value = 0.3
                color_input = bsdf.inputs.get("Base Color")
                if color_input:
                    color_input.default_value = (0.7, 0.85, 1.0, 0.3)
        mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else mat.blend_method

    link_to_collection(obj, f"{PREFIX}_Obstacles")
    return obj


# ---------------------------------------------------------------------------
# Windmill
# ---------------------------------------------------------------------------

def create_octagonal_prism(bm, radius, height, z_base=0.0, taper=1.0):
    """Create an octagonal prism in the bmesh. Returns (bottom_verts, top_verts)."""
    n_sides = 8
    bottom = []
    top = []
    for i in range(n_sides):
        angle = (i / n_sides) * 2.0 * math.pi
        bx = radius * math.cos(angle)
        by = radius * math.sin(angle)
        tx = radius * taper * math.cos(angle)
        ty = radius * taper * math.sin(angle)
        bottom.append(bm.verts.new((bx, by, z_base)))
        top.append(bm.verts.new((tx, ty, z_base + height)))

    # Bottom face
    bm.faces.new(bottom)
    # Top face
    bm.faces.new(list(reversed(top)))
    # Side faces
    for i in range(n_sides):
        i_next = (i + 1) % n_sides
        bm.faces.new([bottom[i], bottom[i_next], top[i_next], top[i]])

    return bottom, top


def build_windmill_base():
    """Build the windmill body (octagonal tower with tapered upper section and roof)."""
    name = safe_name("Windmill_Body")
    remove_if_exists(name)
    print(f"  Building {name}...")

    wm_x = TEE_X
    wm_y = TEE_Y + SEG_WINDMILL_Y
    wm_z = TEE_Z + RAMP_RISE * 0.5  # slightly above fairway level

    bm = bmesh.new()

    # Lower octagonal prism
    create_octagonal_prism(bm, WM_BASE_RADIUS, WM_BASE_HEIGHT, z_base=0.0, taper=1.0)

    # Upper tapered section
    taper_ratio = WM_UPPER_TOP_RADIUS / WM_BASE_RADIUS
    create_octagonal_prism(bm, WM_BASE_RADIUS, WM_UPPER_HEIGHT,
                           z_base=WM_BASE_HEIGHT, taper=taper_ratio)

    # Roof cone
    roof_base_z = WM_BASE_HEIGHT + WM_UPPER_HEIGHT
    n_sides = 8
    roof_bottom = []
    for i in range(n_sides):
        angle = (i / n_sides) * 2.0 * math.pi
        rx = WM_UPPER_TOP_RADIUS * math.cos(angle)
        ry = WM_UPPER_TOP_RADIUS * math.sin(angle)
        roof_bottom.append(bm.verts.new((rx, ry, roof_base_z)))
    apex = bm.verts.new((0, 0, roof_base_z + WM_ROOF_HEIGHT))
    for i in range(n_sides):
        i_next = (i + 1) % n_sides
        bm.faces.new([roof_bottom[i], roof_bottom[i_next], apex])
    # Roof bottom cap
    bm.faces.new(roof_bottom)

    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (wm_x, wm_y, wm_z))
    assign_material(obj, "WindmillBody")
    link_to_collection(obj, f"{PREFIX}_Obstacles")

    # Now cut the ground-level opening through the base for the ball
    build_windmill_opening(wm_x, wm_y, wm_z)

    return obj, (wm_x, wm_y, wm_z)


def build_windmill_opening(wm_x, wm_y, wm_z):
    """Build the ground-level rectangular tunnel through the windmill base."""
    name = safe_name("Windmill_Opening")
    remove_if_exists(name)
    print(f"  Building {name} (ball passage)...")

    # The opening is a rectangular hole through the base along the Y axis
    # We model it as a rectangular tube (open on both Y ends)
    hw = WM_OPENING_WIDTH / 2.0
    hh = WM_OPENING_HEIGHT
    depth = WM_BASE_RADIUS * 2.5  # extends through the full base

    bm = bmesh.new()

    # 4 faces forming the inside of the tunnel (top, bottom, left, right walls)
    v = [
        # front face (negative Y)
        bm.verts.new((-hw, -depth / 2, 0)),       # 0 bottom-left
        bm.verts.new((hw, -depth / 2, 0)),        # 1 bottom-right
        bm.verts.new((hw, -depth / 2, hh)),       # 2 top-right
        bm.verts.new((-hw, -depth / 2, hh)),      # 3 top-left
        # back face (positive Y)
        bm.verts.new((-hw, depth / 2, 0)),        # 4 bottom-left
        bm.verts.new((hw, depth / 2, 0)),         # 5 bottom-right
        bm.verts.new((hw, depth / 2, hh)),        # 6 top-right
        bm.verts.new((-hw, depth / 2, hh)),       # 7 top-left
    ]

    # Top wall (ceiling of tunnel)
    bm.faces.new([v[3], v[2], v[6], v[7]])
    # Bottom wall (floor of tunnel)
    bm.faces.new([v[0], v[4], v[5], v[1]])
    # Left wall
    bm.faces.new([v[0], v[3], v[7], v[4]])
    # Right wall
    bm.faces.new([v[1], v[5], v[6], v[2]])

    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (wm_x, wm_y, wm_z))
    assign_material(obj, "WoodDark")
    link_to_collection(obj, f"{PREFIX}_Obstacles")
    return obj


def build_windmill_blades(wm_x, wm_y, wm_z):
    """
    Build the 4 windmill blades with animation driver.

    Creates an Empty hub, parents 4 blade meshes to it,
    and adds a rotation driver to the hub.
    """
    hub_name = safe_name("Windmill_Hub")
    remove_if_exists(hub_name)
    print(f"  Building {hub_name} and blades...")

    hub_z = wm_z + WM_HUB_HEIGHT

    # Create the hub empty
    hub = bpy.data.objects.new(hub_name, None)
    hub.empty_display_type = 'CIRCLE'
    hub.empty_display_size = WM_HUB_RADIUS
    hub.location = Vector((wm_x, wm_y, hub_z))
    link_to_collection(hub, f"{PREFIX}_Obstacles")

    # Create 4 blades
    for i in range(4):
        blade_name = safe_name(f"Windmill_Blade_{i}")
        remove_if_exists(blade_name)

        angle = (i / 4.0) * 2.0 * math.pi  # 0, 90, 180, 270 degrees

        bm = bmesh.new()

        # Blade is a flat rectangle extending outward from center
        # Built in local space: extends along +Z (radially outward from hub),
        # width along X
        hw = WM_BLADE_WIDTH / 2.0
        ht = WM_BLADE_THICKNESS / 2.0

        # Blade extends from hub radius to blade tip
        blade_start = WM_HUB_RADIUS
        blade_end = blade_start + WM_BLADE_LENGTH

        v = [
            bm.verts.new((-hw, -ht, blade_start)),
            bm.verts.new((hw, -ht, blade_start)),
            bm.verts.new((hw, -ht, blade_end)),
            bm.verts.new((-hw, -ht, blade_end)),
            bm.verts.new((-hw, ht, blade_start)),
            bm.verts.new((hw, ht, blade_start)),
            bm.verts.new((hw, ht, blade_end)),
            bm.verts.new((-hw, ht, blade_end)),
        ]

        # 6 faces (box)
        bm.faces.new([v[0], v[1], v[2], v[3]])  # front
        bm.faces.new([v[4], v[7], v[6], v[5]])  # back
        bm.faces.new([v[0], v[3], v[7], v[4]])  # left
        bm.faces.new([v[1], v[5], v[6], v[2]])  # right
        bm.faces.new([v[3], v[2], v[6], v[7]])  # top (tip)
        bm.faces.new([v[0], v[4], v[5], v[1]])  # bottom (hub end)

        bm.normal_update()

        blade_obj = create_object_from_bmesh(bm, blade_name, (0, 0, 0))
        assign_material(blade_obj, "WindmillBlade")

        # Rotate blade around Y axis by its angle offset (in local space relative to hub)
        blade_obj.rotation_euler = (0, angle, 0)

        # Parent to hub (keep transform)
        blade_obj.parent = hub
        blade_obj.matrix_parent_inverse = hub.matrix_world.inverted()

        link_to_collection(blade_obj, f"{PREFIX}_Obstacles")

    # --- ANIMATION DRIVER ---
    # Rotate the hub around its local Y axis (blades spin in a plane facing the player)
    # driver expression: frame * (2 * pi / 120) => full rotation every 120 frames (4 sec at 30fps)
    print("  Setting up windmill rotation driver...")

    # The blades rotate around the Y axis of the hub (perpendicular to the fairway)
    driver = hub.driver_add("rotation_euler", 1)  # Y-axis rotation
    drv = driver.driver
    drv.type = 'SCRIPTED'

    var = drv.variables.new()
    var.name = "frame"
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'SCENE'
    var.targets[0].id = bpy.context.scene
    var.targets[0].data_path = "frame_current"

    drv.expression = f"frame * (2 * 3.14159 / {REVOLUTION_FRAMES})"

    print(f"  Driver set: full revolution every {REVOLUTION_SECONDS}s ({REVOLUTION_FRAMES} frames)")

    return hub


# ---------------------------------------------------------------------------
# Green and cup
# ---------------------------------------------------------------------------

def build_green():
    """Build the putting green at the end of hole 5."""
    name = safe_name("Green")
    remove_if_exists(name)
    print(f"  Building {name}...")

    green_radius = 1.0
    segments = 32

    bm = bmesh.new()
    center = bm.verts.new((0, 0, 0))
    ring = []
    for i in range(segments):
        angle = (i / segments) * 2.0 * math.pi
        ring.append(bm.verts.new((green_radius * math.cos(angle),
                                   green_radius * math.sin(angle), 0)))

    for i in range(segments):
        i_next = (i + 1) % segments
        bm.faces.new([center, ring[i], ring[i_next]])

    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (GREEN_X, GREEN_Y, GREEN_Z))
    assign_material(obj, "PuttingGreen")
    link_to_collection(obj, f"{PREFIX}_Green")
    return obj


def build_cup():
    """Build the cup (hole) on the green."""
    name = safe_name("Cup")
    remove_if_exists(name)
    print(f"  Building {name}...")

    bm = bmesh.new()
    cup_radius = 0.054  # standard golf cup ~108mm diameter
    cup_depth = 0.05
    segments = 16

    # Bottom disc
    bottom_center = bm.verts.new((0, 0, -cup_depth))
    bottom_ring = []
    for i in range(segments):
        angle = (i / segments) * 2.0 * math.pi
        bottom_ring.append(bm.verts.new((cup_radius * math.cos(angle),
                                          cup_radius * math.sin(angle),
                                          -cup_depth)))
    for i in range(segments):
        i_next = (i + 1) % segments
        bm.faces.new([bottom_center, bottom_ring[i], bottom_ring[i_next]])

    # Top ring (at green surface)
    top_ring = []
    for i in range(segments):
        angle = (i / segments) * 2.0 * math.pi
        top_ring.append(bm.verts.new((cup_radius * math.cos(angle),
                                       cup_radius * math.sin(angle), 0)))

    # Side walls
    for i in range(segments):
        i_next = (i + 1) % segments
        bm.faces.new([bottom_ring[i], top_ring[i], top_ring[i_next], bottom_ring[i_next]])

    bm.normal_update()

    obj = create_object_from_bmesh(bm, name, (CUP_X, CUP_Y, CUP_Z))
    assign_material(obj, "CupBlack")
    link_to_collection(obj, f"{PREFIX}_Green")
    return obj


def build_flag_pin():
    """Build the flag pin and flag on the green."""
    pin_name = safe_name("FlagPin")
    flag_name = safe_name("Flag")
    remove_if_exists(pin_name)
    remove_if_exists(flag_name)
    print(f"  Building {pin_name} and {flag_name}...")

    pin_height = 0.6
    pin_radius = 0.005

    # Pin (cylinder)
    bm = bmesh.new()
    segments = 8
    bottom_ring = []
    top_ring = []
    for i in range(segments):
        angle = (i / segments) * 2.0 * math.pi
        bx = pin_radius * math.cos(angle)
        by = pin_radius * math.sin(angle)
        bottom_ring.append(bm.verts.new((bx, by, 0)))
        top_ring.append(bm.verts.new((bx, by, pin_height)))

    # Side faces
    for i in range(segments):
        i_next = (i + 1) % segments
        bm.faces.new([bottom_ring[i], bottom_ring[i_next],
                       top_ring[i_next], top_ring[i]])

    # Top cap
    bm.faces.new(list(reversed(top_ring)))

    bm.normal_update()

    pin_obj = create_object_from_bmesh(bm, pin_name, (CUP_X, CUP_Y, CUP_Z))
    assign_material(pin_obj, "MetalPin")
    link_to_collection(pin_obj, f"{PREFIX}_Green")

    # Flag (small triangle)
    bm2 = bmesh.new()
    flag_w = 0.08
    flag_h = 0.05
    flag_base_z = pin_height - flag_h - 0.02

    fv = [
        bm2.verts.new((0, 0, flag_base_z)),
        bm2.verts.new((flag_w, 0, flag_base_z + flag_h / 2.0)),
        bm2.verts.new((0, 0, flag_base_z + flag_h)),
    ]
    bm2.faces.new(fv)
    # Back face
    bm2.faces.new(list(reversed([
        bm2.verts.new((0, 0.002, flag_base_z)),
        bm2.verts.new((flag_w, 0.002, flag_base_z + flag_h / 2.0)),
        bm2.verts.new((0, 0.002, flag_base_z + flag_h)),
    ])))
    bm2.normal_update()

    flag_obj = create_object_from_bmesh(bm2, flag_name, (CUP_X, CUP_Y, CUP_Z))
    assign_material(flag_obj, "RedPaint")
    link_to_collection(flag_obj, f"{PREFIX}_Green")

    return pin_obj, flag_obj


# ---------------------------------------------------------------------------
# Decorations
# ---------------------------------------------------------------------------

def build_tulip(x, y, z, color_index, idx):
    """Build a single tulip (cone on a stick)."""
    name = safe_name(f"Tulip_{idx}")
    remove_if_exists(name)

    # Stem (thin cylinder)
    stem_name = safe_name(f"TulipStem_{idx}")
    remove_if_exists(stem_name)

    stem_h = 0.12
    stem_r = 0.005
    bm = bmesh.new()
    segs = 6
    b_ring = []
    t_ring = []
    for i in range(segs):
        a = (i / segs) * 2.0 * math.pi
        bm_x = stem_r * math.cos(a)
        bm_y = stem_r * math.sin(a)
        b_ring.append(bm.verts.new((bm_x, bm_y, 0)))
        t_ring.append(bm.verts.new((bm_x, bm_y, stem_h)))
    for i in range(segs):
        i_n = (i + 1) % segs
        bm.faces.new([b_ring[i], b_ring[i_n], t_ring[i_n], t_ring[i]])
    bm.normal_update()
    stem_obj = create_object_from_bmesh(bm, stem_name, (x, y, z))

    # Create green material for stem
    stem_mat_name = "TulipStemGreen"
    stem_mat = bpy.data.materials.get(stem_mat_name)
    if not stem_mat:
        stem_mat = bpy.data.materials.new(name=stem_mat_name)
        stem_mat.use_nodes = True
        bsdf = stem_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            color_in = bsdf.inputs.get("Base Color")
            if color_in:
                color_in.default_value = (0.1, 0.5, 0.1, 1.0)
    if stem_obj.data.materials:
        stem_obj.data.materials[0] = stem_mat
    else:
        stem_obj.data.materials.append(stem_mat)
    link_to_collection(stem_obj, f"{PREFIX}_Decorations")

    # Flower head (cone)
    tulip_colors = [
        (0.9, 0.1, 0.15, 1.0),   # red
        (1.0, 0.85, 0.1, 1.0),   # yellow
        (0.95, 0.4, 0.6, 1.0),   # pink
        (0.6, 0.15, 0.7, 1.0),   # purple
        (1.0, 0.5, 0.0, 1.0),    # orange
    ]
    color = tulip_colors[color_index % len(tulip_colors)]

    bm2 = bmesh.new()
    flower_r = 0.025
    flower_h = 0.04
    f_segs = 8
    f_base = []
    for i in range(f_segs):
        a = (i / f_segs) * 2.0 * math.pi
        f_base.append(bm2.verts.new((flower_r * math.cos(a),
                                      flower_r * math.sin(a), stem_h)))
    f_apex = bm2.verts.new((0, 0, stem_h + flower_h))
    for i in range(f_segs):
        i_n = (i + 1) % f_segs
        bm2.faces.new([f_base[i], f_base[i_n], f_apex])
    bm2.faces.new(f_base)
    bm2.normal_update()

    flower_obj = create_object_from_bmesh(bm2, name, (x, y, z))

    # Create or reuse tulip color material
    mat_name = f"TulipColor_{color_index % len(tulip_colors)}"
    t_mat = bpy.data.materials.get(mat_name)
    if not t_mat:
        t_mat = bpy.data.materials.new(name=mat_name)
        t_mat.use_nodes = True
        bsdf = t_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            color_in = bsdf.inputs.get("Base Color")
            if color_in:
                color_in.default_value = color
    if flower_obj.data.materials:
        flower_obj.data.materials[0] = t_mat
    else:
        flower_obj.data.materials.append(t_mat)
    link_to_collection(flower_obj, f"{PREFIX}_Decorations")

    return flower_obj, stem_obj


def build_tulip_beds(wm_x, wm_y, wm_z):
    """Build tulip beds around the windmill base."""
    print("  Building tulip beds...")
    tulips_per_side = 5
    bed_radius = WM_BASE_RADIUS + 0.15
    idx = 0

    for i in range(tulips_per_side * 3):  # tulips on 3 sides (not blocking ball path)
        angle = math.radians(45 + (i / (tulips_per_side * 3)) * 270)  # skip front
        tx = wm_x + bed_radius * math.cos(angle)
        ty = wm_y + bed_radius * math.sin(angle)
        tz = wm_z
        build_tulip(tx, ty, tz, idx, idx)
        idx += 1


def build_decorative_pond(wm_x, wm_y, wm_z):
    """Build a small decorative pond near the windmill."""
    name = safe_name("Pond")
    remove_if_exists(name)
    print(f"  Building {name}...")

    pond_radius = 0.35
    segments = 24

    bm = bmesh.new()
    center = bm.verts.new((0, 0, 0))
    ring = []
    for i in range(segments):
        angle = (i / segments) * 2.0 * math.pi
        # Slight irregular shape
        r = pond_radius * (1.0 + 0.1 * math.sin(angle * 3))
        ring.append(bm.verts.new((r * math.cos(angle), r * math.sin(angle), 0)))

    for i in range(segments):
        i_next = (i + 1) % segments
        bm.faces.new([center, ring[i], ring[i_next]])

    bm.normal_update()

    pond_x = wm_x + 0.8
    pond_y = wm_y + 0.3
    pond_z = wm_z - 0.02  # slightly recessed

    obj = create_object_from_bmesh(bm, name, (pond_x, pond_y, pond_z))

    # Create or reuse Water material
    water_mat_name = "Water"
    w_mat = bpy.data.materials.get(water_mat_name)
    if not w_mat:
        w_mat = bpy.data.materials.new(name=water_mat_name)
        w_mat.use_nodes = True
        bsdf = w_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            color_in = bsdf.inputs.get("Base Color")
            if color_in:
                color_in.default_value = (0.1, 0.3, 0.6, 0.8)
            rough_in = bsdf.inputs.get("Roughness")
            if rough_in:
                rough_in.default_value = 0.1
            trans_in = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
            if trans_in:
                trans_in.default_value = 0.5

    if obj.data.materials:
        obj.data.materials[0] = w_mat
    else:
        obj.data.materials.append(w_mat)

    link_to_collection(obj, f"{PREFIX}_Decorations")

    # Pond border (torus ring)
    border_name = safe_name("PondBorder")
    remove_if_exists(border_name)

    bm2 = bmesh.new()
    border_major_r = pond_radius + 0.03
    border_minor_r = 0.02
    b_seg_major = 24
    b_seg_minor = 8

    rings = []
    for i in range(b_seg_major):
        angle = (i / b_seg_major) * 2.0 * math.pi
        r_var = 1.0 + 0.1 * math.sin(angle * 3)
        cx = border_major_r * r_var * math.cos(angle)
        cy = border_major_r * r_var * math.sin(angle)

        ring_verts = []
        for j in range(b_seg_minor):
            theta = (j / b_seg_minor) * 2.0 * math.pi
            # Cross section in the radial-Z plane
            rad_x = math.cos(angle)
            rad_y = math.sin(angle)
            r_off = border_minor_r * math.cos(theta)
            z_off = border_minor_r * math.sin(theta)
            ring_verts.append(bm2.verts.new((
                cx + r_off * rad_x,
                cy + r_off * rad_y,
                z_off
            )))
        rings.append(ring_verts)

    for i in range(b_seg_major):
        i_next = (i + 1) % b_seg_major
        for j in range(b_seg_minor):
            j_next = (j + 1) % b_seg_minor
            bm2.faces.new([
                rings[i][j], rings[i][j_next],
                rings[i_next][j_next], rings[i_next][j]
            ])

    bm2.normal_update()
    border_obj = create_object_from_bmesh(bm2, border_name, (pond_x, pond_y, pond_z))
    assign_material(border_obj, "StoneBorder")
    link_to_collection(border_obj, f"{PREFIX}_Decorations")

    return obj


# ---------------------------------------------------------------------------
# Connecting fairway sections between features
# ---------------------------------------------------------------------------

def build_connecting_fairways():
    """Build the fairway sections that connect tee, ramp, loop, windmill, and green."""
    print("  Building connecting fairway sections...")

    # Section: ramp top to loop entry
    ramp_top_y = 0.5 + RAMP_LENGTH  # 1.5
    loop_entry_y = SEG_LOOP_CENTER_Y - LOOP_RADIUS - 0.1
    z_ramp_top = RAMP_RISE
    build_flat_fairway_section(ramp_top_y, loop_entry_y, TEE_Z + z_ramp_top,
                               TEE_Z + z_ramp_top, "RampToLoop")

    # Section: loop exit to windmill
    loop_exit_y = SEG_LOOP_CENTER_Y + LOOP_RADIUS + 0.1
    wm_entry_y = SEG_WINDMILL_Y - WM_BASE_RADIUS - 0.1
    build_flat_fairway_section(loop_exit_y, wm_entry_y, TEE_Z + z_ramp_top,
                               TEE_Z + z_ramp_top, "LoopToWindmill")

    # Section: windmill exit to downhill start
    wm_exit_y = SEG_WINDMILL_Y + WM_BASE_RADIUS + 0.1
    build_flat_fairway_section(wm_exit_y, SEG_DOWNHILL_START, TEE_Z + z_ramp_top,
                               TEE_Z + z_ramp_top - 0.05, "WindmillToDownhill")


# ---------------------------------------------------------------------------
# Hole number marker
# ---------------------------------------------------------------------------

def build_hole_marker():
    """Build a small marker/sign showing hole number 5."""
    name = safe_name("HoleMarker")
    remove_if_exists(name)
    print(f"  Building {name}...")

    # Simple sign post
    bm = bmesh.new()

    # Post
    post_w = 0.02
    post_h = 0.4
    v = [
        bm.verts.new((-post_w, -post_w, 0)),
        bm.verts.new((post_w, -post_w, 0)),
        bm.verts.new((post_w, post_w, 0)),
        bm.verts.new((-post_w, post_w, 0)),
        bm.verts.new((-post_w, -post_w, post_h)),
        bm.verts.new((post_w, -post_w, post_h)),
        bm.verts.new((post_w, post_w, post_h)),
        bm.verts.new((-post_w, post_w, post_h)),
    ]
    # Side faces
    bm.faces.new([v[0], v[1], v[5], v[4]])
    bm.faces.new([v[1], v[2], v[6], v[5]])
    bm.faces.new([v[2], v[3], v[7], v[6]])
    bm.faces.new([v[3], v[0], v[4], v[7]])
    bm.faces.new([v[4], v[5], v[6], v[7]])  # top cap

    # Sign board
    sign_w = 0.1
    sign_h = 0.08
    sign_z = post_h - sign_h - 0.02
    sv = [
        bm.verts.new((-sign_w, -0.005, sign_z)),
        bm.verts.new((sign_w, -0.005, sign_z)),
        bm.verts.new((sign_w, -0.005, sign_z + sign_h)),
        bm.verts.new((-sign_w, -0.005, sign_z + sign_h)),
        bm.verts.new((-sign_w, 0.005, sign_z)),
        bm.verts.new((sign_w, 0.005, sign_z)),
        bm.verts.new((sign_w, 0.005, sign_z + sign_h)),
        bm.verts.new((-sign_w, 0.005, sign_z + sign_h)),
    ]
    bm.faces.new([sv[0], sv[1], sv[2], sv[3]])
    bm.faces.new([sv[7], sv[6], sv[5], sv[4]])
    bm.faces.new([sv[0], sv[3], sv[7], sv[4]])
    bm.faces.new([sv[1], sv[5], sv[6], sv[2]])
    bm.faces.new([sv[3], sv[2], sv[6], sv[7]])
    bm.faces.new([sv[0], sv[4], sv[5], sv[1]])

    bm.normal_update()

    marker_x = TEE_X - FAIRWAY_WIDTH / 2.0 - 0.2
    marker_y = TEE_Y + 0.25
    marker_z = TEE_Z

    obj = create_object_from_bmesh(bm, name, (marker_x, marker_y, marker_z))
    assign_material(obj, "WoodDark")
    link_to_collection(obj, f"{PREFIX}_Decorations")
    return obj


# ---------------------------------------------------------------------------
# Main build routine
# ---------------------------------------------------------------------------

def build_hole_5():
    """Master function to build all elements of Hole 5: The Windmill."""

    print("=" * 60)
    print("HOLE 5: THE WINDMILL (Par 4) - SIGNATURE HOLE")
    print("=" * 60)

    # Validate required collections exist
    required_collections = [
        "Hole_5",
        f"{PREFIX}_Fairway",
        f"{PREFIX}_Green",
        f"{PREFIX}_Borders",
        f"{PREFIX}_Obstacles",
        f"{PREFIX}_Decorations",
    ]
    print("\n[1/9] Validating collections...")
    for col_name in required_collections:
        col = bpy.data.collections.get(col_name)
        if col is None:
            print(f"  Collection '{col_name}' not found -- creating it.")
            new_col = bpy.data.collections.new(col_name)
            # Try to parent under Hole_5 if it exists and this is a sub-collection
            if col_name != "Hole_5":
                parent = bpy.data.collections.get("Hole_5")
                if parent:
                    parent.children.link(new_col)
                else:
                    bpy.context.scene.collection.children.link(new_col)
            else:
                bpy.context.scene.collection.children.link(new_col)
        else:
            print(f"  OK: {col_name}")

    # Set scene FPS
    bpy.context.scene.render.fps = FPS
    print(f"\n  Scene FPS set to {FPS}")

    # --- Build fairway sections ---
    print("\n[2/9] Building tee area and ramp...")
    build_tee_area()
    build_ramp()

    # --- Loop-de-loop ---
    print("\n[3/9] Building loop-de-loop...")
    build_loop_de_loop()

    # --- Windmill ---
    print("\n[4/9] Building windmill body...")
    wm_body, (wm_x, wm_y, wm_z) = build_windmill_base()

    print("\n[5/9] Building windmill blades with animation driver...")
    build_windmill_blades(wm_x, wm_y, wm_z)

    # --- Connecting fairway and downhill ---
    print("\n[6/9] Building connecting fairways and downhill slope...")
    build_connecting_fairways()
    build_downhill_section()

    # --- Green, cup, flag ---
    print("\n[7/9] Building green, cup, and flag...")
    build_green()
    build_cup()
    build_flag_pin()

    # --- Borders ---
    print("\n[8/9] Building border rails...")
    build_all_borders()

    # --- Decorations ---
    print("\n[9/9] Building decorations...")
    build_tulip_beds(wm_x, wm_y, wm_z)
    build_decorative_pond(wm_x, wm_y, wm_z)
    build_hole_marker()

    # Summary
    h5_objects = []
    for col_name in required_collections:
        col = bpy.data.collections.get(col_name)
        if col:
            h5_objects.extend(list(col.objects))

    print("\n" + "=" * 60)
    print(f"HOLE 5 BUILD COMPLETE")
    print(f"  Total objects created: {len(h5_objects)}")
    for col_name in required_collections[1:]:  # skip parent collection
        col = bpy.data.collections.get(col_name)
        count = len(col.objects) if col else 0
        print(f"    {col_name}: {count} objects")
    print(f"  Windmill animation: {REVOLUTION_SECONDS}s per revolution ({REVOLUTION_FRAMES} frames)")
    print(f"  Hole length: {GREEN_Y - TEE_Y:.1f}m  |  Drop: {abs(GREEN_Z - TEE_Z):.1f}m")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_hole_5()
else:
    # When run via Blender's text editor or exec()
    build_hole_5()
