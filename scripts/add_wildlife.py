"""Add red squirrels, fell pony, and WAGR improvements to the mini golf course."""
import bpy
import bmesh
import math
from mathutils import Vector


def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        if parent:
            parent.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col


def make_material(name, color, metallic=0.0, roughness=0.8):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_sphere(name, pos, radius, segments=12, col=None, mat=None, scale=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2, radius=radius)
    if scale:
        for v in bm.verts:
            v.co.x *= scale[0]
            v.co.y *= scale[1]
            v.co.z *= scale[2]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = pos
    if mat:
        obj.data.materials.append(mat)
    if col:
        col.objects.link(obj)
    return obj


def make_cone(name, pos, r1, r2, depth, segments=8, col=None, mat=None, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=segments, radius1=r1, radius2=r2, depth=depth)
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = pos
    if rot:
        obj.rotation_euler = rot
    if mat:
        obj.data.materials.append(mat)
    if col:
        col.objects.link(obj)
    return obj


def build_squirrel(name, pos, facing, col, body_mat, tail_mat):
    """Build a red squirrel at given position."""
    parts = []

    # Body
    body = make_sphere(name + "_Body", pos + Vector((0, 0, 0.025)),
                       0.02, 12, col, body_mat, scale=(1.0, 1.5, 0.8))
    body.rotation_euler.z = facing
    parts.append(body)

    # Head
    head = make_sphere(name + "_Head", pos + Vector((0, 0.03, 0.035)),
                       0.012, 10, col, body_mat)
    head.rotation_euler.z = facing
    parts.append(head)

    # Ear tufts
    for side, label in [(-1, "L"), (1, "R")]:
        ear = make_cone(name + "_Ear" + label, pos + Vector((side * 0.008, 0.03, 0.048)),
                        0.003, 0.001, 0.01, 6, col, body_mat)
        ear.rotation_euler.z = facing
        parts.append(ear)

    # Bushy tail (curled up)
    tail = make_sphere(name + "_Tail", pos + Vector((0, -0.03, 0.045)),
                       0.015, 8, col, tail_mat, scale=(0.6, 2.0, 1.0))
    tail.rotation_euler = (0.8, 0, facing)
    parts.append(tail)

    return parts


def build_fell_pony(pos, col):
    """Build a black fell pony."""
    pony_mat = make_material("FellPony_Mat", (0.05, 0.04, 0.04), roughness=0.85)

    # Body
    body = make_sphere("FellPony_Body", pos + Vector((0, 0, 0.08)),
                       0.06, 14, col, pony_mat, scale=(0.9, 1.8, 0.7))

    # Head
    head = make_sphere("FellPony_Head", pos + Vector((0, 0.12, 0.13)),
                       0.025, 10, col, pony_mat, scale=(1.0, 1.5, 1.0))
    head.rotation_euler.x = -0.4

    # 4 legs
    leg_offsets = [(-0.03, -0.05), (0.03, -0.05), (-0.03, 0.05), (0.03, 0.05)]
    for i, (ox, oy) in enumerate(leg_offsets):
        make_cone(f"FellPony_Leg{i}", pos + Vector((ox, oy, 0.035)),
                  0.01, 0.015, 0.07, 8, col, pony_mat)

    # Feathered hooves (wider at base)
    for i, (ox, oy) in enumerate(leg_offsets):
        make_sphere(f"FellPony_Hoof{i}", pos + Vector((ox, oy, 0.005)),
                    0.012, 8, col, pony_mat, scale=(1.2, 1.2, 0.5))

    # Flowing mane
    make_sphere("FellPony_Mane", pos + Vector((0, 0.08, 0.14)),
                0.02, 8, col, pony_mat, scale=(0.3, 3.0, 0.5))

    # Tail (ground-trailing)
    make_sphere("FellPony_Tail", pos + Vector((0, -0.11, 0.04)),
                0.015, 8, col, pony_mat, scale=(0.4, 1.0, 2.5))


def improve_woolpack_materials():
    """Apply proper whitewashed limewash to Eskdale buildings."""
    # Whitewash material for traditional Lake District buildings
    whitewash = make_material("Whitewash_Limewash", (0.95, 0.93, 0.88), roughness=0.9)

    # Slate roof material (blue-grey)
    slate_roof = make_material("CumbrianSlate_Roof", (0.3, 0.33, 0.38), roughness=0.75)

    # Dark window frames
    dark_frame = make_material("DarkWindowFrame", (0.08, 0.08, 0.1), roughness=0.6)

    # Apply to Woolpack Inn
    for obj in bpy.data.objects:
        n = obj.name
        if "Woolpack_Inn_Walls" in n:
            obj.data.materials.clear()
            obj.data.materials.append(whitewash)
        elif "Woolpack_Inn_Roof" in n:
            obj.data.materials.clear()
            obj.data.materials.append(slate_roof)
        elif "Woolpack_Inn_Win" in n or "Woolpack_Inn_Door" in n:
            obj.data.materials.clear()
            obj.data.materials.append(dark_frame)
        elif "Woolpack_Inn_Chimney" in n:
            obj.data.materials.clear()
            obj.data.materials.append(whitewash)

    # Apply to Boot Watermill
    for obj in bpy.data.objects:
        n = obj.name
        if "BootMill_Walls" in n:
            obj.data.materials.clear()
            obj.data.materials.append(whitewash)
        elif "BootMill_Roof" in n:
            obj.data.materials.clear()
            obj.data.materials.append(slate_roof)
        elif "BootMill_Door" in n or "BootMill_Window" in n:
            obj.data.materials.clear()
            obj.data.materials.append(dark_frame)

    # Apply to Muncaster Castle - pink granite
    pink_granite = make_material("PinkGranite", (0.72, 0.5, 0.45), roughness=0.7)
    for obj in bpy.data.objects:
        if "MuncasterTower_Body" in obj.name or "MuncasterTower_Cren" in obj.name:
            obj.data.materials.clear()
            obj.data.materials.append(pink_granite)

    print("Materials updated: Whitewash, Slate, Pink Granite applied")


def add_heather_patches():
    """Add purple heather ground cover on fell sections."""
    wild_col = get_or_create_collection("Wildlife")
    heather_mat = make_material("Heather_Purple", (0.45, 0.15, 0.5), roughness=0.95)

    # Heather patches on higher terrain areas
    positions = [
        Vector((0.5, 1.5, 0.05)), Vector((9.0, 2.0, 0.05)),
        Vector((8.5, 5.5, -0.5)), Vector((0.5, 8.0, -0.9)),
        Vector((7.5, 10.0, -1.3)), Vector((0.5, 13.0, -1.8)),
    ]
    for i, pos in enumerate(positions):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.15)
        for v in bm.verts:
            v.co.z *= 0.1  # Very flat
            v.co.x *= 1.0 + (i % 3) * 0.3
            v.co.y *= 1.0 + ((i + 1) % 3) * 0.3
        mesh = bpy.data.meshes.new(f"Heather_{i}_Mesh")
        bm.to_mesh(mesh)
        bm.free()
        patch = bpy.data.objects.new(f"Heather_Patch_{i}", mesh)
        patch.location = pos
        patch.data.materials.append(heather_mat)
        wild_col.objects.link(patch)

    print(f"{len(positions)} heather patches added")


if __name__ == "__main__":
    wild_col = get_or_create_collection("Wildlife")

    # Materials
    sq_body_mat = make_material("RedSquirrel_Body", (0.6, 0.2, 0.08), roughness=0.9)
    sq_tail_mat = make_material("RedSquirrel_Tail", (0.65, 0.25, 0.1), roughness=0.95)

    # 3 Red Squirrels near woodland areas
    build_squirrel("RedSquirrel_1", Vector((1.2, 2.0, 0.05)), 0.5,
                   wild_col, sq_body_mat, sq_tail_mat)
    build_squirrel("RedSquirrel_2", Vector((6.5, 5.0, -0.4)), -0.3,
                   wild_col, sq_body_mat, sq_tail_mat)
    build_squirrel("RedSquirrel_3", Vector((3.5, 11.0, -1.3)), 1.2,
                   wild_col, sq_body_mat, sq_tail_mat)
    print("3 Red Squirrels placed")

    # Fell Pony on open fell area
    build_fell_pony(Vector((8.5, 4.0, 0.0)), wild_col)
    print("Fell Pony placed")

    # Improve building materials
    improve_woolpack_materials()

    # Add heather patches
    add_heather_patches()

    # Save
    bpy.ops.wm.save_mainfile()
    print("Wildlife and material improvements saved")
