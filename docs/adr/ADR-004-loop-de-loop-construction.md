# ADR-004: Loop-de-Loop Construction

## Status

Accepted

## Date

2026-02-15

## Context

Hole 5 ("The Windmill") includes a vertical loop-de-loop with approximately 0.6m diameter. The ball travels up a curved ramp, through the enclosed loop, and exits toward the windmill structure. The loop must be:

- Visually clear: Viewers should see the ball inside the loop, requiring transparency
- Structurally sound in 3D: The loop tube must have consistent cross-section and smooth curvature
- Physics compatible: A ball rigid body must be able to roll through the loop with gravity (requires sufficient entry speed in simulation)
- Aesthetically integrated: The loop connects a ramp section to the windmill approach, so transitions must be smooth

The loop is a defining visual element of the signature hole and must read clearly in both close-up renders and overview shots.

## Decision

Construct the loop using a **Bezier curve path extruded as a tube** with a transparent material for the loop section and opaque material for the entry/exit ramps.

### Curve Path

1. **Loop Curve**: A single Bezier curve (`Hole_05_Loop_Path`) defines the entire ball path from the uphill ramp, through the vertical circle, and out toward the windmill. The curve has the following segments:
   - Entry ramp: ascending from tee level, angled upward at ~30 degrees
   - Loop entry: curve transitions smoothly from upward slope into the vertical circle
   - Vertical circle: 0.6m diameter (0.3m radius), center elevated 0.3m above the entry point
   - Loop exit: curve transitions from the top of the loop back to horizontal
   - Windmill approach: short horizontal section leading to the windmill opening

2. **Curve Resolution**: The Bezier curve uses 24-32 resolution points per segment for smooth curvature through the loop. The circular section uses at least 4 Bezier control points with handles adjusted to approximate a true circle.

3. **Curve Tilt**: The curve's tilt parameter is set to 0 throughout the loop section to keep the tube cross-section consistently oriented (no twisting).

### Tube Geometry

1. **Bevel Object**: A circular Bezier curve (`Loop_Cross_Section`) with 0.12m diameter serves as the bevel object for the path. This produces a tube large enough for the golf ball (4.3cm diameter) with clearance.

2. **Track Surface**: The tube represents the outer enclosure. The actual track surface the ball rolls on is a separate, narrower mesh inside the tube -- a half-pipe profile. This is created by using a semicircular bevel cross-section (`Loop_Track_Profile`) on the same path, offset downward.

3. **Mesh Conversion**: After shaping, both the tube and the track are converted to mesh for UV mapping and material assignment. The original curves are preserved in a reference collection.

### Material Assignment

1. **Transparent Tube**: The loop enclosure uses a glass/transparent material with slight blue or green tint. Settings: Principled BSDF with Transmission = 0.95, Roughness = 0.05, IOR = 1.45 (acrylic). Alpha Blend mode in EEVEE, Glass BSDF in Cycles.

2. **Track Surface**: The inner track uses an opaque material matching the fairway artificial turf, but with a slightly smoother appearance to indicate a different surface (polished track).

3. **Entry/Exit Ramps**: The sections before and after the loop are opaque, using the standard border and fairway materials. The transition from opaque to transparent is handled by a material boundary at defined edge loops on the mesh.

### Structural Supports

1. **Support Frame**: Two vertical support posts (`Loop_Support_L`, `Loop_Support_R`) flanking the loop, connected by a horizontal crossbar at the top. Modeled as cylindrical steel tubes (3cm diameter).

2. **Base Mounts**: The supports attach to the terrain mesh at the base. Small concrete pad objects at each foot.

### Physics Track

1. **Collision Mesh**: The track surface mesh (half-pipe) is assigned as a Rigid Body: Passive object with Mesh collision shape. This provides the surface for the ball to roll on during physics simulation.

2. **Tube Walls**: The transparent tube enclosure is also a Passive rigid body with Mesh collision, preventing the ball from escaping the loop.

3. **Entry Speed**: Physics simulation of the ball through the loop requires an entry velocity of approximately 3.4 m/s (calculated from v = sqrt(g * r * 5) for a frictionless loop, with safety margin). The uphill ramp angle and length are tuned to achieve this from a reasonable initial putt speed.

## Consequences

### Positive

- **Smooth curvature**: Bezier curves produce mathematically smooth loops without faceting artifacts visible at render resolution.
- **Adjustable dimensions**: Changing the loop diameter means scaling the circular section of the curve. The bevel object scales the tube width independently.
- **Transparency**: The glass material allows viewers to see the ball (or the track interior) through the loop, which is critical for visual storytelling and understanding the hole layout.
- **Physics compatibility**: The separate track mesh inside the tube provides a clean collision surface for rigid body simulation without the ball colliding with the transparent outer wall under normal conditions.
- **Visual landmark**: The loop is immediately recognizable in overview renders, drawing attention to the signature hole.

### Negative

- **Transparency rendering cost**: Glass/transparent materials significantly increase render time in Cycles (additional light bounces) and require careful settings in EEVEE (alpha blend sorting issues).
- **Bezier precision**: Achieving a true circle with Bezier curves requires precise handle placement. A small error produces an egg-shaped loop rather than a circle. A Python script to set exact handle positions mitigates this.
- **Dual mesh maintenance**: The outer tube and inner track are two meshes following the same path. Changes to the path require updating both.
- **Physics tuning**: Ensuring the ball completes the loop without falling requires careful tuning of entry speed, friction, and loop radius. This is a simulation constraint, not a modeling one.

## Alternatives Considered

### Mesh Modeling (Manual Extrusion)

Model the loop tube by manually extruding a circular cross-section along a path using Blender's mesh tools (extrude, rotate, bridge edge loops).

- **Pros**: Direct control over every vertex. No curve conversion artifacts.
- **Cons**: Extremely tedious for a smooth circular path. Risk of inconsistent cross-sections at each extrusion step. Difficult to adjust the loop diameter after construction without remodeling. No parametric control.
- **Rejected because**: The Bezier curve approach achieves the same result with parametric adjustability and guaranteed smooth curvature. Manual extrusion offers no advantage for a tube-on-path shape.

### Torus Primitive with Cutout

Start with a Blender torus primitive (major radius 0.3m, minor radius 0.06m) and cut it open to create the loop, then attach entry/exit ramp geometry.

- **Pros**: Perfect circle by definition (torus is mathematically circular). Quick to create the loop section.
- **Cons**: The torus must be cut and joined with ramp meshes, creating topology challenges at the seams. The torus cross-section is circular, not a half-pipe track shape. Adjusting the loop diameter after cutting is destructive. No continuous path from ramp through loop to exit.
- **Rejected because**: While the torus gives a perfect circle, the seam management at entry/exit points and the inability to define the continuous ball path as a single curve make this approach less practical than the Bezier method.

### Geometry Nodes Curve-to-Mesh

Use Blender's Geometry Nodes to convert a curve to mesh procedurally, allowing non-destructive loop construction.

- **Pros**: Fully non-destructive. Changes to the curve update the mesh automatically. Profile curve can be swapped dynamically.
- **Cons**: Geometry Nodes curve-to-mesh does not natively support multi-material assignment along the length (transparent section vs opaque ramps) without additional attribute-based material indexing. Physics rigid body assignment on geometry node output requires the Realize Instances step, which can lose attribute data. More complex to set up for a one-off element.
- **Rejected because**: The added complexity of geometry node setup for a single unique element (the loop exists only on Hole 5) does not justify the non-destructive benefit. The Bezier-to-mesh conversion with preserved reference curves provides sufficient editability.
