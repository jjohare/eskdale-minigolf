# ADR-007: Elevation and Scale

## Status

Accepted

## Date

2026-02-15

## Context

The mini golf course has specific physical dimensions: 15m x 10m maximum footprint, approximately 3m total elevation drop across 9 holes, with individual hole lengths from 3m to 10m. The Blender model must accurately represent these dimensions for both visual presentation and potential construction planning use.

Blender does not enforce a unit system by default. Without a clear convention, objects can be modeled at arbitrary scales, leading to inconsistent dimensions, incorrect physics simulations, and misleading renders. The physics simulation system (rigid body) depends on accurate scale for gravity and collision behavior.

The elevation profile from the PRD defines specific heights:
```
Hole:  1    2    3    4    5    6    7    8    9
Elev:  0.0  0.0  0.3  0.6  1.1  1.6  2.0  2.3  2.7
```
With 0.3m additional for pathway ramps, totaling ~3.0m.

## Decision

Adopt a strict scale and coordinate system: **1 Blender Unit (BU) = 1 meter**, **Z-axis up**, with the **course origin at the top-left corner** (Hole 1 tee position) at world origin.

### Unit Configuration

1. **Scene Units**: Blender Scene Properties > Units set to Metric, Unit Scale = 1.0, Length = Meters. This ensures all dimension displays, measurements, and physics calculations use meters.

2. **Scale Convention**: 1 BU = 1 meter without exception. A 1.5m-tall windmill is 1.5 BU tall. A 0.6m loop diameter is 0.6 BU. A 108mm cup diameter is 0.108 BU. All artists and scripts must verify object dimensions in the N-panel before finalizing.

3. **Grid Settings**: Viewport grid set to 1m major divisions with 10 subdivisions (0.1m minor grid lines). This provides visual reference at both course scale and detail scale.

### Coordinate System

1. **Origin Point**: World origin (0, 0, 0) is placed at the top-left corner of the course, corresponding to the Hole 1 tee position at the highest elevation.

2. **Axis Orientation**:
   - **X-axis**: Positive X runs along the long dimension of the course (15m direction, east)
   - **Y-axis**: Positive Y runs along the short dimension (10m direction, south, downhill in the switchback)
   - **Z-axis**: Positive Z is up. The highest point (Hole 1 tee) is at Z = 0.0. Terrain descends to negative Z values. The lowest point (Hole 9 green) is approximately at Z = -3.0.

3. **Elevation Convention**: Z = 0.0 at the top. Each tier's elevation is a negative Z offset from the top:
   ```
   Tier 1 (Holes 1-2): Z = 0.0
   Tier 2 (Holes 2-3): Z = -0.3
   Tier 3 (Holes 3-4): Z = -0.6
   Tier 4 (Holes 4-5): Z = -1.1
   Tier 5 (Holes 5-6): Z = -1.6
   Tier 6 (Holes 6-7): Z = -2.0
   Tier 7 (Holes 7-8): Z = -2.3
   Base (Hole 9):      Z = -2.7 to -3.0
   ```

### Reference Points

1. **Elevation Empties**: An Empty object at each tier's canonical elevation, named `ElevRef_Tier_01` through `ElevRef_Tier_08`. Placed at the tier's Y-midpoint along the X-axis, at the correct Z height. These empties serve as visual guides and snapping targets.

2. **Course Boundary**: A wireframe box (`CourseBoundary`) spanning 15m x 10m x 3m showing the maximum footprint envelope. Placed on a locked, hidden-by-default layer for reference.

3. **Measurement Empties**: At each hole's tee and cup position, an Empty named `Hole_XX_Tee_Ref` and `Hole_XX_Cup_Ref` records the intended position. These can be used to verify hole lengths and elevation drops by measuring between empties.

### Verification Protocol

Before finalizing any hole or terrain section:

1. **Dimension Check**: Select the object, open the N-panel, verify X/Y/Z dimensions match the PRD specifications in meters.
2. **Elevation Check**: Place the 3D cursor at the object's lowest point, read the Z coordinate, verify it matches the tier elevation table.
3. **Length Check**: For each hole, measure the distance from tee empty to cup empty using Blender's measurement tool. Verify against the PRD hole length.
4. **Footprint Check**: Enable the CourseBoundary wireframe and verify all geometry falls within the 15m x 10m envelope.

### Physics Implications

With 1 BU = 1 meter, Blender's rigid body physics engine uses standard SI units:
- Gravity: 9.81 m/s^2 (Blender default, correct for this scale)
- Mass: kilograms (golf ball: 0.046 kg)
- Velocity: m/s (typical putt speed: 1-3 m/s)

No physics scale corrections are needed.

## Consequences

### Positive

- **Architectural accuracy**: Dimensions directly correspond to real-world meters. Construction planning can reference the model dimensions directly.
- **Physics correctness**: Standard gravity and mass values produce realistic ball behavior without scale factors.
- **Intuitive editing**: Artists can think in meters. "The windmill is 1.5 units tall" means 1.5 meters with no conversion.
- **Consistent collaboration**: Any contributor opening the file sees metric dimensions. No ambiguity about scale.
- **Measurement tools work directly**: Blender's ruler tool, dimension display, and transform values all report in meters.

### Negative

- **Negative Z convention**: Using Z = 0 at the top and descending to negative values is less intuitive than ascending from 0 at the base. However, placing the origin at the highest point (where construction typically begins) aligns with the design flow from Hole 1 downward.
- **Small detail precision**: Objects like the cup (0.108m diameter) and border profile (0.1m height) are small in Blender's viewport at 1:1 scale. Frequent zooming is needed for detail work. The 0.1m grid subdivision helps.
- **Viewport clipping**: At 1:1 scale, the viewport near clip plane must be set low enough (0.01m) to avoid clipping when zoomed into small details, while the far clip must extend to cover the full course (at least 20m).

## Alternatives Considered

### 1 BU = 1 Centimeter

Model at 100x scale (1 BU = 1 cm) so the course spans 1500 x 1000 BU.

- **Pros**: Small details (cup, border profile) are more comfortable to edit at this scale. No viewport clipping issues at detail level.
- **Cons**: Physics engine requires gravity to be scaled by 100x (981 m/s^2) or objects become unrealistically bouncy. All physics parameters need conversion. Artists must mentally convert "150 BU = 1.5 meters" constantly. Scene dimensions are misleadingly large in the properties panel.
- **Rejected because**: The physics simulation dependency on correct scale makes the 1:100 approach error-prone. The mental overhead of unit conversion for every dimension check outweighs the viewport comfort benefit.

### Z = 0 at Base, Ascending

Place the course origin at the lowest point (Hole 9 green, base level) with positive Z ascending to the top.

- **Pros**: All Z values are positive, which is more intuitive for "height above ground."
- **Cons**: The design flow goes from Hole 1 (top) to Hole 9 (bottom). Placing the origin at the design starting point (Hole 1) is more natural for the build sequence. Construction begins at the top and proceeds downhill.
- **Rejected because**: Aligning the origin with the design and construction starting point (top, Hole 1) provides a more natural workflow despite the negative Z values. The elevation reference empties make it easy to verify positions regardless of sign convention.

### No Fixed Origin (Per-Hole Local Coordinates)

Each hole uses its own local coordinate system with origin at the tee position.

- **Pros**: Per-hole dimensions are always relative and easy to verify.
- **Cons**: Course-level layout verification becomes difficult. Calculating distances between holes requires transforming between local coordinate systems. The switchback layout depends on precise positioning of holes relative to each other across the full footprint.
- **Rejected because**: The course is a single integrated structure, not 9 independent models. A unified world coordinate system is essential for verifying the overall layout, elevation profile, and footprint compliance.
