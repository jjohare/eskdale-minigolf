# ADR-006: Landscaping Approach

## Status

Accepted

## Date

2026-02-15

## Context

The PRD specifies a "naturalistic English garden aesthetic" with extensive landscaping between and around the holes:

- Planting beds with low-maintenance shrubs, ornamental grasses, and seasonal flowers
- Feature trees (small ornamental) at key visual points
- Rock gardens and boulder clusters
- Ground cover plants on slopes between tiers
- Water features integrated with the course (covered in ADR-011)
- LED accent lighting along pathways for evening play
- Specific per-hole landscaping: tulip beds (Hole 5), ferns (Holes 2, 3), alpine plants (Hole 4), wildflowers (Hole 6), water lilies (Hole 7), Japanese maple (Hole 7), colorful flowers (Hole 9)

The landscaping must populate a 15m x 10m area with sufficient density to look naturalistic without overwhelming scene complexity or render times. Individual plant placement for the entire course would be prohibitively time-consuming.

## Decision

Use a **layered approach** combining Geometry Nodes particle scattering for ground cover and grass, a curated asset library for feature plants and rocks, and manual placement for focal-point vegetation.

### Layer 1: Ground Cover and Grass (Geometry Nodes)

1. **Grass System**: A Geometry Nodes modifier (`GN_Grass_Scatter`) on each terrain tier mesh distributes grass blade instances across surfaces. The system uses:
   - **Density Attribute**: A vertex weight paint layer (`grass_density`) on the terrain mesh controls where grass appears (high on flat areas, zero on pathways and fairways).
   - **Blade Instances**: 3-4 grass blade mesh variants (straight, curved, bent) instanced at random rotation and scale. Each blade is 3-5 faces (minimal geometry).
   - **Scale Variation**: Noise Texture drives per-instance scale (0.7x to 1.3x base height) for natural variation.
   - **Color Variation**: An attribute-based color shift applied via the grass material (see ADR-005 MG_ColorVariation node group) for hue variation across the field.

2. **Ground Cover Plants**: A second Geometry Nodes modifier (`GN_Groundcover_Scatter`) distributes low-growing plant clusters (clover, moss patches, small ferns) on slope regions between tiers. Lower density than grass, larger individual instances.

3. **Flower Beds**: Per-hole flower instances scattered within painted regions. Each flower type (tulips, wildflowers, seasonal blooms) is a small mesh instance with a species-specific material.

### Layer 2: Shrubs and Medium Plants (Asset Library)

1. **Asset Source**: A curated set of 8-12 plant models stored in a Blender asset library file (`assets/plants.blend`). Sources:
   - PolyHaven 3D plant assets (CC0 license)
   - Botaniq community edition assets if available
   - Hand-modeled simple shapes for stylized plants where photorealism is not required

2. **Plant Types**:
   - Ornamental grasses (3 variants: tall, medium, compact)
   - Box hedge (modular sections for bordering)
   - Flowering shrubs (2 variants: lavender-style, hydrangea-style)
   - Fern clusters (2 variants: for woodland areas on Holes 2, 3)
   - Alpine succulents (for Hole 4 rock garden)

3. **Placement**: Manual placement from the asset browser into per-hole Decoration sub-collections. Positioned using snapping to terrain surface. Each instance can be individually scaled and rotated.

### Layer 3: Feature Trees and Focal Points (Manual Modeling/Placement)

1. **Japanese Maple** (Hole 7): A single hand-modeled ornamental tree with geometry node leaf distribution on branch curves. Focal point of the Japanese garden theme.

2. **Small Ornamental Trees**: 2-3 generic ornamental tree models placed at key visual points (course entrance, midway rest area, course exit). Modeled with moderate detail (500-2000 faces per tree plus leaf instances).

3. **Signage and Structures**: Welcome sign (Hole 1), scorecard station (Hole 9), hole number markers. These are manually modeled one-off objects.

### Layer 4: Rocks and Boulders

1. **Rock Library**: 5-6 procedurally generated rock shapes using Blender's sculpt mode or the Rock Generator add-on. Stored in `assets/rocks.blend`.

2. **Boulder Clusters**: Manually arranged groups of 3-7 rocks at rock garden locations (Hole 4 alpine garden, Hole 8 ravine walls, general tier edges).

3. **Scatter Rocks**: Small pebbles and gravel scattered via Geometry Nodes on pathway edges and planting bed borders.

### Performance Budget

| Element | Instance Count (est.) | Faces per Instance | Total Faces |
|---------|----------------------|-------------------|-------------|
| Grass blades | 50,000 | 4 | 200,000 |
| Ground cover | 5,000 | 12 | 60,000 |
| Flowers | 3,000 | 8 | 24,000 |
| Shrubs | 60 | 500 | 30,000 |
| Trees | 5 | 2,000 + leaves | 50,000 |
| Rocks | 200 | 300 | 60,000 |
| **Total landscaping** | | | **~424,000** |

This is within acceptable limits for a Blender scene targeting both EEVEE and Cycles rendering.

## Consequences

### Positive

- **Efficient population**: Geometry Nodes scattering handles the bulk of ground-level vegetation (grass, ground cover, flowers) with minimal manual work per square meter.
- **Artistic control**: Feature plants and trees are manually placed, ensuring focal points look intentional rather than algorithmically scattered.
- **Performance management**: Instance-based scattering (Geometry Nodes) uses instanced rendering, which is dramatically more memory-efficient than unique geometry per plant.
- **Layered editing**: Each layer can be hidden, adjusted, or replaced independently. Disabling grass scattering shows the bare terrain for hole editing.
- **Asset reuse**: The plant and rock libraries are reusable across holes and future projects.

### Negative

- **Asset creation time**: Building the initial plant and rock asset library requires upfront investment (8-12 plant models, 5-6 rocks).
- **Weight painting**: Each terrain tier mesh needs vertex weight painting for grass density, which is manual work across 7 tier meshes.
- **Memory at render time**: 50,000+ grass instances consume viewport and render memory despite instancing. EEVEE handles this well; Cycles may need instance culling for very dense areas.
- **Seasonal specificity**: The chosen plants imply a specific season. Changing from summer to autumn would require recoloring materials and swapping some plant assets.

## Alternatives Considered

### Fully Procedural Vegetation (Geometry Nodes Only)

Generate all plants, trees, and rocks purely through Geometry Nodes without pre-made assets.

- **Pros**: No external assets needed. Everything is parametric and adjustable.
- **Cons**: Creating a convincing ornamental tree or flowering shrub purely in Geometry Nodes requires extremely complex node trees. Each species would need its own node group. Development time for 8-12 species would be substantial. Results typically look less organic than modeled or scanned assets.
- **Rejected because**: The time investment for procedural generation of diverse plant species exceeds the benefit for this project. Geometry Nodes excels at scattering and grass generation but is not efficient for complex organic shapes.

### Photogrammetry/Scanned Assets Only

Use only photogrammetry-scanned plant models from asset libraries.

- **Pros**: Maximum realism. Every plant looks photographic.
- **Cons**: Scanned assets are high-poly (10,000-100,000 faces each). Instancing 50+ shrubs at this density would exceed the scene's polygon budget. File size balloons with embedded high-resolution textures. Limited to available scanned species.
- **Rejected because**: The polygon budget and file size constraints make full photogrammetry impractical for a scene with hundreds of plant instances. The hybrid approach uses lower-poly hand-modeled or simplified assets that render well in the context of a miniature golf visualization.

### Particle System (Legacy Hair/Particle)

Use Blender's legacy particle system for grass and plant distribution.

- **Pros**: Mature system with familiar controls. Weight painting integration.
- **Cons**: Legacy particle system is being phased out in Blender 5.0 in favor of Geometry Nodes. Hair particles produce strand-based geometry, not mesh instances, limiting material control. Converting particles to mesh instances loses the live scattering behavior. Geometry Nodes provides the same functionality with better performance and more control.
- **Rejected because**: Geometry Nodes is the current and future standard for instanced scattering in Blender. Building on the legacy particle system introduces technical debt.
