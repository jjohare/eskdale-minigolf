# Aggregates - Tiered Mini Golf Course

## Overview

Aggregates define consistency boundaries within the domain. Each aggregate has a root
entity that controls access to its internal entities and enforces invariants. In the
context of a Blender build, aggregates map to collection hierarchies and object
groupings that must remain internally consistent.

---

## 1. Course Aggregate (Root)

The top-level aggregate representing the entire mini golf course. All other aggregates
are accessed through or positioned relative to the Course root.

### Root Entity: Course

| Property | Type | Value/Constraint |
|----------|------|------------------|
| name | string | "Tiered Mini Golf Course" |
| footprint | Dimensions | 15m x 10m (max envelope) |
| activeArea | Dimensions | ~13m x 9m (actual usage) |
| totalElevationDrop | ElevationDrop | 3.0m (start to finish) |
| holeCount | integer | 9 (invariant) |
| totalPar | integer | 27 (invariant) |
| layoutPattern | enum | Switchback |
| style | string | "Naturalistic English garden" |

### Contains
- `holes: Hole[9]` -- ordered array, Hole 1 at top through Hole 9 at bottom
- `pathways: Pathway[]` -- connections between consecutive holes (8 pathways)
- `tiers: Tier[7]` -- Tier 1 (top) through Tier 6 + base level
- `elevationProfile: ElevationProfile` -- cumulative elevation data

### Invariants
1. `holes.length == 9`
2. `sum(holes[].par) == 27`
3. `sum(holes[].drop) + pathwayDrops == 3.0m`
4. All holes fit within the footprint boundary
5. Pathways connect hole[n].green to hole[n+1].tee for all n in [1,8]
6. Tier elevations are monotonically decreasing from Tier 1 to base

### Blender Mapping
- Top-level collection: "MiniGolf_Course"
- Child collections: "Hole_01" through "Hole_09", "Pathways", "Terrain", "Landscaping_Global"

---

## 2. Hole Aggregate

Each hole is an independent aggregate with its own internal consistency rules.
Holes are the primary unit of work in the build process.

### Root Entity: Hole

| Property | Type | Value/Constraint |
|----------|------|------------------|
| number | integer | 1-9 |
| name | string | e.g. "The Welcome", "The Windmill" |
| par | HolePar | 2, 3, or 4 |
| length | HoleLength | 3m to 10m |
| drop | ElevationDrop | per hole elevation change |
| tierStart | TierReference | which tier the tee is on |
| tierEnd | TierReference | which tier the green is on |
| isSignature | boolean | true only for Hole 5 |

### Contains
- `tee: Tee` -- starting position entity
- `fairway: Fairway` -- the putting surface shape
- `green: Green` -- the final putting area
- `cup: Cup` -- the target hole
- `obstacles: Obstacle[]` -- 0 or more obstacle entities
- `borders: Border[]` -- continuous border rail segments
- `landscapeZone: LandscapeZone` -- surrounding decorative elements

### Invariants
1. Exactly one tee, one green, one cup per hole
2. Cup is located within the green boundary
3. Borders form a continuous perimeter (no gaps except obstacle entry/exit points)
4. Green width >= 0.9m at all points
5. A valid ball path exists from tee to cup through all obstacles
6. Fairway surface is continuous from tee to green
7. `par` matches obstacle complexity: par 2 = no obstacles, par 3 = 1-2, par 4 = 3+

### Per-Hole Specifications

| Hole | Name | Par | Length | Drop | Obstacles |
|------|------|-----|--------|------|-----------|
| 1 | The Welcome | 2 | 3.5m | 0.0m | None |
| 2 | The Cascade | 3 | 5.0m | 0.3m | BumperStones(2), Chicane |
| 3 | The Bridge | 3 | 6.0m | 0.3m | Bridge, BankedTurn |
| 4 | The Spiral | 3 | 7.0m | 0.5m | SpiralPath, RockMound |
| 5 | The Windmill | 4 | 8.0m | 0.5m | Loop, Windmill, Ramps |
| 6 | The Tunnel | 3 | 5.5m | 0.4m | SplitTunnel |
| 7 | The Stepping Stones | 3 | 5.0m | 0.3m | SteppingStones(3), Pond |
| 8 | The Ravine | 3 | 6.0m | 0.4m | Ravine, LaunchRamp, AltPath |
| 9 | The Grand Finale | 3 | 6.0m | 0.0m | Spinners(4), RaisedGreen |

### Blender Mapping
- Collection per hole: "Hole_01" containing "Tee_01", "Fairway_01", "Green_01", etc.
- Obstacles as child collections within the hole: "Hole_05/Windmill", "Hole_05/Loop"
- Landscaping sub-collection: "Hole_01/Landscaping"

---

## 3. Obstacle Aggregate

Obstacles are complex entities that may contain multiple moving parts, structural
components, and animation data. Each obstacle type is a specialized aggregate.

### Root Entity: Obstacle (Abstract)

| Property | Type | Value/Constraint |
|----------|------|------------------|
| type | ObstacleType | enum of obstacle types |
| position | Position3D | world-space placement |
| dimensions | Dimensions | bounding box |
| holeNumber | integer | which hole owns this obstacle |
| affectsPath | boolean | true if obstacle blocks/redirects ball |

### Specialized Obstacle Aggregates

#### WindmillObstacle
| Property | Type | Value |
|----------|------|-------|
| height | meters | 1.5m |
| bladeCount | integer | 4 |
| rotationPeriod | seconds | 4.0 |
| openingWidth | meters | 0.15 (15cm) |
| style | string | "Dutch traditional" |
| blades | WindmillBlade[4] | rotating blade entities |
| structure | WindmillStructure | the building body |
| opening | WindmillOpening | ground-level passage |

Invariants:
- Blade tips pass at ground level blocking the opening
- Opening width allows standard golf ball (42.67mm) passage
- Rotation is continuous and constant speed

#### LoopObstacle
| Property | Type | Value |
|----------|------|-------|
| diameter | meters | 0.6m |
| trackWidth | meters | 0.15m (ball + clearance) |
| material | string | "Transparent enclosed tube" |
| entryRamp | Ramp | uphill approach |
| exitPoint | Position3D | connects to windmill entrance |

Invariants:
- Full 360-degree vertical loop
- Entry ramp provides sufficient momentum for ball to complete loop
- Tube fully encloses the ball path

#### TunnelObstacle
| Property | Type | Value |
|----------|------|-------|
| length | meters | ~2m through hill |
| splitPaths | TunnelPath[2] | left (safe) and right (risky) |
| material | string | "Natural stone" |
| hillCover | boolean | true (grass-topped hill above) |

Invariants:
- Both paths merge before the green
- Right path is shorter but has a narrow gap
- Tunnel is fully enclosed (no visible ball from outside)

#### BridgeObstacle
| Property | Type | Value |
|----------|------|-------|
| width | meters | 0.6m (narrowed from standard) |
| spanLength | meters | ~2m over gully |
| railHeight | meters | 0.05m (low side rails) |
| material | string | "Timber" |
| elevation | meters | above gully floor |

Invariants:
- Bridge is narrower than standard fairway (deliberate challenge)
- Side rails prevent ball from falling off
- Structural supports visible from below

#### SpinnerObstacle
| Property | Type | Value |
|----------|------|-------|
| count | integer | 4 (Hole 9) |
| placement | string | "Alternating sides" |
| rotationSpeed | degrees/sec | variable, faster than windmill |
| postHeight | meters | ~0.3m |
| bladeReach | meters | ~0.2m into fairway |

Invariants:
- Spinners do not fully block the path (always a passage available)
- Posts are mounted at fairway border
- Blade reach extends partway across fairway

### Blender Mapping
- Each obstacle is a sub-collection within its hole
- Animated obstacles have armatures with drivers
- Transparent elements use glass/transparency shader

---

## 4. LandscapeZone Aggregate

Groups all decorative natural elements surrounding a hole or course area.

### Root Entity: LandscapeZone

| Property | Type | Value/Constraint |
|----------|------|------------------|
| zoneId | string | "LZ_Hole_01", "LZ_Global_Entrance", etc. |
| theme | GardenTheme | English, Dutch, Japanese, Alpine, Butterfly, Celebration |
| bounds | BoundingBox | spatial extent of the zone |
| holeAssociation | integer? | null for global zones |

### Contains
- `plantBeds: PlantBed[]` -- collections of vegetation
- `rockFeatures: RockFeature[]` -- boulders, rock gardens, stone arrangements
- `waterFeatures: WaterFeature[]` -- ponds, streams, waterfalls
- `furniture: Furniture[]` -- benches, signs, scorecard stations
- `lighting: AccentLight[]` -- LED pathway lights

### Per-Hole Landscape Themes

| Hole | Theme | Key Features |
|------|-------|-------------|
| 1 | English Welcome | Flower beds, stone archway, welcome signage |
| 2 | Cascade Garden | Waterfall, ferns, moss-covered rocks |
| 3 | Woodland Gully | Deep planting in gully, ferns, mosses, stone walls |
| 4 | Alpine Rock Garden | Succulents, alpine plants, central rock mound |
| 5 | Dutch Garden | Tulip beds, pond with reeds, Dutch theme |
| 6 | Butterfly Garden | Wildflowers, grass-topped hill |
| 7 | Japanese Garden | Water lilies, koi pond, small maple tree |
| 8 | Dramatic Ravine | Rock faces, stream, planted ravine sides |
| 9 | Celebration | Colorful flowers, seating, scorecard station |

### Blender Mapping
- Sub-collection "Landscaping" within each hole collection
- Particle systems for grass and ground cover
- Instanced collections for repeated plant types
- Water planes with shader-driven animation

---

## 5. TerrainTier Aggregate

Represents one horizontal tier of the hillside terrain with its associated structural
elements.

### Root Entity: TerrainTier

| Property | Type | Value/Constraint |
|----------|------|------------------|
| tierNumber | integer | 1-6 + base (0) |
| elevation | meters | absolute height from base |
| platformArea | Area2D | the flat area at this tier |
| holesOnTier | integer[] | which holes are on this tier |

### Contains
- `retainingWalls: RetainingWall[]` -- walls holding the tier edge
- `slopes: Slope[]` -- gradients connecting to adjacent tiers
- `ramps: Ramp[]` -- pathway transitions between tiers
- `steps: StepSet[]` -- optional step features

### Tier Elevation Map

| Tier | Elevation (m) | Holes | Drop to Next |
|------|--------------|-------|--------------|
| 1 (Top) | 3.0 | H1, H2 start | 0.3m |
| 2 | 2.7 | H2 end, H3, H4 start | 0.5m |
| 3 | 2.2 | H4 end, H5 start | 0.5m |
| 4 | 1.7 | H5 end, H6 start | 0.4m |
| 5 | 1.3 | H6 end, H7, H8 start | 0.4m |
| 6 | 0.9 | H8 end, H9 | 0.0m (pathway) |
| Base | 0.0 | Exit/scoring | -- |

Note: Remaining 0.9m distributed across pathway ramps between tiers.

### Invariants
1. Tier elevations are strictly decreasing
2. Every tier has at least one retaining wall
3. Retaining wall materials are natural stone, timber sleeper, or gabion basket
4. Maximum slope gradient is 45 degrees
5. All platforms are large enough to contain their assigned holes

### Blender Mapping
- Terrain mesh subdivided and sculpted per tier
- Retaining wall objects aligned to tier boundaries
- Vertex groups per tier for material assignment
- Modifier stack: subdivision + sculpt + boolean (for gullies/ravines)
