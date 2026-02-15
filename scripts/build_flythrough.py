"""
Flythrough Camera Animation for Mini Golf Course
==================================================
Creates a NURBS-path camera animation that flies through all 9 holes
of the mini golf course in a smooth, cinematic sweep.

Camera path: high entrance overview -> swoop down -> follow course -> finale pullback
Look-at path: tracks slightly ahead along hole centers for natural framing

Run inside Blender:
    exec(open("/home/devuser/workspace/minigolf/scripts/build_flythrough.py").read(), {"__name__": "__main__"})
"""

import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BLEND_FILE = "/home/devuser/workspace/minigolf/minigolf_course.blend"

FPS = 30
TOTAL_FRAMES = 600  # 20 seconds at 30fps
FRAME_START = 1
FRAME_END = 600

RESOLUTION_X = 1280
RESOLUTION_Y = 720
OUTPUT_PATH = "/home/devuser/workspace/minigolf/renders/flythrough/frame_"

# Camera path waypoints (where the camera physically travels)
CAMERA_PATH_POINTS = [
    Vector((1.5, -2.0, 3.0)),     # Start: high above entrance, looking down
    Vector((1.5,  0.0, 1.0)),     # Hole 1: swoop down to eye level
    Vector((5.0,  3.0, 0.8)),     # Hole 2: follow curve east
    Vector((7.0,  5.0, 0.5)),     # Hole 3: pass over bridge
    Vector((3.5,  7.0, 0.3)),     # Hole 4: spiral area
    Vector((5.0, 10.0, 0.2)),     # Hole 5: WINDMILL - get close
    Vector((5.0, 11.0, 0.5)),     # After windmill: pull back
    Vector((3.0, 13.0, -0.5)),    # Hole 6: tunnel hill
    Vector((7.0, 13.5, -1.0)),    # Hole 7: over stepping stones
    Vector((2.0, 14.5, -1.2)),    # Hole 8: ravine lookdown
    Vector((7.0, 14.5, -1.5)),    # Hole 9: finale
    Vector((5.0, 16.0, 2.0)),     # End: pull back and up for overview
]

# Look-at path waypoints (where the camera looks, roughly at hole centers)
LOOKAT_PATH_POINTS = [
    Vector((1.5,  1.0,  0.0)),    # Look at Hole 1 area
    Vector((1.5,  2.0,  0.0)),    # Still looking at Hole 1
    Vector((5.0,  4.5, -0.15)),   # Look at Hole 2 center
    Vector((7.0,  6.0, -0.45)),   # Look at Hole 3 bridge
    Vector((3.5,  8.0, -0.85)),   # Look at Hole 4 spiral
    Vector((5.0, 10.5, -1.35)),   # Look at Hole 5 windmill
    Vector((5.0, 11.5, -1.35)),   # Still on windmill area
    Vector((3.0, 13.5, -1.8)),    # Look at Hole 6 tunnel
    Vector((7.0, 14.0, -2.15)),   # Look at Hole 7 stones
    Vector((2.0, 14.8, -2.5)),    # Look at Hole 8 ravine
    Vector((7.0, 15.0, -2.7)),    # Look at Hole 9 finale
    Vector((5.0, 14.0, -1.5)),    # Final overview look center
]

# Names for created objects
CAM_PATH_NAME = "FlythroughPath"
LOOKAT_PATH_NAME = "FlythroughLookAt"
CAMERA_NAME = "FlythroughCam"
TARGET_NAME = "FlythroughTarget"
COLLECTION_NAME = "Flythrough"

# All flythrough-related object names for cleanup
FLYTHROUGH_OBJECTS = [CAMERA_NAME, TARGET_NAME, CAM_PATH_NAME, LOOKAT_PATH_NAME]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def remove_object(name):
    """Remove an object and its data block if it exists."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return
    # Unlink from all collections
    for col in obj.users_collection:
        col.objects.unlink(obj)
    # Remove associated data
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None:
        if isinstance(data, bpy.types.Curve):
            bpy.data.curves.remove(data)
        elif isinstance(data, bpy.types.Camera):
            bpy.data.cameras.remove(data)


def get_or_create_collection(name):
    """Return existing collection or create and link a new one."""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link_to_collection(obj, collection):
    """Ensure obj is linked to the given collection and unlinked from others."""
    for col in obj.users_collection:
        col.objects.unlink(obj)
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def create_nurbs_path(name, points, collection):
    """Create a NURBS path (CurveData with NURBS spline) from a list of Vector points.

    Uses order 4 for smooth interpolation. Endpoint flag is set so the curve
    passes through the first and last control points.
    """
    curve_data = bpy.data.curves.new(name=name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 64  # high resolution for smooth camera motion

    spline = curve_data.splines.new('NURBS')
    spline.points.add(len(points) - 1)  # one point already exists

    for i, pt in enumerate(points):
        spline.points[i].co = (pt.x, pt.y, pt.z, 1.0)  # w=1 for uniform weight

    spline.order_u = min(4, len(points))  # cubic NURBS
    spline.use_endpoint_u = True          # clamp to endpoints

    obj = bpy.data.objects.new(name, curve_data)
    link_to_collection(obj, collection)
    print(f"  Created NURBS path '{name}' with {len(points)} control points")
    return obj


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_flythrough():
    """Build the complete flythrough camera rig: paths, camera, target, constraints."""

    print("=" * 60)
    print("Building flythrough camera animation")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Cleanup existing flythrough objects
    # ------------------------------------------------------------------
    print("\n[1/7] Cleaning up existing flythrough objects...")
    for name in FLYTHROUGH_OBJECTS:
        if bpy.data.objects.get(name):
            print(f"  Removing existing '{name}'")
            remove_object(name)

    # Remove stale collection if empty
    col = bpy.data.collections.get(COLLECTION_NAME)
    if col is not None and len(col.objects) == 0:
        bpy.data.collections.remove(col)

    # ------------------------------------------------------------------
    # 2. Create collection
    # ------------------------------------------------------------------
    print("\n[2/7] Creating Flythrough collection...")
    fly_col = get_or_create_collection(COLLECTION_NAME)
    print(f"  Collection '{COLLECTION_NAME}' ready")

    # ------------------------------------------------------------------
    # 3. Create camera path (NURBS curve)
    # ------------------------------------------------------------------
    print("\n[3/7] Creating camera path curve...")
    cam_path = create_nurbs_path(CAM_PATH_NAME, CAMERA_PATH_POINTS, fly_col)

    # ------------------------------------------------------------------
    # 4. Create look-at path (NURBS curve)
    # ------------------------------------------------------------------
    print("\n[4/7] Creating look-at target path curve...")
    lookat_path = create_nurbs_path(LOOKAT_PATH_NAME, LOOKAT_PATH_POINTS, fly_col)

    # ------------------------------------------------------------------
    # 5. Create camera and target empty
    # ------------------------------------------------------------------
    print("\n[5/7] Creating camera and target empty...")

    # Camera
    cam_data = bpy.data.cameras.new(name=CAMERA_NAME)
    cam_data.lens = 28          # slightly wide for cinematic feel
    cam_data.clip_start = 0.05
    cam_data.clip_end = 100.0
    cam_data.dof.use_dof = False

    cam_obj = bpy.data.objects.new(CAMERA_NAME, cam_data)
    link_to_collection(cam_obj, fly_col)
    print(f"  Created camera '{CAMERA_NAME}' (28mm lens)")

    # Target empty
    target_obj = bpy.data.objects.new(TARGET_NAME, None)
    target_obj.empty_display_type = 'SPHERE'
    target_obj.empty_display_size = 0.15
    link_to_collection(target_obj, fly_col)
    print(f"  Created target empty '{TARGET_NAME}'")

    # ------------------------------------------------------------------
    # 6. Add constraints and keyframe the Follow Path offsets
    # ------------------------------------------------------------------
    print("\n[6/7] Adding constraints and keyframing animation...")

    # --- Camera Follow Path ---
    con_cam_path = cam_obj.constraints.new(type='FOLLOW_PATH')
    con_cam_path.name = "FollowCameraPath"
    con_cam_path.target = cam_path
    con_cam_path.use_fixed_location = False
    con_cam_path.use_curve_follow = False  # we handle orientation via Track To
    con_cam_path.forward_axis = 'FORWARD_Y'
    con_cam_path.up_axis = 'UP_Z'

    # Keyframe offset: start at 0 (frame 1), end at -TOTAL_FRAMES (frame FRAME_END)
    con_cam_path.offset = 0
    con_cam_path.keyframe_insert(data_path="offset", frame=FRAME_START)
    con_cam_path.offset = -TOTAL_FRAMES
    con_cam_path.keyframe_insert(data_path="offset", frame=FRAME_END)

    # Set interpolation to linear for constant speed along path
    if cam_obj.animation_data and cam_obj.animation_data.action:
        for fc in cam_obj.animation_data.action.fcurves:
            if "offset" in fc.data_path:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'

    print("  Camera 'Follow Path' constraint added and keyframed")

    # --- Camera Track To Target ---
    con_track = cam_obj.constraints.new(type='TRACK_TO')
    con_track.name = "TrackToTarget"
    con_track.target = target_obj
    con_track.track_axis = 'TRACK_NEGATIVE_Z'
    con_track.up_axis = 'UP_Y'
    print("  Camera 'Track To' constraint added -> FlythroughTarget")

    # --- Target Follow Path ---
    con_target_path = target_obj.constraints.new(type='FOLLOW_PATH')
    con_target_path.name = "FollowLookAtPath"
    con_target_path.target = lookat_path
    con_target_path.use_fixed_location = False
    con_target_path.use_curve_follow = False
    con_target_path.forward_axis = 'FORWARD_Y'
    con_target_path.up_axis = 'UP_Z'

    # Same keyframing for target
    con_target_path.offset = 0
    con_target_path.keyframe_insert(data_path="offset", frame=FRAME_START)
    con_target_path.offset = -TOTAL_FRAMES
    con_target_path.keyframe_insert(data_path="offset", frame=FRAME_END)

    if target_obj.animation_data and target_obj.animation_data.action:
        for fc in target_obj.animation_data.action.fcurves:
            if "offset" in fc.data_path:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'

    print("  Target 'Follow Path' constraint added and keyframed")

    # ------------------------------------------------------------------
    # 7. Scene and render settings
    # ------------------------------------------------------------------
    print("\n[7/7] Configuring scene and render settings...")

    scene = bpy.context.scene

    # Frame range and FPS
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.frame_current = FRAME_START
    print(f"  Frame range: {FRAME_START}-{FRAME_END} @ {FPS}fps ({TOTAL_FRAMES / FPS:.0f}s)")

    # Set active camera
    scene.camera = cam_obj
    print(f"  Active camera set to '{CAMERA_NAME}'")

    # Render engine
    scene.render.engine = 'BLENDER_EEVEE'
    print("  Render engine: EEVEE")

    # Resolution
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.resolution_percentage = 100
    print(f"  Resolution: {RESOLUTION_X}x{RESOLUTION_Y}")

    # Output path and format
    scene.render.filepath = OUTPUT_PATH
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.compression = 15
    print(f"  Output: {OUTPUT_PATH}####.png")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    print("\nSaving blend file...")
    bpy.ops.wm.save_mainfile()
    print(f"  Saved: {bpy.data.filepath}")

    print("\n" + "=" * 60)
    print("Flythrough camera animation setup complete!")
    print(f"  Camera path: {len(CAMERA_PATH_POINTS)} waypoints")
    print(f"  Look-at path: {len(LOOKAT_PATH_POINTS)} waypoints")
    print(f"  Duration: {TOTAL_FRAMES} frames ({TOTAL_FRAMES / FPS:.0f}s)")
    print(f"  Render to: {OUTPUT_PATH}")
    print("  To render: bpy.ops.render.render(animation=True)")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_flythrough()
