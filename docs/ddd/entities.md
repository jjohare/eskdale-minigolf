# Entities - Tiered Mini Golf Course

## Overview

Entities are domain objects with a distinct identity that persists through the build
process. Each entity maps to one or more Blender objects and has properties that
must be maintained consistently throughout construction.

---

## Course-Level Entities

### Course
The root entity representing the entire mini golf installation.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "minigolf_tiered_9hole" |
| name | string | "Tiered Mini Golf Course" |
| footprint | Dimensions | 15m x 10m maximum envelope |
| activeArea | Dimensions | ~13m x 9m actual usage |
| totalDrop | ElevationDrop | 3.0m total from top to bottom |
| holeCount | integer | 9 (fixed) |
| totalPar | integer | 27 (fixed) |
| style | string | "Naturalistic English garden" |
| scale | float | 1.0 (1 Blender unit = 1 meter) |

### Pathway
A walking connection between consecutive holes.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "pathway_01_to_02", etc. |
| fromHole | integer | source hole number |
| toHole | integer | destination hole number |
| length | meters | walking distance |
| width | meters | pathway width (~1.0m) |
| surface | Material | non-slip surface material |
| elevationChange | meters | drop along this pathway |
| hasRamp | boolean | whether it includes a ramp |
| hasSteps | boolean | whether it includes steps |
| hasLighting | boolean | LED accent lighting present |

---

## Hole Entities

### Hole
The primary gameplay entity containing all elements of a single mini golf hole.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "hole_01" through "hole_09" |
| number | integer | 1-9 |
| name | string | display name (e.g., "The Welcome") |
| par | HolePar | 2, 3, or 4 |
| length | HoleLength | 3m to 10m |
| drop | ElevationDrop | elevation change within this hole |
| tierStart | integer | starting tier number |
| tierEnd | integer | ending tier number |
| isSignature | boolean | true only for Hole 5 |
| description | string | narrative description of the hole |

### Tee
The starting platform where the player places the ball.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "tee_01" through "tee_09" |
| holeNumber | integer | parent hole |
| position | Position3D | world-space center |
| dimensions | Dimensions | ~0.5m x 0.5m platform |
| elevation | meters | absolute height |
| material | Material | artificial turf with tee marker |
| markerColor | Color | colored dot or line indicating tee position |

### Fairway
The putting surface between tee and green.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "fairway_01" through "fairway_09" |
| holeNumber | integer | parent hole |
| shape | SplinePath | centerline path from tee to green |
| width | meters | varies, minimum 0.9m |
| widthProfile | float[] | width at sampled points along path |
| slope | SlopeProfile | longitudinal slope changes |
| crossSlope | float | lateral tilt (for banked turns) |
| material | Material | artificial turf |
| contours | ContourMap | subtle surface undulations |

### Green
The final putting surface surrounding the cup.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "green_01" through "green_09" |
| holeNumber | integer | parent hole |
| position | Position3D | center of the green |
| shape | ClosedSpline | outline of the green area |
| minWidth | meters | >= 0.9m |
| typicalWidth | meters | ~1.2m |
| slope | SlopeProfile | subtle breaks toward the cup |
| material | Material | artificial turf (slightly different shade) |
| isRaised | boolean | true for Hole 9 |
| raiseHeight | meters | elevation above surrounding area |

### Cup
The target hole where the ball finishes.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "cup_01" through "cup_09" |
| holeNumber | integer | parent hole |
| position | Position3D | center of the cup |
| diameter | meters | 0.108 (108mm standard) |
| depth | meters | ~0.1m |
| rimMaterial | Material | metal (stainless steel) |
| hasFlag | boolean | true for Hole 9 (celebration flag) |
| hasBell | boolean | true for Hole 9 (decorative bell/gong) |

### Border
Continuous rail along the fairway perimeter.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "border_01a", "border_01b", etc. |
| holeNumber | integer | parent hole |
| path | SplinePath | rail centerline |
| height | meters | 0.10m (10cm) |
| profile | CrossSection | rounded top edge |
| material | Material | natural stone |
| hasGap | boolean | true at obstacle entry/exit points |
| gapWidth | meters | width of any gap (for obstacle transitions) |

---

## Obstacle Entities

### WindmillStructure
The building body of the windmill on Hole 5.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "windmill_structure" |
| position | Position3D | base center position |
| height | meters | 1.5m total |
| style | string | "Dutch traditional" |
| bodyShape | Geometry | hexagonal or cylindrical base |
| roofShape | Geometry | conical or pyramidal cap |
| material | Material | timber and plaster |
| openingPosition | Position3D | ground-level ball passage |
| openingWidth | meters | 0.15m (15cm) |
| openingHeight | meters | 0.10m (ball clearance) |

### WindmillBlade
One of four rotating blades on the windmill.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "windmill_blade_1" through "windmill_blade_4" |
| index | integer | 0-3 (90-degree offset each) |
| length | meters | ~0.75m (from hub to tip) |
| width | meters | ~0.2m |
| material | Material | timber with fabric/lattice detail |
| rotationOffset | Rotation | index * 90 degrees |
| pivotPoint | Position3D | hub center on windmill |

### LoopTrack
The vertical loop-de-loop enclosed track on Hole 5.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "loop_track" |
| position | Position3D | center of the loop circle |
| diameter | meters | 0.6m |
| trackWidth | meters | ~0.08m (ball width + clearance) |
| trackDepth | meters | ~0.05m (channel depth) |
| enclosureMaterial | Material | transparent (acrylic/glass) |
| entryAngle | Rotation | angle where ball enters from ramp |
| exitAngle | Rotation | angle where ball exits toward windmill |

### TunnelStructure
Stone tunnel through artificial hill on Hole 6.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "tunnel_structure" |
| position | Position3D | tunnel entrance center |
| length | meters | ~2m |
| height | meters | ~0.3m internal clearance |
| width | meters | ~0.5m total (both paths) |
| wallMaterial | Material | natural stone |
| leftPath | TunnelPath | longer, safer route |
| rightPath | TunnelPath | shorter, narrower route |
| mergePoint | Position3D | where paths rejoin |

### TunnelPath
One route through the split tunnel.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "tunnel_path_left", "tunnel_path_right" |
| side | enum | Left or Right |
| length | meters | left is longer, right is shorter |
| width | meters | left is wider, right has narrow gap |
| narrowestPoint | meters | right path minimum width |
| curvature | SplinePath | path centerline through tunnel |

### BridgeDeck
The walking/putting surface of the elevated bridge on Hole 3.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "bridge_deck" |
| position | Position3D | bridge start position |
| length | meters | ~2m span |
| width | meters | 0.6m (deliberate narrowing) |
| railHeight | meters | 0.05m (low side rails) |
| deckMaterial | Material | timber planks |
| railMaterial | Material | timber rails |
| supportCount | integer | 2-4 vertical supports |
| supportMaterial | Material | timber posts |
| clearanceBelow | meters | height above gully floor |

### SteppingStone
One of three raised platform stones on Hole 7.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "stepping_stone_1" through "stepping_stone_3" |
| index | integer | 1-3 along the path |
| position | Position3D | center of stone platform |
| diameter | meters | 0.5m |
| height | meters | elevation above pond surface |
| surfaceMaterial | Material | flat stone top with turf |
| sideMaterial | Material | natural stone |
| connectingRamp | Ramp | short ramp to next stone or fairway |

### RavineGap
The dramatic gap crossing on Hole 8.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "ravine_gap" |
| position | Position3D | center of the gap |
| gapWidth | meters | 0.5m |
| depth | meters | ravine depth below fairway |
| launchRamp | Ramp | angled surface for ball launch |
| landingPad | LandingZone | receiving area on far side |
| catchNet | CatchNet | safety net below gap |
| alternativePath | SplinePath | winding path around the ravine |

### PinwheelSpinner
One of four spinning obstacles on Hole 9.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "spinner_1" through "spinner_4" |
| index | integer | 1-4 along the fairway |
| position | Position3D | post base position |
| side | enum | Left or Right (alternating) |
| postHeight | meters | ~0.3m |
| bladeCount | integer | 4-6 blades per pinwheel |
| bladeReach | meters | how far blades extend into fairway |
| rotationSpeed | degrees/sec | spin rate |
| material | Material | colorful painted metal |

### BumperStone
A mid-fairway stone obstacle on Hole 2.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "bumper_stone_1", "bumper_stone_2" |
| position | Position3D | center of stone |
| dimensions | Dimensions | roughly spherical, ~0.15m |
| material | Material | natural stone (rounded) |

---

## Landscape Entities

### PlantBed
A defined planting area.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "plantbed_h01_entrance", etc. |
| position | Position3D | center of bed |
| shape | ClosedSpline | bed boundary outline |
| soilMaterial | Material | dark earth/mulch |
| plants | PlantInstance[] | species, position, scale per plant |
| density | float | plants per square meter |

### RockFeature
A decorative stone arrangement.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "rock_feature_h04_center", etc. |
| position | Position3D | center of arrangement |
| rockCount | integer | number of individual stones |
| rocks | RockInstance[] | mesh, position, rotation per rock |
| style | enum | Boulder, Garden, Mossy, Alpine, Dramatic |

### WaterFeature
A decorative water element.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "water_h02_cascade", "water_h05_pond", etc. |
| type | enum | Waterfall, Pond, Stream, Combined |
| position | Position3D | center/start position |
| dimensions | Dimensions | bounding extent |
| depth | meters | water depth (decorative) |
| hasAnimation | boolean | animated shader/flow |
| details | string[] | "water lilies", "koi fish", "reeds", etc. |
| material | Material | water shader (transparent, refractive) |

### FeatureTree
A small ornamental tree at a visual focal point.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "tree_h07_maple", etc. |
| species | string | "Japanese Maple", "Ornamental Cherry", etc. |
| position | Position3D | trunk base position |
| height | meters | 2-4m |
| canopyRadius | meters | crown spread |
| material | Material | bark + foliage materials |

---

## Terrain Entities

### RetainingWall
A structural wall holding a tier edge.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "retwall_tier1_north", etc. |
| tierNumber | integer | which tier boundary |
| path | SplinePath | wall centerline |
| height | meters | tier drop height |
| wallType | enum | NaturalStone, TimberSleeper, GabionBasket |
| material | Material | matching wall type |
| thickness | meters | wall depth |

### Slope
A gradient surface connecting two tiers.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "slope_tier2_to_3", etc. |
| startElevation | meters | top of slope |
| endElevation | meters | bottom of slope |
| gradient | degrees | angle of descent |
| surfaceMaterial | Material | grass or ground cover |
| length | meters | slope run length |

### Ramp
A pathway transition between tiers for pedestrian access.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "ramp_pathway_01_02", etc. |
| startElevation | meters | top of ramp |
| endElevation | meters | bottom of ramp |
| width | meters | ~1.0m |
| gradient | degrees | gentle slope (< 15 degrees) |
| surfaceMaterial | Material | non-slip pathway surface |
| hasHandrail | boolean | for steeper ramps |

---

## Rendering Entities

### Camera
A positioned camera for rendering.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "camera_overview", "camera_hole_01", etc. |
| position | Position3D | camera world position |
| target | Position3D | look-at point |
| focalLength | mm | lens focal length |
| type | enum | Overview, HoleDetail, EyeLevel, Flyover |
| resolution | Resolution | minimum 1920x1080 |

### Light
A light source in the scene.

| Property | Type | Description |
|----------|------|-------------|
| id | string | "sun_main", "led_pathway_01", etc. |
| type | enum | Sun, Area, Point, Spot |
| position | Position3D | world position |
| rotation | Rotation | light direction |
| color | Color | light color temperature |
| intensity | float | light strength |
| castShadows | boolean | shadow casting enabled |
