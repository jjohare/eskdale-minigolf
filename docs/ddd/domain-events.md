# Domain Events - Tiered Mini Golf Course

## Overview

Domain events represent significant state transitions during the Blender build process.
Each event signals that a meaningful construction step has been completed and may trigger
downstream work in other bounded contexts. Events are ordered to reflect the natural
build sequence from terrain foundation through final render output.

---

## Event Catalog

### Phase 1: Foundation Events

#### TerrainCreated
Fired when the base terrain mesh is sculpted and the hillside form is established.

| Field | Type | Description |
|-------|------|-------------|
| terrainId | string | "terrain_main" |
| footprint | Dimensions | 15m x 10m envelope |
| elevationRange | ElevationDrop | 0.0m to 3.0m |
| vertexCount | integer | mesh complexity |
| timestamp | datetime | build step completion time |

**Triggers**: TierEstablished events can begin. CourseLayout context starts hole positioning.

**Preconditions**: None (first event in the build).

**Postconditions**: A subdivided, sculpted mesh exists representing the hillside.

---

#### TierEstablished
Fired once per tier when a horizontal platform is carved into the terrain at the
correct elevation.

| Field | Type | Description |
|-------|------|-------------|
| tierNumber | integer | 1-6 or 0 (base) |
| elevation | meters | absolute height |
| platformArea | Area2D | usable flat area |
| retainingWallType | WallType | NaturalStone, TimberSleeper, or GabionBasket |
| timestamp | datetime | build step completion time |

**Triggers**: HolePositioned events for holes assigned to this tier.

**Preconditions**: TerrainCreated has fired.

**Postconditions**: A flat platform exists at the specified elevation with retaining
walls along its downhill edges.

Expected sequence: 7 events (Tier 1 through Tier 6 + Base).

---

#### RetainingWallBuilt
Fired when a retaining wall segment is placed along a tier boundary.

| Field | Type | Description |
|-------|------|-------------|
| wallId | string | "retwall_tier1_north", etc. |
| tierNumber | integer | which tier boundary |
| wallType | WallType | construction material type |
| path | SplinePath | wall alignment |
| height | meters | wall height (= tier drop) |
| timestamp | datetime | build step completion time |

**Triggers**: MaterialApplied for the wall surface.

**Preconditions**: TierEstablished for the relevant tier.

**Postconditions**: Retaining wall geometry exists with correct dimensions.

---

### Phase 2: Hole Construction Events

#### HolePositioned
Fired when a hole's tee and green positions are established in world coordinates
on the correct tier.

| Field | Type | Description |
|-------|------|-------------|
| holeNumber | integer | 1-9 |
| holeName | string | display name |
| teePosition | Position3D | world-space tee center |
| greenPosition | Position3D | world-space green center |
| tierStart | integer | starting tier |
| tierEnd | integer | ending tier |
| drop | ElevationDrop | elevation change |
| par | HolePar | 2, 3, or 4 |
| timestamp | datetime | build step completion time |

**Triggers**: FairwayConstructed for this hole. HoleDesign context begins geometry work.

**Preconditions**: TierEstablished for both tierStart and tierEnd.

**Postconditions**: Empty objects marking tee and green positions exist in the Blender scene.

Expected sequence: 9 events, one per hole.

---

#### FairwayConstructed
Fired when the putting surface mesh is created between tee and green, including
all curves, slopes, and width variations.

| Field | Type | Description |
|-------|------|-------------|
| holeNumber | integer | 1-9 |
| length | HoleLength | measured along putting line |
| minWidth | meters | narrowest point |
| centerlinePath | SplinePath | fairway center curve |
| slopeProfile | SlopeProfile | longitudinal slopes |
| timestamp | datetime | build step completion time |

**Triggers**: BordersInstalled, ObstacleBuilt events for this hole.

**Preconditions**: HolePositioned for this hole.

**Postconditions**: A continuous mesh surface exists from tee to green with correct
UV mapping for turf material.

---

#### BordersInstalled
Fired when all border rail segments are placed around a hole's fairway perimeter.

| Field | Type | Description |
|-------|------|-------------|
| holeNumber | integer | 1-9 |
| segmentCount | integer | number of border segments |
| totalLength | meters | combined rail length |
| gapCount | integer | number of gaps (obstacle entries) |
| height | meters | 0.10m (constant) |
| timestamp | datetime | build step completion time |

**Triggers**: MaterialApplied for border surfaces.

**Preconditions**: FairwayConstructed for this hole.

**Postconditions**: Continuous border rails with rounded top profile surround the fairway.

---

#### CupPlaced
Fired when the cup (hole) is boolean-subtracted into the green surface.

| Field | Type | Description |
|-------|------|-------------|
| holeNumber | integer | 1-9 |
| position | Position3D | cup center |
| diameter | meters | 0.108m (standard) |
| depth | meters | ~0.1m |
| hasFlag | boolean | true for Hole 9 |
| hasBell | boolean | true for Hole 9 |
| timestamp | datetime | build step completion time |

**Triggers**: Hole is playable (valid path exists from tee to cup).

**Preconditions**: FairwayConstructed for this hole.

**Postconditions**: A cylindrical depression exists in the green surface.

---

### Phase 3: Obstacle Events

#### ObstacleBuilt
Fired when a mechanical or structural obstacle is fully modeled and placed within
its hole.

| Field | Type | Description |
|-------|------|-------------|
| obstacleId | string | unique obstacle identifier |
| obstacleType | ObstacleType | Windmill, Loop, Tunnel, etc. |
| holeNumber | integer | parent hole |
| position | Position3D | obstacle placement |
| dimensions | Dimensions | bounding box |
| hasAnimation | boolean | requires animation setup |
| timestamp | datetime | build step completion time |

**Triggers**: If hasAnimation, triggers animation setup in AnimationAndPhysics context.
Triggers MaterialApplied for obstacle surfaces.

**Preconditions**: FairwayConstructed for the parent hole.

**Postconditions**: Obstacle geometry exists with correct dimensions and position.

Specific obstacle events (specialized ObstacleBuilt):

#### WindmillConstructed
| Field | Type | Description |
|-------|------|-------------|
| height | meters | 1.5m |
| bladeCount | integer | 4 |
| openingWidth | meters | 0.15m |
| style | string | "Dutch traditional" |

#### LoopConstructed
| Field | Type | Description |
|-------|------|-------------|
| diameter | meters | 0.6m |
| enclosureMaterial | string | "Transparent acrylic" |
| entryRampAngle | degrees | ramp approach angle |

#### TunnelCarved
| Field | Type | Description |
|-------|------|-------------|
| length | meters | tunnel length through hill |
| pathCount | integer | 2 (split path) |
| hillCovered | boolean | true (grass-topped) |

---

### Phase 4: Animation Events

#### WindmillAnimated
Fired when the windmill blade rotation animation is set up with drivers.

| Field | Type | Description |
|-------|------|-------------|
| windmillId | string | "windmill_structure" |
| rotationPeriod | seconds | 4.0 |
| driverExpression | string | rotation driver formula |
| bladeCount | integer | 4 |
| armatureName | string | Blender armature object name |
| timestamp | datetime | build step completion time |

**Triggers**: Animation can be rendered. RenderingPipeline can include this in outputs.

**Preconditions**: ObstacleBuilt for the windmill (WindmillConstructed).

**Postconditions**: Windmill blades rotate continuously in the viewport and render.

---

#### SpinnersAnimated
Fired when all pinwheel spinner animations are configured.

| Field | Type | Description |
|-------|------|-------------|
| spinnerCount | integer | 4 |
| rotationPeriods | float[] | per-spinner period |
| holeNumber | integer | 9 |
| timestamp | datetime | build step completion time |

**Triggers**: Animation renders can include Hole 9 spinner motion.

**Preconditions**: ObstacleBuilt for all 4 spinners.

---

#### CameraPathCreated
Fired when the flyover camera animation path is defined (optional).

| Field | Type | Description |
|-------|------|-------------|
| pathId | string | "flyover_path" |
| controlPoints | Position3D[] | path waypoints |
| duration | seconds | total flyover time |
| frameRange | [integer, integer] | start and end frames |
| timestamp | datetime | build step completion time |

**Triggers**: Flyover render can be executed.

**Preconditions**: All holes and landscaping are in place.

---

### Phase 5: Material and Landscaping Events

#### MaterialApplied
Fired each time a PBR material is assigned to a mesh object or set of objects.

| Field | Type | Description |
|-------|------|-------------|
| materialName | string | material identifier |
| targetObjects | string[] | Blender object names |
| contextArea | string | which context triggered this |
| roughness | float | 0-1 |
| metallic | float | 0-1 |
| hasNormalMap | boolean | normal map assigned |
| timestamp | datetime | build step completion time |

**Triggers**: Object is visually complete for rendering.

**Preconditions**: Target geometry exists.

**Postconditions**: No default grey material remains on the target objects.

---

#### LandscapingPlaced
Fired when a landscape zone's decorative elements are instanced into the scene.

| Field | Type | Description |
|-------|------|-------------|
| zoneId | string | landscape zone identifier |
| holeNumber | integer | associated hole (or 0 for global) |
| theme | GardenTheme | aesthetic theme |
| plantCount | integer | number of plant instances |
| rockCount | integer | number of rock instances |
| hasWater | boolean | water feature present |
| hasTree | boolean | feature tree present |
| timestamp | datetime | build step completion time |

**Triggers**: MaterialApplied for vegetation and rock surfaces.

**Preconditions**: FairwayConstructed and BordersInstalled for the associated hole.
TerrainModeling has established tier surfaces.

**Postconditions**: Decorative elements surround the hole within defined zone boundaries.

---

#### WaterFeatureActivated
Fired when a water feature's shader is configured with animation (optional).

| Field | Type | Description |
|-------|------|-------------|
| featureId | string | water feature identifier |
| featureType | WaterFeatureType | Waterfall, Pond, Stream |
| hasFlowAnimation | boolean | animated texture offset |
| hasDisplacement | boolean | surface displacement waves |
| timestamp | datetime | build step completion time |

---

### Phase 6: Rendering Events

#### LightingConfigured
Fired when the scene lighting is set up for golden hour rendering.

| Field | Type | Description |
|-------|------|-------------|
| sunAngle | degrees | sun elevation (~15-25) |
| sunAzimuth | degrees | sun direction |
| colorTemperature | kelvin | ~4500K warm |
| environmentType | string | "HDRI" or "Procedural sky" |
| timestamp | datetime | build step completion time |

**Triggers**: Renders can be executed.

**Preconditions**: None (can be set up at any time).

---

#### RenderCompleted
Fired each time a render finishes producing an output file.

| Field | Type | Description |
|-------|------|-------------|
| renderId | string | unique render identifier |
| renderType | string | "overview", "hole_detail", "animation", "flyover" |
| cameraId | string | which camera was used |
| resolution | Resolution | output resolution |
| outputPath | string | file path of rendered image/video |
| frameCount | integer | 1 for stills, N for animations |
| renderEngine | string | "Cycles" or "EEVEE" |
| renderTime | seconds | wall-clock render time |
| timestamp | datetime | completion time |

**Triggers**: Deliverable is ready for review.

**Preconditions**: LightingConfigured. All geometry and materials in the camera's view
are complete.

**Postconditions**: An image or video file exists at outputPath.

Expected renders:
1. Overview top-down (1 image)
2. Overview perspective (1 image)
3. Per-hole detail (9 images)
4. Windmill animation (1 video/GIF)
5. Camera flyover (1 video, optional)

---

## Event Flow Diagram

```
TerrainCreated
    |
    v
TierEstablished (x7) --> RetainingWallBuilt (per wall)
    |
    v
HolePositioned (x9)
    |
    v
FairwayConstructed (x9) --> BordersInstalled (x9)
    |                             |
    v                             v
CupPlaced (x9)             MaterialApplied (borders)
    |
    v
ObstacleBuilt (per obstacle)
    |
    +--> WindmillConstructed --> WindmillAnimated
    +--> LoopConstructed
    +--> TunnelCarved
    +--> SpinnersBuilt --> SpinnersAnimated
    |
    v
MaterialApplied (obstacles, fairways, terrain)
    |
    v
LandscapingPlaced (per zone) --> WaterFeatureActivated
    |
    v
LightingConfigured
    |
    v
CameraPathCreated (optional)
    |
    v
RenderCompleted (x12+)
```

---

## Event Ordering Constraints

1. TerrainCreated MUST precede all TierEstablished events
2. TierEstablished MUST precede HolePositioned for holes on that tier
3. HolePositioned MUST precede FairwayConstructed for that hole
4. FairwayConstructed MUST precede BordersInstalled and ObstacleBuilt for that hole
5. ObstacleBuilt MUST precede WindmillAnimated / SpinnersAnimated
6. All geometry events MUST precede their MaterialApplied events
7. All scene content MUST be complete before RenderCompleted (for that camera view)
8. LightingConfigured MUST precede any RenderCompleted
9. Holes can be built in parallel (no inter-hole ordering dependency)
10. Landscaping can proceed in parallel with obstacle construction
