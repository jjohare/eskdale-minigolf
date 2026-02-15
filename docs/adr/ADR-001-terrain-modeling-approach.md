# ADR-001: Terrain Modeling Approach

## Status

Accepted

## Date

2026-02-15

## Context

The mini golf course descends approximately 3 meters over 9 holes across a 15m x 10m footprint. The terrain follows a tiered/terraced layout with varying elevation drops per hole (ranging from 0.0m to 0.5m). The course uses a switchback/zigzag pattern down an incline, requiring clear separation between elevation levels connected by ramps, steps, and cascading features.

The terrain must support:
- 6 distinct elevation tiers (plus the base level)
- Retaining walls between tiers using natural stone, timber sleepers, or gabion baskets
- Pathways between holes with non-slip surfaces
- Planting beds and landscaping zones between tiers
- Structural integrity for obstacles like the windmill (1.5m tall) and bridge (Hole 3)

The elevation profile is:
```
Hole:  1    2    3    4    5    6    7    8    9
Elev:  0.0  0.0  0.3  0.6  1.1  1.6  2.0  2.3  2.7
```

The modeling approach must balance visual fidelity, editability, and manageable geometry complexity for a scene that will include 9 holes, landscaping, water features, and animated elements.

## Decision

Use **modular tier segments** to construct the terrain. Each elevation tier is modeled as an independent mesh object (or small group of objects) that can be positioned, edited, and textured independently. Tiers are organized into Blender collections corresponding to their elevation level.

### Implementation Details

1. **Tier Base Meshes**: Each tier is a roughly planar mesh (subdivided plane or low-poly sculpt) representing that elevation level's ground surface. The mesh extends to cover the footprint of all holes at that tier.

2. **Retaining Walls**: Separate mesh objects for walls between tiers. These are extruded profiles (stone wall, timber sleeper, or gabion) snapped to the edges where tiers meet. Modeled as standalone objects so different wall styles can be applied per transition.

3. **Transition Ramps**: Connecting geometry between tiers modeled as separate meshes. Each ramp or stairway is its own object, placed at the junction between two tier base meshes.

4. **Vertex Groups per Tier**: Each tier mesh uses vertex groups to delineate zones: pathway, planting bed, hole fairway cutout, and slope region. This allows per-zone material assignment and geometry node scattering.

5. **Tier Naming Convention**: `Terrain_Tier_01` through `Terrain_Tier_07` (7 elevation levels including base). Retaining walls follow `RetainingWall_Tier_01_02` (between Tier 1 and Tier 2).

6. **Elevation Precision**: Each tier's Z-position is set via exact numeric entry in Blender's transform panel. A reference empty at each tier's origin records the canonical elevation value.

## Consequences

### Positive

- **Independent editing**: Each tier can be modified without affecting others. Adding detail to Tier 3 does not risk disturbing the geometry of Tier 5.
- **Clear elevation control**: Tier heights are set by object origin Z-position plus vertex positions, making it straightforward to verify the elevation profile matches the PRD.
- **Modular collections**: Each tier maps naturally to a Blender collection, enabling easy show/hide during editing and organized outliner navigation.
- **Retaining wall flexibility**: Different wall styles per tier transition without boolean operations or complex mesh merging.
- **Scalable complexity**: Individual tiers can have different subdivision levels based on detail needs (e.g., Tier 3-4 around the windmill can be more detailed).
- **Material assignment**: Per-tier meshes simplify UV mapping and material slot assignment.

### Negative

- **Seam management**: Edges where tier meshes meet require careful alignment to avoid visible gaps. Retaining wall objects must bridge these seams.
- **More objects in scene**: 7 tier meshes plus retaining walls and ramps results in more objects than a single sculpted mesh approach. Outliner management becomes important.
- **Potential for misalignment**: If tier meshes are moved independently, the course geometry can become inconsistent. Locked transforms on tier objects mitigate this.
- **No single continuous surface**: Physics simulations (ball rolling) cannot use a single collision mesh; each tier needs its own collider.

## Alternatives Considered

### Option A: Single Sculpted Mesh

Model the entire terrain as one continuous mesh, sculpting the tiered form using Blender's sculpt mode or proportional editing.

- **Pros**: Single mesh means no seam issues, one continuous collision surface, simpler physics setup.
- **Cons**: Difficult to make precise elevation changes per tier. Sculpting exact 0.3m or 0.5m drops requires constant measurement. Any edit to one area can propagate to nearby vertices. UV mapping across the entire 15m x 10m mesh is unwieldy. Extremely high vertex count needed for both flat tier surfaces and steep retaining walls in the same mesh.
- **Rejected because**: The precision requirements of the tiered elevation profile (specific meter values per tier) make sculpting impractical. The risk of unintended geometry changes during editing is too high for a project requiring architectural accuracy.

### Option C: Displacement Map on Plane

Start with a subdivided plane covering the full 15x10m footprint. Apply a displacement modifier driven by a grayscale height map image where each tier's elevation is painted as a distinct gray value.

- **Pros**: Height map can be painted in any 2D image editor. Easy to visualize the overall elevation profile. Single object with displacement modifier.
- **Cons**: Achieving sharp tier edges (retaining walls) requires extremely high subdivision on the base plane, leading to massive vertex counts. Displacement maps produce smooth gradients by default; sharp steps need very high resolution. Retaining wall detail (stone texture, gabion structure) cannot be represented in a displacement map alone. UV distortion on steep displaced faces makes texturing the walls difficult.
- **Rejected because**: The sharp tier transitions with distinct retaining wall styles cannot be adequately represented by displacement alone. The vertex count needed for sharp edges would be prohibitive, and the approach does not support the per-wall-style material variation required by the design.
