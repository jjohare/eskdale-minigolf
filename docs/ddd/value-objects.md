# Value Objects - Tiered Mini Golf Course

## Overview

Value objects are immutable domain primitives without identity. Two value objects with the
same properties are considered equal. They encapsulate measurement, constraint, and
configuration data used throughout the domain.

---

## Spatial Value Objects

### Position3D
A point in 3D world space. Blender coordinate system: X = east/west, Y = north/south,
Z = up/down. 1 unit = 1 meter.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| x | float | meters | within [-7.5, 7.5] course bounds |
| y | float | meters | within [-5.0, 5.0] course bounds |
| z | float | meters | within [0.0, 3.0] elevation range |

Equality: two Position3D values are equal if x, y, and z match within 0.001m tolerance.

Usage: tee positions, cup positions, obstacle placement, camera targets, light positions.

### Dimensions
A 3D bounding box size. Always positive values.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| length | float | meters | > 0 |
| width | float | meters | > 0 |
| height | float | meters | >= 0 (0 for flat elements) |

Usage: course footprint (15m x 10m), obstacle bounding boxes, platform sizes.

### Area2D
A 2D footprint area.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| length | float | meters | > 0 |
| width | float | meters | > 0 |

Derived: `area() => length * width` in square meters.

Usage: tier platform areas, planting bed extents.

### BoundingBox
An axis-aligned bounding box in 3D space.

| Property | Type | Unit |
|----------|------|------|
| min | Position3D | meters |
| max | Position3D | meters |

Derived: `dimensions() => Dimensions(max.x - min.x, max.y - min.y, max.z - min.z)`
Derived: `center() => Position3D((min.x + max.x)/2, (min.y + max.y)/2, (min.z + max.z)/2)`

Usage: collision bounds, spatial queries, zone extents.

---

## Measurement Value Objects

### ElevationDrop
The vertical height change between two points.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| startHeight | float | meters | >= 0 |
| endHeight | float | meters | >= 0 |

Derived: `drop() => startHeight - endHeight` (positive = descending)
Invariant: `startHeight >= endHeight` (course always descends or stays flat)

Per-hole values:

| Hole | startHeight | endHeight | drop |
|------|-------------|-----------|------|
| 1 | 3.0 | 3.0 | 0.0 |
| 2 | 3.0 | 2.7 | 0.3 |
| 3 | 2.7 | 2.4 | 0.3 |
| 4 | 2.4 | 1.9 | 0.5 |
| 5 | 1.9 | 1.4 | 0.5 |
| 6 | 1.4 | 1.0 | 0.4 |
| 7 | 1.0 | 0.7 | 0.3 |
| 8 | 0.7 | 0.3 | 0.4 |
| 9 | 0.3 | 0.3 | 0.0 |

Usage: hole elevation changes, tier transitions, slope calculations.

### HoleLength
The distance measured along the putting line from tee to cup.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| value | float | meters | >= 3.0 and <= 10.0 |

Specific values:

| Hole | Length |
|------|--------|
| 1 | 3.5m |
| 2 | 5.0m |
| 3 | 6.0m |
| 4 | 7.0m |
| 5 | 8.0m (longest) |
| 6 | 5.5m |
| 7 | 5.0m |
| 8 | 6.0m |
| 9 | 6.0m |

Total: 52.0m of putting surface.

### HolePar
The expected number of strokes to complete a hole.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| value | integer | strokes | >= 2 and <= 4 |

Distribution: 1x par 2, 7x par 3, 1x par 4. Sum = 27.

Validation rules:
- Par 2: no major obstacles, length <= 4m
- Par 3: 1-2 obstacles, length 4m-7m
- Par 4: 3+ obstacles, length >= 7m

### GreenWidth
The width of the putting green at any measured cross-section.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| value | float | meters | >= 0.9 (minimum), typical 1.2 |

Invariant: no point along the green may be narrower than 0.9m, except at deliberate
narrowing obstacles (bridge at 0.6m is a fairway narrowing, not a green dimension).

### CupDiameter
The standard mini golf cup size.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| value | float | meters | 0.108 (108mm, fixed) |

This is a universal constant in mini golf. The cup is always 108mm diameter.

### BorderHeight
The height of the border rails along the fairway perimeter.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| value | float | meters | 0.10 (10cm, fixed) |

The border profile has a rounded top edge. This is constant across all holes.

---

## Rotation and Motion Value Objects

### Rotation
An angular orientation or rate.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| degrees | float | degrees | 0 to 360 |
| axis | enum | X, Y, or Z | rotation axis |

Usage:
- Windmill blade offset: 90 degrees per blade on Z axis
- Spiral path: 270 degrees around the center mound
- Banked turn angle: cross-slope rotation

### RotationRate
A continuous rotation speed for animated objects.

| Property | Type | Unit |
|----------|------|------|
| degreesPerSecond | float | deg/s |
| period | float | seconds per full revolution |

Derived: `degreesPerSecond = 360 / period`

Specific values:
- Windmill: period = 4.0s, rate = 90 deg/s
- Spinners: period = ~2.0s, rate = ~180 deg/s (faster than windmill)

Blender driver expression: `frame * (360 / (fps * period))`

### SlopeProfile
Describes the longitudinal slope along a fairway or terrain section.

| Property | Type | Unit |
|----------|------|------|
| segments | SlopeSegment[] | ordered slope segments |

Each SlopeSegment:

| Property | Type | Unit |
|----------|------|------|
| startDistance | float | meters from tee |
| endDistance | float | meters from tee |
| gradient | float | degrees (positive = downhill) |

Usage: fairway slopes, ramp gradients, terrain grades.

---

## Material Value Objects

### Material
A PBR material definition for surface appearance.

| Property | Type | Unit | Constraint |
|----------|------|------|------------|
| name | string | -- | unique identifier |
| baseColor | Color | RGB | albedo color |
| roughness | float | 0-1 | 0 = mirror, 1 = matte |
| metallic | float | 0-1 | 0 = dielectric, 1 = metal |
| normalStrength | float | 0-1 | normal map intensity |
| opacity | float | 0-1 | 1 = opaque, 0 = transparent |

Standard materials in the course:

| Name | BaseColor | Roughness | Metallic | Notes |
|------|-----------|-----------|----------|-------|
| ArtificialTurf | (0.15, 0.45, 0.12) | 0.85 | 0.0 | Main putting surface |
| ArtificialTurf_Green | (0.12, 0.50, 0.10) | 0.80 | 0.0 | Green area (slightly different) |
| NaturalStone | (0.55, 0.50, 0.45) | 0.75 | 0.0 | Border rails, walls |
| NaturalStone_Moss | (0.35, 0.45, 0.30) | 0.80 | 0.0 | Moss-covered rocks |
| Timber | (0.45, 0.30, 0.15) | 0.70 | 0.0 | Bridge, windmill, sleepers |
| Metal_Stainless | (0.85, 0.85, 0.85) | 0.25 | 1.0 | Cup rim, structural metal |
| Metal_Painted | varies | 0.40 | 0.8 | Spinners (colorful) |
| Water | (0.05, 0.15, 0.25) | 0.05 | 0.0 | Ponds, streams (+ transparency) |
| Transparent_Acrylic | (0.95, 0.95, 0.95) | 0.10 | 0.0 | Loop tube (opacity ~0.15) |
| Pathway_NonSlip | (0.50, 0.45, 0.40) | 0.90 | 0.0 | Walking paths |
| Gabion_Wire | (0.60, 0.60, 0.55) | 0.50 | 0.8 | Wire cage for gabions |
| GabionStone_Fill | (0.55, 0.52, 0.48) | 0.80 | 0.0 | Stones inside gabion |

### Color
An RGB color value.

| Property | Type | Constraint |
|----------|------|------------|
| r | float | 0.0 to 1.0 |
| g | float | 0.0 to 1.0 |
| b | float | 0.0 to 1.0 |

Usage: material base colors, light colors, accent colors.

### Resolution
An image output resolution.

| Property | Type | Constraint |
|----------|------|------------|
| width | integer | >= 1920 |
| height | integer | >= 1080 |

Default: 1920x1080. Can be higher for detail renders.

---

## Enumeration Value Objects

### ObstacleType
The classification of obstacle mechanics.

Values: `Windmill`, `Loop`, `Tunnel`, `Bridge`, `Spiral`, `SteppingStones`, `Ravine`,
`Spinner`, `BumperStone`, `Chicane`, `BankedTurn`, `RaisedGreen`

### WallType
The construction material for retaining walls.

Values: `NaturalStone`, `TimberSleeper`, `GabionBasket`

### GardenTheme
The landscaping aesthetic applied to a hole's surroundings.

Values: `EnglishWelcome`, `CascadeGarden`, `WoodlandGully`, `AlpineRock`, `DutchGarden`,
`ButterflyGarden`, `JapaneseGarden`, `DramaticRavine`, `CelebrationGarden`

### WaterFeatureType
The category of decorative water element.

Values: `Waterfall`, `Pond`, `Stream`, `Combined`

### CameraType
The purpose category for a camera.

Values: `Overview`, `HoleDetail`, `EyeLevel`, `Flyover`

### LightType
The Blender light category.

Values: `Sun`, `Area`, `Point`, `Spot`

---

## Composite Value Objects

### SplinePath
An ordered sequence of control points defining a curve.

| Property | Type |
|----------|------|
| controlPoints | Position3D[] |
| isClosed | boolean |
| interpolation | enum (Bezier, NURBS, Poly) |

Usage: fairway centerlines, border rail paths, pathway routes, camera flyover paths.

### CrossSection
A 2D profile shape used for extrusion.

| Property | Type |
|----------|------|
| points | Position2D[] |
| isClosed | boolean |

Usage: border rail profile (rounded top edge), retaining wall profile.

### ContourMap
Subtle surface elevation variations on a putting surface.

| Property | Type |
|----------|------|
| samples | ElevationSample[] |
| resolution | float (meters between samples) |

Each ElevationSample: `{ position: Position2D, height: float }`

Usage: green undulations, fairway subtle slopes for ball guidance.
