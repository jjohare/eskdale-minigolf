"""
apply_pbr_landscaping.py

Enhances all existing PBR materials in the mini golf scene with proper
Principled BSDF node setups using procedural textures, then adds
landscaping elements (rocks, shrubs, trees, flowers, pathways) to the
scene's existing empty collections.

Designed to run inside Blender's Python environment (bpy).

Coordinate system (ADR-007):
  - 1 BU = 1 meter
  - Z = 0 at top (Hole 1), descending to Z ~ -3.0 at base (Hole 9)
  - X = long axis (15m), Y = short axis (10m)
  - Origin at Hole 1 tee (top-left corner)

Tier elevations:
  Tier 1 (H1-H2): Z =  0.0
  Tier 2 (H2-H3): Z = -0.3
  Tier 3 (H3-H4): Z = -0.6
  Tier 4 (H4-H5): Z = -1.1
  Tier 5 (H5-H6): Z = -1.6
  Tier 6 (H6-H7): Z = -2.0
  Tier 7 (H7-H8): Z = -2.3
  Base   (H9):    Z = -2.7
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector, noise


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def get_or_create_collection(name, parent=None):
    """Return existing collection by name, or create it under parent."""
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    target = parent if parent else bpy.context.scene.collection
    target.children.link(col)
    return col


def link_obj_to_collection(obj, collection):
    """Link an object into a collection, removing from others."""
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)


def get_or_create_material(name):
    """Return existing material or create a new one."""
    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
    else:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    return mat


def clear_nodes(mat):
    """Remove all nodes from a material's node tree."""
    mat.use_nodes = True
    tree = mat.node_tree
    for node in list(tree.nodes):
        tree.nodes.remove(node)
    return tree


def add_principled(tree, location=(0, 0)):
    """Add a Principled BSDF node and Material Output, connect them."""
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = location

    output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (location[0] + 400, location[1])

    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return bsdf, output


def add_noise_texture(tree, location=(-600, 0), scale=50.0, detail=6.0,
                      roughness=0.5):
    """Add a Noise Texture node with common settings."""
    noise_tex = tree.nodes.new('ShaderNodeTexNoise')
    noise_tex.location = location
    noise_tex.inputs['Scale'].default_value = scale
    noise_tex.inputs['Detail'].default_value = detail
    noise_tex.inputs['Roughness'].default_value = roughness
    return noise_tex


def add_voronoi_texture(tree, location=(-600, 0), scale=5.0,
                        feature='F1'):
    """Add a Voronoi Texture node."""
    voronoi = tree.nodes.new('ShaderNodeTexVoronoi')
    voronoi.location = location
    voronoi.inputs['Scale'].default_value = scale
    if hasattr(voronoi, 'feature'):
        voronoi.feature = feature
    return voronoi


def add_wave_texture(tree, location=(-600, 0), scale=3.0,
                     wave_type='BANDS', distortion=2.0):
    """Add a Wave Texture node."""
    wave = tree.nodes.new('ShaderNodeTexWave')
    wave.location = location
    wave.wave_type = wave_type
    wave.inputs['Scale'].default_value = scale
    wave.inputs['Distortion'].default_value = distortion
    return wave


def add_mapping_and_texcoord(tree, location=(-1000, 0)):
    """Add Texture Coordinate -> Mapping node pair."""
    tex_coord = tree.nodes.new('ShaderNodeTexCoord')
    tex_coord.location = location

    mapping = tree.nodes.new('ShaderNodeMapping')
    mapping.location = (location[0] + 200, location[1])

    tree.links.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    return tex_coord, mapping


def add_bump_node(tree, location=(-200, -300), strength=0.3):
    """Add a Bump node."""
    bump = tree.nodes.new('ShaderNodeBump')
    bump.location = location
    bump.inputs['Strength'].default_value = strength
    return bump


def add_mix_rgb(tree, location=(-300, 0), fac=0.5,
                blend_type='MIX'):
    """Add a Mix node (color)."""
    mix = tree.nodes.new('ShaderNodeMix')
    mix.location = location
    mix.data_type = 'RGBA'
    mix.blend_type = blend_type
    mix.inputs['Factor'].default_value = fac
    return mix


def add_color_ramp(tree, location=(-400, 0)):
    """Add a Color Ramp node."""
    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.location = location
    return ramp


def set_principled_input(bsdf, name, value):
    """Safely set an input on the Principled BSDF."""
    if name in bsdf.inputs:
        inp = bsdf.inputs[name]
        if hasattr(value, '__len__') and not isinstance(value, str):
            inp.default_value = value
        else:
            inp.default_value = value


# ---------------------------------------------------------------------------
# TASK 1: Material Enhancement
# ---------------------------------------------------------------------------

def enhance_artificial_turf():
    """ArtificialTurf: fine noise for grass blade variation."""
    print("[MAT] Enhancing ArtificialTurf...")
    mat = get_or_create_material("ArtificialTurf")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.15, 0.45, 0.12, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.8)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1000, 0))

    noise1 = add_noise_texture(tree, (-600, 200), scale=120.0, detail=8.0,
                               roughness=0.6)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    noise2 = add_noise_texture(tree, (-600, 0), scale=300.0, detail=4.0,
                               roughness=0.4)
    tree.links.new(mapping.outputs['Vector'], noise2.inputs['Vector'])

    mix = add_mix_rgb(tree, (-200, 100), fac=0.3)
    mix.inputs['A'].default_value = (0.15, 0.45, 0.12, 1.0)
    mix.inputs['B'].default_value = (0.12, 0.38, 0.08, 1.0)
    tree.links.new(noise1.outputs['Fac'], mix.inputs['Factor'])
    tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])

    bump = add_bump_node(tree, (-50, -200), strength=0.15)
    tree.links.new(noise2.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_putting_green():
    """PuttingGreen: slightly brighter, smoother surface."""
    print("[MAT] Enhancing PuttingGreen...")
    mat = get_or_create_material("PuttingGreen")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.1, 0.5, 0.1, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.7)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1000, 0))

    noise1 = add_noise_texture(tree, (-600, 200), scale=200.0, detail=6.0,
                               roughness=0.5)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    mix = add_mix_rgb(tree, (-200, 100), fac=0.2)
    mix.inputs['A'].default_value = (0.1, 0.5, 0.1, 1.0)
    mix.inputs['B'].default_value = (0.13, 0.55, 0.08, 1.0)
    tree.links.new(noise1.outputs['Fac'], mix.inputs['Factor'])
    tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])

    noise_bump = add_noise_texture(tree, (-600, -200), scale=350.0,
                                   detail=4.0)
    tree.links.new(mapping.outputs['Vector'], noise_bump.inputs['Vector'])
    bump = add_bump_node(tree, (-50, -200), strength=0.08)
    tree.links.new(noise_bump.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_stone_border():
    """StoneBorder: Voronoi-driven stone pattern."""
    print("[MAT] Enhancing StoneBorder...")
    mat = get_or_create_material("StoneBorder")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.5, 0.48, 0.45, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.85)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1200, 0))

    voronoi = add_voronoi_texture(tree, (-800, 200), scale=4.0)
    tree.links.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])

    noise1 = add_noise_texture(tree, (-800, 0), scale=15.0, detail=5.0)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    mix = add_mix_rgb(tree, (-400, 100), fac=0.4)
    mix.inputs['A'].default_value = (0.5, 0.48, 0.45, 1.0)
    mix.inputs['B'].default_value = (0.42, 0.40, 0.36, 1.0)
    tree.links.new(voronoi.outputs['Distance'], mix.inputs['Factor'])
    tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])

    bump = add_bump_node(tree, (-50, -200), strength=0.4)
    tree.links.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_natural_stone():
    """NaturalStone: rough rock surface with Voronoi cells."""
    print("[MAT] Enhancing NaturalStone...")
    mat = get_or_create_material("NaturalStone")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Roughness', 0.9)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1200, 0))

    voronoi = add_voronoi_texture(tree, (-800, 300), scale=3.0)
    tree.links.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])

    noise1 = add_noise_texture(tree, (-800, 100), scale=8.0, detail=6.0)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    mix1 = add_mix_rgb(tree, (-500, 200), fac=0.5)
    mix1.inputs['A'].default_value = (0.52, 0.50, 0.48, 1.0)
    mix1.inputs['B'].default_value = (0.40, 0.35, 0.28, 1.0)
    tree.links.new(voronoi.outputs['Distance'], mix1.inputs['Factor'])

    mix2 = add_mix_rgb(tree, (-200, 100), fac=0.3)
    tree.links.new(mix1.outputs['Result'], mix2.inputs['A'])
    mix2.inputs['B'].default_value = (0.55, 0.52, 0.50, 1.0)
    tree.links.new(noise1.outputs['Fac'], mix2.inputs['Factor'])
    tree.links.new(mix2.outputs['Result'], bsdf.inputs['Base Color'])

    bump = add_bump_node(tree, (-50, -300), strength=0.6)
    tree.links.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_wood_material(mat_name, base_color, dark_color, roughness_val):
    """Generic wood material with Wave texture grain pattern."""
    print(f"[MAT] Enhancing {mat_name}...")
    mat = get_or_create_material(mat_name)
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Roughness', roughness_val)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1200, 0))

    wave = add_wave_texture(tree, (-800, 200), scale=5.0,
                            wave_type='BANDS', distortion=3.0)
    wave.inputs['Detail'].default_value = 4.0
    wave.inputs['Detail Scale'].default_value = 1.5
    tree.links.new(mapping.outputs['Vector'], wave.inputs['Vector'])

    noise1 = add_noise_texture(tree, (-800, 0), scale=20.0, detail=4.0)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    mix = add_mix_rgb(tree, (-400, 100), fac=0.5)
    mix.inputs['A'].default_value = (*base_color, 1.0)
    mix.inputs['B'].default_value = (*dark_color, 1.0)
    tree.links.new(wave.outputs['Fac'], mix.inputs['Factor'])

    mix2 = add_mix_rgb(tree, (-200, 100), fac=0.15)
    tree.links.new(mix.outputs['Result'], mix2.inputs['A'])
    mix2.inputs['B'].default_value = (
        base_color[0] * 0.7, base_color[1] * 0.6, base_color[2] * 0.5, 1.0
    )
    tree.links.new(noise1.outputs['Fac'], mix2.inputs['Factor'])
    tree.links.new(mix2.outputs['Result'], bsdf.inputs['Base Color'])

    bump = add_bump_node(tree, (-50, -200), strength=0.2)
    tree.links.new(wave.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_wood_rail():
    enhance_wood_material("WoodRail",
                          base_color=(0.55, 0.35, 0.15),
                          dark_color=(0.40, 0.22, 0.08),
                          roughness_val=0.65)


def enhance_wood_dark():
    enhance_wood_material("WoodDark",
                          base_color=(0.25, 0.15, 0.05),
                          dark_color=(0.15, 0.08, 0.02),
                          roughness_val=0.7)


def enhance_water():
    """Water: transparent with animated wave displacement."""
    print("[MAT] Enhancing Water...")
    mat = get_or_create_material("Water")
    tree = clear_nodes(mat)

    mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else None
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'BLENDED'

    bsdf, out = add_principled(tree, location=(300, 0))
    set_principled_input(bsdf, 'Base Color', (0.05, 0.15, 0.3, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.1)
    set_principled_input(bsdf, 'Transmission Weight', 0.8)
    set_principled_input(bsdf, 'IOR', 1.33)
    set_principled_input(bsdf, 'Specular IOR Level', 0.8)
    # Fallback for older Blender API names
    set_principled_input(bsdf, 'Transmission', 0.8)
    set_principled_input(bsdf, 'Specular', 0.8)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1200, 0))

    wave1 = add_wave_texture(tree, (-800, 300), scale=8.0,
                             wave_type='BANDS', distortion=1.5)
    wave1.inputs['Detail'].default_value = 3.0
    tree.links.new(mapping.outputs['Vector'], wave1.inputs['Vector'])

    wave2 = add_wave_texture(tree, (-800, 100), scale=12.0,
                             wave_type='RINGS', distortion=1.0)
    wave2.inputs['Detail'].default_value = 2.0
    tree.links.new(mapping.outputs['Vector'], wave2.inputs['Vector'])

    mix_waves = add_mix_rgb(tree, (-500, 200), fac=0.5)
    tree.links.new(wave1.outputs['Fac'], mix_waves.inputs['A'])
    tree.links.new(wave2.outputs['Fac'], mix_waves.inputs['B'])

    bump = add_bump_node(tree, (0, -200), strength=0.15)
    tree.links.new(mix_waves.outputs['Result'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    # Animate wave offset with a driver for continuous motion
    try:
        wave1.inputs['Phase Offset'].default_value = 0.0
        drv = wave1.inputs['Phase Offset'].driver_add('default_value')
        drv.driver.type = 'SCRIPTED'
        drv.driver.expression = 'frame / 24.0'

        wave2.inputs['Phase Offset'].default_value = 0.0
        drv2 = wave2.inputs['Phase Offset'].driver_add('default_value')
        drv2.driver.type = 'SCRIPTED'
        drv2.driver.expression = 'frame / 36.0'
    except Exception as e:
        print(f"  [WARN] Could not add wave animation driver: {e}")


def enhance_dirt_soil():
    """DirtSoil: earthy brown with noise variation."""
    print("[MAT] Enhancing DirtSoil...")
    mat = get_or_create_material("DirtSoil")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.35, 0.25, 0.15, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.95)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1000, 0))

    noise1 = add_noise_texture(tree, (-600, 200), scale=30.0, detail=6.0,
                               roughness=0.7)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    noise2 = add_noise_texture(tree, (-600, 0), scale=80.0, detail=3.0)
    tree.links.new(mapping.outputs['Vector'], noise2.inputs['Vector'])

    mix = add_mix_rgb(tree, (-200, 100), fac=0.35)
    mix.inputs['A'].default_value = (0.35, 0.25, 0.15, 1.0)
    mix.inputs['B'].default_value = (0.28, 0.18, 0.10, 1.0)
    tree.links.new(noise1.outputs['Fac'], mix.inputs['Factor'])
    tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])

    bump = add_bump_node(tree, (-50, -200), strength=0.25)
    tree.links.new(noise2.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_pathway_concrete():
    """PathwayConcrete: grey concrete with noise bump."""
    print("[MAT] Enhancing PathwayConcrete...")
    mat = get_or_create_material("PathwayConcrete")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.6, 0.58, 0.55, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.8)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1000, 0))

    noise1 = add_noise_texture(tree, (-600, 200), scale=40.0, detail=5.0,
                               roughness=0.6)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    mix = add_mix_rgb(tree, (-200, 100), fac=0.15)
    mix.inputs['A'].default_value = (0.6, 0.58, 0.55, 1.0)
    mix.inputs['B'].default_value = (0.52, 0.50, 0.47, 1.0)
    tree.links.new(noise1.outputs['Fac'], mix.inputs['Factor'])
    tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])

    noise_bump = add_noise_texture(tree, (-600, -200), scale=100.0,
                                   detail=4.0)
    tree.links.new(mapping.outputs['Vector'], noise_bump.inputs['Vector'])
    bump = add_bump_node(tree, (-50, -200), strength=0.2)
    tree.links.new(noise_bump.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_simple_material(mat_name, base_color, roughness, metallic=0.0,
                            extra_settings=None):
    """Build a simple Principled BSDF material with solid color."""
    print(f"[MAT] Enhancing {mat_name}...")
    mat = get_or_create_material(mat_name)
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (*base_color, 1.0))
    set_principled_input(bsdf, 'Roughness', roughness)
    set_principled_input(bsdf, 'Metallic', metallic)

    if extra_settings:
        for key, val in extra_settings.items():
            set_principled_input(bsdf, key, val)

    return mat, tree, bsdf, out


def enhance_cup_black():
    enhance_simple_material("CupBlack",
                            base_color=(0.02, 0.02, 0.02),
                            roughness=0.3, metallic=0.3)


def enhance_windmill_blade():
    enhance_simple_material("WindmillBlade",
                            base_color=(0.2, 0.15, 0.1),
                            roughness=0.5)


def enhance_windmill_body():
    enhance_simple_material("WindmillBody",
                            base_color=(0.85, 0.82, 0.75),
                            roughness=0.7)


def enhance_transparent_tube():
    """TransparentTube: glass-like material."""
    print("[MAT] Enhancing TransparentTube...")
    mat = get_or_create_material("TransparentTube")
    tree = clear_nodes(mat)

    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'BLEND'
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'BLENDED'

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.9, 0.95, 1.0, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.05)
    set_principled_input(bsdf, 'Transmission Weight', 0.95)
    set_principled_input(bsdf, 'IOR', 1.5)
    # Fallback names
    set_principled_input(bsdf, 'Transmission', 0.95)
    set_principled_input(bsdf, 'Alpha', 0.3)


def enhance_metal_pin():
    enhance_simple_material("MetalPin",
                            base_color=(0.8, 0.8, 0.8),
                            roughness=0.2, metallic=1.0)


def enhance_red_paint():
    enhance_simple_material("RedPaint",
                            base_color=(0.8, 0.1, 0.05),
                            roughness=0.4)


def enhance_white_paint():
    enhance_simple_material("WhitePaint",
                            base_color=(0.9, 0.9, 0.9),
                            roughness=0.35)


def enhance_golf_ball_white():
    """GolfBallWhite: slightly textured white ball surface."""
    print("[MAT] Enhancing GolfBallWhite...")
    mat = get_or_create_material("GolfBallWhite")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.95, 0.95, 0.95, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.35)

    # Dimple pattern using Voronoi
    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1000, 0))

    voronoi = add_voronoi_texture(tree, (-600, -200), scale=60.0)
    tree.links.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])

    bump = add_bump_node(tree, (-50, -200), strength=0.08)
    tree.links.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def enhance_all_materials():
    """Run all material enhancements."""
    print("=" * 60)
    print("TASK 1: Enhancing PBR Materials")
    print("=" * 60)

    enhance_artificial_turf()
    enhance_putting_green()
    enhance_stone_border()
    enhance_natural_stone()
    enhance_wood_rail()
    enhance_wood_dark()
    enhance_water()
    enhance_dirt_soil()
    enhance_pathway_concrete()
    enhance_cup_black()
    enhance_windmill_blade()
    enhance_windmill_body()
    enhance_transparent_tube()
    enhance_metal_pin()
    enhance_red_paint()
    enhance_white_paint()
    enhance_golf_ball_white()

    print(f"[MAT] All 17 materials enhanced.")


# ---------------------------------------------------------------------------
# TASK 2: Landscaping
# ---------------------------------------------------------------------------

# Tier positions for placing landscaping elements (approximate centers).
# Based on the switchback layout in the PRD.
# Format: (x, y, z)
TIER_POSITIONS = {
    'tier1': (3.0, 1.5, 0.0),      # H1-H2 area
    'tier2': (3.0, 3.5, -0.3),     # H3 area
    'tier3': (3.0, 5.0, -0.6),     # H4 area
    'tier4': (6.0, 5.0, -1.1),     # H5 windmill area
    'tier5': (3.0, 6.5, -1.6),     # H6 area
    'tier6': (3.0, 7.5, -2.0),     # H7 area
    'tier7': (6.0, 8.0, -2.3),     # H8 area
    'tier_base': (6.0, 9.0, -2.7), # H9 area
}

# Specific landmark positions
HOLE1_ENTRANCE = (1.0, 0.5, 0.0)
HOLE5_WINDMILL = (6.5, 5.0, -1.1)


def create_leaf_material():
    """Create a green leaf material with subsurface scattering."""
    print("[MAT] Creating Leaf material...")
    mat = get_or_create_material("Leaf")
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (0.08, 0.35, 0.05, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.6)
    set_principled_input(bsdf, 'Subsurface Weight', 0.15)
    set_principled_input(bsdf, 'Subsurface Color', (0.1, 0.5, 0.02, 1.0))
    # Fallback for older API
    set_principled_input(bsdf, 'Subsurface', 0.15)

    tex_coord, mapping = add_mapping_and_texcoord(tree, (-1000, 0))
    noise1 = add_noise_texture(tree, (-600, 100), scale=25.0, detail=4.0)
    tree.links.new(mapping.outputs['Vector'], noise1.inputs['Vector'])

    mix = add_mix_rgb(tree, (-200, 100), fac=0.25)
    mix.inputs['A'].default_value = (0.08, 0.35, 0.05, 1.0)
    mix.inputs['B'].default_value = (0.12, 0.45, 0.08, 1.0)
    tree.links.new(noise1.outputs['Fac'], mix.inputs['Factor'])
    tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])

    return mat


def create_tulip_material(name, color):
    """Create a tulip petal material."""
    print(f"[MAT] Creating {name} material...")
    mat = get_or_create_material(name)
    tree = clear_nodes(mat)

    bsdf, out = add_principled(tree, location=(200, 0))
    set_principled_input(bsdf, 'Base Color', (*color, 1.0))
    set_principled_input(bsdf, 'Roughness', 0.45)
    set_principled_input(bsdf, 'Subsurface Weight', 0.1)
    set_principled_input(bsdf, 'Subsurface', 0.1)

    return mat


def create_rock(name, location, size, collection):
    """
    Create a rough rock mesh using icosphere with randomized vertices.
    """
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(name, mesh)
    link_obj_to_collection(obj, collection)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=size)

    # Displace vertices for organic shape
    random.seed(hash(name))
    for v in bm.verts:
        displacement = random.uniform(-0.3, 0.3) * size
        v.co += v.normal * displacement
        # Add some asymmetry
        v.co.x += random.uniform(-0.1, 0.1) * size
        v.co.y += random.uniform(-0.1, 0.1) * size

    bm.to_mesh(mesh)
    bm.free()

    mesh.update()
    obj.location = location

    # Assign NaturalStone material
    stone_mat = get_or_create_material("NaturalStone")
    obj.data.materials.append(stone_mat)

    # Smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj


def create_rock_clusters(collection):
    """Place 5-6 rock clusters at tier transitions."""
    print("[LAND] Creating rock clusters...")

    cluster_positions = [
        # Between Tier 1 and 2
        (1.5, 2.5, -0.15),
        # Between Tier 2 and 3
        (4.5, 4.0, -0.45),
        # Between Tier 3 and 4
        (2.0, 5.5, -0.85),
        # Between Tier 5 and 6
        (5.0, 7.0, -1.8),
        # Between Tier 6 and 7
        (1.5, 8.0, -2.15),
        # Near base
        (4.0, 9.0, -2.5),
    ]

    for ci, center in enumerate(cluster_positions):
        num_rocks = random.randint(3, 6)
        for ri in range(num_rocks):
            offset_x = random.uniform(-0.5, 0.5)
            offset_y = random.uniform(-0.5, 0.5)
            offset_z = random.uniform(-0.05, 0.05)
            rock_size = random.uniform(0.05, 0.2)
            loc = (
                center[0] + offset_x,
                center[1] + offset_y,
                center[2] + offset_z,
            )
            create_rock(f"Rock_C{ci}_R{ri}", loc, rock_size, collection)

    print(f"  Created 6 rock clusters.")


def create_shrub(name, location, radius, collection, material):
    """Create a simple shrub as a displaced sphere."""
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(name, mesh)
    link_obj_to_collection(obj, collection)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=radius)

    # Slight organic displacement
    random.seed(hash(name) + 42)
    for v in bm.verts:
        displacement = random.uniform(-0.15, 0.15) * radius
        v.co += v.normal * displacement

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj.location = location
    obj.data.materials.append(material)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj


def create_shrubs(collection):
    """Place 8-10 ornamental shrubs in planting beds between holes."""
    print("[LAND] Creating ornamental shrubs...")
    leaf_mat = create_leaf_material()

    shrub_positions = [
        # Along Tier 1 edges
        (0.5, 1.0, 0.0, 0.25),
        (5.5, 1.0, 0.0, 0.3),
        # Between H2 and H3
        (1.0, 3.0, -0.3, 0.2),
        (5.0, 3.0, -0.3, 0.35),
        # Near H4 spiral
        (1.5, 5.0, -0.6, 0.3),
        # Between H5 and H6
        (2.0, 6.0, -1.35, 0.25),
        (5.5, 6.5, -1.6, 0.2),
        # Near H7
        (1.0, 7.5, -2.0, 0.3),
        # Near H9
        (7.0, 8.5, -2.5, 0.25),
        (8.0, 9.0, -2.7, 0.2),
    ]

    for i, (x, y, z, r) in enumerate(shrub_positions):
        create_shrub(f"Shrub_{i:02d}", (x, y, z), r, collection, leaf_mat)

    print(f"  Created {len(shrub_positions)} shrubs.")


def create_tree(name, location, trunk_height, crown_radius, crown_type,
                collection):
    """
    Create a simple ornamental tree: cylinder trunk + sphere/cone crown.
    """
    print(f"  Creating tree: {name}")
    trunk_radius = 0.05

    # --- Trunk ---
    bpy.ops.mesh.primitive_cylinder_add(
        radius=trunk_radius,
        depth=trunk_height,
        location=(
            location[0],
            location[1],
            location[2] + trunk_height / 2.0,
        ),
    )
    trunk = bpy.context.active_object
    trunk.name = f"{name}_Trunk"

    wood_mat = get_or_create_material("WoodDark")
    trunk.data.materials.append(wood_mat)

    for poly in trunk.data.polygons:
        poly.use_smooth = True

    link_obj_to_collection(trunk, collection)

    # --- Crown ---
    crown_z = location[2] + trunk_height + crown_radius * 0.6

    if crown_type == 'SPHERE':
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=crown_radius,
            segments=16, ring_count=12,
            location=(location[0], location[1], crown_z),
        )
    else:  # CONE
        bpy.ops.mesh.primitive_cone_add(
            radius1=crown_radius,
            radius2=0.02,
            depth=crown_radius * 2.0,
            location=(location[0], location[1], crown_z),
        )

    crown = bpy.context.active_object
    crown.name = f"{name}_Crown"

    leaf_mat = get_or_create_material("Leaf")
    crown.data.materials.append(leaf_mat)

    for poly in crown.data.polygons:
        poly.use_smooth = True

    link_obj_to_collection(crown, collection)

    return trunk, crown


def create_trees(collection):
    """Place 3-4 small ornamental trees at visual focal points."""
    print("[LAND] Creating ornamental trees...")

    tree_specs = [
        # Near course entrance (Hole 1)
        ("Tree_Entrance", (0.3, 0.3, 0.0), 0.5, 0.4, 'SPHERE'),
        # Midway rest area (between H4 and H5)
        ("Tree_Midway", (4.0, 4.5, -0.85), 0.55, 0.45, 'SPHERE'),
        # Near H7 Japanese garden
        ("Tree_JapaneseMaple", (1.0, 7.0, -2.0), 0.6, 0.5, 'SPHERE'),
        # Course exit near H9
        ("Tree_Exit", (8.0, 9.5, -2.7), 0.5, 0.35, 'CONE'),
    ]

    for name, loc, trunk_h, crown_r, crown_type in tree_specs:
        create_tree(name, loc, trunk_h, crown_r, crown_type, collection)

    print(f"  Created {len(tree_specs)} trees.")


def create_tulip(name, location, material, collection):
    """Create a single tulip: stem (thin cylinder) + bud (cone)."""
    stem_h = 0.05
    stem_r = 0.003
    bud_r = 0.015
    bud_h = 0.03

    # Stem
    bpy.ops.mesh.primitive_cylinder_add(
        radius=stem_r,
        depth=stem_h,
        location=(
            location[0],
            location[1],
            location[2] + stem_h / 2.0,
        ),
    )
    stem = bpy.context.active_object
    stem.name = f"{name}_Stem"

    leaf_mat = get_or_create_material("Leaf")
    stem.data.materials.append(leaf_mat)
    link_obj_to_collection(stem, collection)

    # Bud (inverted cone for tulip shape)
    bpy.ops.mesh.primitive_cone_add(
        radius1=bud_r,
        radius2=0.005,
        depth=bud_h,
        location=(
            location[0],
            location[1],
            location[2] + stem_h + bud_h / 2.0,
        ),
    )
    bud = bpy.context.active_object
    bud.name = f"{name}_Bud"
    bud.data.materials.append(material)

    for poly in bud.data.polygons:
        poly.use_smooth = True

    link_obj_to_collection(bud, collection)

    return stem, bud


def create_flower_beds(collection):
    """
    Scatter tulips around Hole 1 entrance and Hole 5 windmill area.
    """
    print("[LAND] Creating flower beds...")

    tulip_red = create_tulip_material("TulipRed", (0.85, 0.08, 0.05))
    tulip_yellow = create_tulip_material("TulipYellow", (0.95, 0.85, 0.1))
    tulip_purple = create_tulip_material("TulipPurple", (0.55, 0.1, 0.6))

    tulip_mats = [tulip_red, tulip_yellow, tulip_purple]

    random.seed(555)

    # --- Hole 1 entrance flower bed (6-8 tulips) ---
    h1_center = HOLE1_ENTRANCE
    h1_count = 0
    for i in range(8):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0.2, 0.6)
        x = h1_center[0] + math.cos(angle) * dist
        y = h1_center[1] + math.sin(angle) * dist
        z = h1_center[2]
        mat = random.choice(tulip_mats)
        create_tulip(f"Tulip_H1_{i:02d}", (x, y, z), mat, collection)
        h1_count += 1

    print(f"  Hole 1 entrance: {h1_count} tulips")

    # --- Hole 5 windmill flower bed (15-20 tulips) ---
    h5_center = HOLE5_WINDMILL
    h5_count = 0
    for i in range(18):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0.3, 1.0)
        x = h5_center[0] + math.cos(angle) * dist
        y = h5_center[1] + math.sin(angle) * dist
        z = h5_center[2]
        mat = random.choice(tulip_mats)
        create_tulip(f"Tulip_H5_{i:02d}", (x, y, z), mat, collection)
        h5_count += 1

    print(f"  Hole 5 windmill: {h5_count} tulips")
    print(f"  Total tulips: {h1_count + h5_count}")


def create_pathway_section(name, start, end, width, collection):
    """
    Create a flat rectangular pathway between two points.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    angle = math.atan2(dy, dx)
    mid_x = (start[0] + end[0]) / 2.0
    mid_y = (start[1] + end[1]) / 2.0
    mid_z = (start[2] + end[2]) / 2.0

    bpy.ops.mesh.primitive_plane_add(
        size=1.0,
        location=(mid_x, mid_y, mid_z + 0.005),
    )
    pathway = bpy.context.active_object
    pathway.name = name

    pathway.scale = (length, width, 1.0)
    pathway.rotation_euler = (0, 0, angle)

    # Tilt for elevation change
    dz = end[2] - start[2]
    if length > 0:
        pitch = math.atan2(dz, length)
        pathway.rotation_euler.y = -pitch

    concrete_mat = get_or_create_material("PathwayConcrete")
    pathway.data.materials.append(concrete_mat)

    link_obj_to_collection(pathway, collection)
    return pathway


def create_pathways(collection):
    """
    Create pathway sections connecting each hole's green to the next tee.
    Based on the switchback layout from the PRD.
    """
    print("[LAND] Creating pathway sections...")

    # Approximate tee/exit positions for pathway connections.
    # Each entry: (start_point, end_point) representing green exit -> next tee.
    pathway_segments = [
        # H1 green -> H2 tee
        ("Pathway_H1_H2", (4.5, 1.5, 0.0), (5.0, 2.0, 0.0)),
        # H2 green -> H3 tee
        ("Pathway_H2_H3", (5.0, 2.5, -0.15), (5.0, 3.0, -0.3)),
        # H3 green -> H4 tee
        ("Pathway_H3_H4", (1.5, 3.5, -0.3), (1.5, 4.5, -0.6)),
        # H4 green -> H5 tee (down to windmill)
        ("Pathway_H4_H5", (2.5, 5.5, -0.6), (4.5, 5.0, -1.1)),
        # H5 green -> H6 tee
        ("Pathway_H5_H6", (7.5, 5.5, -1.1), (5.5, 6.0, -1.6)),
        # H6 green -> H7 tee
        ("Pathway_H6_H7", (2.0, 6.5, -1.6), (2.0, 7.0, -2.0)),
        # H7 green -> H8 tee
        ("Pathway_H7_H8", (2.0, 8.0, -2.0), (4.0, 8.0, -2.3)),
        # H8 green -> H9 tee
        ("Pathway_H8_H9", (7.0, 8.0, -2.3), (7.0, 8.5, -2.7)),
    ]

    pathway_width = 0.8

    for name, start, end in pathway_segments:
        create_pathway_section(name, start, end, pathway_width, collection)

    print(f"  Created {len(pathway_segments)} pathway sections.")


def create_landscaping():
    """Create all landscaping elements and link to existing collections."""
    print()
    print("=" * 60)
    print("TASK 2: Adding Landscaping Elements")
    print("=" * 60)

    # Get or create the target collections
    rocks_col = get_or_create_collection("Rocks")
    plants_col = get_or_create_collection("Plants")
    flowers_col = get_or_create_collection("Flowers")
    pathways_col = get_or_create_collection("Pathways")

    print(f"[LAND] Target collections: Rocks, Plants, Flowers, Pathways")

    create_rock_clusters(rocks_col)
    create_shrubs(plants_col)
    create_trees(plants_col)
    create_flower_beds(flowers_col)
    create_pathways(pathways_col)


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def main():
    print()
    print("*" * 60)
    print("  Mini Golf PBR Material Enhancement & Landscaping Script")
    print("*" * 60)
    print()

    # Ensure we are in object mode
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    # Set a fixed random seed for reproducible landscaping placement
    random.seed(2026)

    enhance_all_materials()
    create_landscaping()

    # Final summary
    mat_count = len(bpy.data.materials)
    obj_count = len(bpy.data.objects)

    print()
    print("=" * 60)
    print("  COMPLETE")
    print("=" * 60)
    print(f"  Total materials in scene: {mat_count}")
    print(f"  Total objects in scene:   {obj_count}")
    print(f"  Collections populated:    Rocks, Plants, Flowers, Pathways")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    # When executed via Blender's text editor or exec(), run directly
    main()
