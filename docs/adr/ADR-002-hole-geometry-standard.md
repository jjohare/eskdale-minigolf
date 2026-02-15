# ADR-002: Hole Geometry Standard

## Status

Accepted

## Date

2026-02-15

## Context

The course contains 9 holes with varying lengths (3m to 8m), widths (minimum 0.9m, typical 1.2m), and features. Each hole requires a fairway surface, border rails (10cm height, rounded top edge), a tee position, and a cup (108mm diameter). Some holes have additional geometry: bridges, tunnels, ramps, loops, and obstacle placements.

A consistent construction method is needed so that:
- All 9 holes share a recognizable visual style
- Dimensions conform to playability standards from the PRD
- Holes can be edited independently without affecting neighbors
- The cup, tee, and fairway are identifiable in the data model for potential physics simulation
- New contributors can understand and replicate the construction pattern

## Decision

Adopt a standardized construction method for all hole geometry based on **extruded curve paths for fairways, bevel objects for borders, and planar meshes for greens**.

### Fairway Construction

1. **Path Curve**: Each hole's centerline is defined as a Bezier curve (`Hole_XX_Path`). Control points define the fairway shape: straight sections, curves, S-bends, and doglegs.

2. **Fairway Surface**: A plane mesh is modeled to follow the path curve's shape. The plane is subdivided and shaped to match the fairway width (0.9m minimum, 1.2m typical). The Shrinkwrap modifier projects it onto the tier terrain mesh for proper ground contact.

3. **Fairway Width**: Controlled by the Bezier curve's bevel depth or by a manually modeled mesh that references the path as a guide. Variable width sections (narrowing chicanes, wider greens) are modeled by adjusting edge loops on the fairway mesh.

### Border Rail Construction

1. **Border Profile**: A shared bevel object (`Border_Profile`) defines the cross-section of all border rails: 10cm height with a rounded top edge (2cm radius fillet). This profile is a small Bezier curve with 4-5 control points.

2. **Border Curves**: Two Bezier curves per hole (`Hole_XX_Border_L` and `Hole_XX_Border_R`) trace the left and right edges of the fairway. Each uses the shared `Border_Profile` as its bevel object.

3. **Conversion**: Border curves are converted to mesh after shaping for UV mapping and material assignment. The original curves are kept in a hidden reference collection for future edits.

### Green and Cup

1. **Green Area**: The putting green at each hole's end is a slightly flattened region of the fairway mesh, marked with a vertex group (`Green`) for distinct material assignment (shorter turf texture).

2. **Cup Geometry**: A cylinder (108mm diameter, 100mm depth) subtracted from the green surface via Boolean modifier, or modeled as a recessed ring. Named `Hole_XX_Cup`. A small flag object (`Hole_XX_Flag`) is placed at the cup position.

3. **Tee Area**: A small rectangular region (0.3m x 0.4m) at the start of each hole, marked with a vertex group (`Tee`) for material variation. A tee marker object (`Hole_XX_TeeMarker`) indicates the starting position.

### Naming Convention

All objects follow this pattern:
```
Hole_01_Fairway
Hole_01_Border_L
Hole_01_Border_R
Hole_01_Cup
Hole_01_Flag
Hole_01_TeeMarker
Hole_01_Path          (reference curve, hidden)
Hole_01_Obstacle_XX   (per-obstacle naming)
```

### Per-Hole Collection Structure

Each hole resides in its own collection:
```
Holes/
  Hole_01/
    Fairway/
      Hole_01_Fairway
      Hole_01_Border_L
      Hole_01_Border_R
      Hole_01_Cup
      Hole_01_Flag
      Hole_01_TeeMarker
    Obstacles/
      (hole-specific obstacles)
    Decorations/
      (hole-specific decorative elements)
    Reference/
      Hole_01_Path
```

## Consequences

### Positive

- **Consistency**: All holes share the same construction vocabulary. A fairway is always a shaped mesh, borders always use the shared bevel profile, cups are always the same diameter.
- **Editability**: Modifying a hole's layout means adjusting its path curve and reshaping the fairway mesh. Border curves follow the same edit.
- **Dimensional accuracy**: The bevel profile object enforces exact 10cm border height across all holes. Cup cylinders are parameterized at 108mm.
- **Material simplicity**: Vertex groups on the fairway mesh (`Green`, `Tee`, `Fairway`) allow a single material with different texture coordinates per zone, or separate material slots.
- **Physics readiness**: The fairway mesh serves directly as a collision surface. Borders provide containment geometry. The cup Boolean creates the physical depression.

### Negative

- **Initial setup time**: Creating the standardized structure for each hole requires following the template carefully. The first hole takes longest; subsequent holes are faster.
- **Boolean artifacts**: The cup Boolean can produce non-manifold geometry if the fairway mesh is too coarse around the cup area. Local subdivision around the cup mitigates this.
- **Curve-to-mesh conversion**: Converting border curves to meshes is a one-way operation for UV mapping. Edits require going back to the reference curves and reconverting.
- **Vertex group discipline**: The vertex group naming convention must be followed precisely for materials and physics to work correctly.

## Alternatives Considered

### Fully Procedural (Geometry Nodes)

Generate each hole entirely from geometry nodes taking the path curve as input, automatically creating fairway width, borders, cup, and tee.

- **Pros**: Parametric, non-destructive, changes propagate automatically.
- **Cons**: The variation between holes (bridge on Hole 3, tunnel on Hole 6, loop on Hole 5) makes a single geometry node tree extremely complex. Each hole's unique obstacles break the parametric pattern.
- **Rejected because**: The diversity of hole features means a universal geometry node setup would be more complex to maintain than the manual-but-standardized approach. Geometry nodes are better suited for repetitive elements like border rails (explored in ADR-006 for vegetation).

### Individual Sculpted Meshes

Sculpt each hole as a single high-poly mesh with borders, fairway, and cup modeled as part of one continuous surface.

- **Pros**: No seams, no Boolean operations, artistic freedom.
- **Cons**: Difficult to maintain consistent border height (10cm) and cup diameter (108mm) through sculpting. High vertex count per hole. No parametric control over dimensions.
- **Rejected because**: Playability dimensions are architectural requirements, not artistic suggestions. Sculpting cannot reliably maintain the dimensional precision needed.
