# ADR-005: Material System

## Status

Accepted

## Date

2026-02-15

## Context

The mini golf course requires a cohesive material system covering diverse surfaces: artificial turf, natural stone, wood, water, metal, glass/acrylic, concrete, and vegetation. The PRD specifies a "naturalistic English garden aesthetic" with PBR (Physically Based Rendering) materials for all surfaces.

Materials must work across two render engines (EEVEE for preview, Cycles for final output -- see ADR-010). They must also support the golden hour lighting specified in the PRD without requiring per-material adjustments when switching light rigs.

Key surface types:
- Artificial turf (fairways, greens, tee areas -- with variation between them)
- Natural stone (retaining walls, borders, stepping stones, tunnel)
- Wood (bridge, windmill, timber sleepers, signage)
- Water (ponds, streams, waterfall -- animated, see ADR-011)
- Metal (flagpoles, support frames, spinners)
- Glass/Acrylic (loop-de-loop tube, stepping stone enclosures)
- Concrete (pathway surfaces, pads)
- Earth/Soil (exposed terrain, planting beds)

## Decision

Implement a **shared PBR material library** using Blender's node-based material system, with procedural textures where possible and image textures from PolyHaven where procedural generation cannot achieve the required quality.

### Material Library Structure

All materials are stored in a dedicated fake-user-flagged datablock collection. Each material follows the naming convention `MG_` prefix (MiniGolf):

```
MG_Turf_Fairway       -- Standard fairway artificial turf
MG_Turf_Green         -- Shorter, tighter green surface
MG_Turf_Tee           -- Tee area marking
MG_Stone_Retaining    -- Natural stone retaining walls
MG_Stone_Border       -- Border rail stone
MG_Stone_Cobble       -- Pathway cobblestones
MG_Stone_Stepping     -- Stepping stone platforms
MG_Wood_Bridge        -- Wooden bridge planks
MG_Wood_Windmill      -- Windmill timber
MG_Wood_Sleeper       -- Timber sleeper retaining
MG_Water_Pond         -- Still water surface
MG_Water_Stream       -- Flowing water
MG_Water_Waterfall    -- Cascading water
MG_Metal_Steel        -- Steel supports, flagpoles
MG_Metal_Spinner      -- Pinwheel spinner material
MG_Glass_Loop         -- Transparent loop tube
MG_Concrete_Path      -- Pathway surface
MG_Earth_Soil         -- Exposed soil in beds
MG_Earth_Mulch        -- Bark mulch ground cover
```

### Procedural Materials

#### Artificial Turf (MG_Turf_Fairway)

- **Base Color**: Noise Texture (scale 200, detail 8) mixed with Voronoi Texture (scale 150) to create fine grass-blade variation. Base green hue (HSV: 0.33, 0.7, 0.4) with subtle yellow-green variation.
- **Roughness**: 0.85 (matte artificial surface)
- **Normal**: Noise texture driving a bump node (strength 0.15) for micro-surface variation.
- **Green Variant**: Same node group with tighter noise scale (300) and slightly darker base color to indicate shorter turf.

#### Natural Stone (MG_Stone_Retaining)

- **Base Color**: Voronoi Texture (Crackle mode, scale 3) for stone block pattern, mixed with Noise Texture for color variation. Warm gray palette (HSV: 0.08, 0.1, 0.5).
- **Roughness**: 0.75-0.9 mapped by Voronoi cells for per-stone variation.
- **Normal**: Voronoi-based bump for inter-stone grooves (strength 0.4) plus Noise Texture for stone surface roughness (strength 0.1).
- **Displacement**: Optional true displacement in Cycles for stone face relief.

#### Metal (MG_Metal_Steel)

- **Base Color**: (0.6, 0.6, 0.6) neutral steel gray
- **Metallic**: 1.0
- **Roughness**: 0.3 (brushed finish)
- **Normal**: Anisotropic noise for brushed metal appearance

### Image-Based Materials

#### Wood (MG_Wood_Bridge)

- **Source**: PolyHaven wood plank texture (e.g., `wood_planks_009`) or equivalent CC0 asset.
- **Maps**: Diffuse, Roughness, Normal, Displacement (4 texture images per material)
- **UV Mapping**: Box projection for large surfaces, manual UV for featured objects.
- **Rationale**: Procedural wood grain that looks convincing at close range is extremely difficult. Image textures provide realistic grain, knots, and weathering.

#### Cobblestone (MG_Stone_Cobble)

- **Source**: PolyHaven cobblestone texture for pathway surfaces where procedural stone patterns lack the organic feel of real cobble.
- **Maps**: Diffuse, Roughness, Normal, Displacement

### Node Groups

Shared functionality is encapsulated in node groups:

1. **MG_WeatheringMix**: Adds edge wear and moss/dirt accumulation. Inputs: base material, weathering amount (0-1). Uses Ambient Occlusion and Pointiness attribute to drive dirt in crevices and wear on edges.

2. **MG_ColorVariation**: Adds subtle hue/saturation/value shifts driven by Object Info > Random. Prevents identical-looking objects when the same material is applied to multiple stones or planks.

3. **MG_ScaleMapper**: Converts UV coordinates to world-space coordinates for consistent texture scale regardless of object UV layout. Ensures stone blocks are the same visual size on all retaining walls.

### EEVEE/Cycles Compatibility

- All materials use the Principled BSDF shader, which is compatible with both engines.
- Transparent materials (glass) use the `Alpha Blend` blend mode in EEVEE and standard glass in Cycles. A `Is EEVEE` driver switches between simplified and full transparency setups where needed.
- No Cycles-only nodes (e.g., true SSS for vegetation) are used in primary materials. SSS is added as an optional layer that gracefully degrades in EEVEE.

## Consequences

### Positive

- **Consistency**: The `MG_` prefix and shared library ensure all materials are discoverable and follow the same PBR conventions.
- **Reusability**: Node groups (WeatheringMix, ColorVariation, ScaleMapper) reduce duplication and ensure consistent visual treatment across different material types.
- **Engine compatibility**: Principled BSDF foundation works across EEVEE and Cycles without material swapping.
- **Procedural advantage**: Procedural textures (turf, stone, metal) have no resolution limit and tile seamlessly.
- **External asset quality**: PolyHaven image textures for wood and cobblestone provide photorealistic quality where procedural falls short.

### Negative

- **Texture memory**: Image-based materials (wood, cobblestone) add texture memory load. At 2K resolution with 4 maps each, this is ~48MB per material (manageable).
- **External dependency**: PolyHaven textures must be downloaded and packed into the .blend file. If textures are not packed, the file becomes non-portable.
- **Procedural tuning**: Procedural textures require careful parameter tuning to look natural. The turf material in particular needs iteration to avoid looking like noise.
- **Material count**: 18+ materials is a significant library to maintain. Changes to the shared node groups affect all materials that use them.

## Alternatives Considered

### Fully Procedural (No Image Textures)

Generate all materials purely from Blender's procedural texture nodes, eliminating external texture dependencies.

- **Pros**: Zero external files, fully resolution-independent, complete portability.
- **Cons**: Procedural wood grain convincing at close range requires extremely complex node trees (50+ nodes). Cobblestone with natural irregularity is similarly difficult. Development time for high-quality procedural wood and stone exceeds the benefit.
- **Rejected because**: Wood and cobblestone at the required quality level would consume disproportionate development time. Image textures from CC0 sources provide better results faster.

### Fully Image-Based (Texture Painting)

Use image textures for all surfaces, including turf and metal, sourced from texture libraries.

- **Pros**: Consistent workflow for all materials. Predictable visual results.
- **Cons**: Turf texture tiling is visible at the scale of the course (15m x 10m). Stone retaining walls need per-wall UV mapping to avoid seam artifacts. Texture memory grows significantly with full image-based approach. UV mapping for every unique surface adds substantial time.
- **Rejected because**: Procedural textures for turf, stone, and metal tile perfectly at any scale and eliminate UV mapping for simple surfaces. The hybrid approach leverages each technique's strengths.

### Substance Painter Export

Create materials in Substance Painter and export PBR texture sets for Blender.

- **Pros**: Industry-standard material authoring. Powerful painting and masking tools.
- **Cons**: Requires Substance Painter license. Adds an external dependency to the workflow. Exported textures are fixed-resolution (not procedural). Round-tripping between Substance and Blender for edits adds friction.
- **Rejected because**: The project scope (a single Blender scene) does not justify introducing an external material authoring tool. Blender's native node system covers all requirements.
