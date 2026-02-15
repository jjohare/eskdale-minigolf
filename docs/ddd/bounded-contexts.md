# Bounded Contexts - Tiered Mini Golf Course

## Overview

Eight bounded contexts partition the mini golf course domain into areas with clear
responsibilities, distinct ubiquitous languages, and well-defined interfaces. Each
context corresponds to a phase or concern in the Blender build process.

---

## 1. CourseLayout Context

**Responsibility**: Overall course topology, spatial arrangement of holes on the hillside,
elevation mapping, and pathway routing between holes.

### Owns
- Course footprint boundary (15m x 10m envelope, ~13m x 9m active)
- Switchback/zigzag layout pattern
- Hole position coordinates (tee and green locations)
- Tier definitions (Tier 1 through Tier 6 + base)
- Elevation profile (cumulative drops per hole)
- Pathway geometry between holes (non-slip surfaces)
- Entrance (top) and exit (bottom) locations

### Language
- Tier: a horizontal terrace at a specific elevation
- Switchback: the zigzag routing pattern down the hillside
- Pathway: a walking route connecting one hole's green to the next hole's tee
- Footprint: the bounding rectangle of the entire course
- Elevation profile: the cumulative height change across all 9 holes

### Key Rules
- Holes are arranged in switchback pattern: H1-H2 east, H3-H4 west, H5 center, etc.
- Pathways must include non-slip surfaces and gentle ramps
- Total elevation drop across all pathways and holes sums to 3.0m
- Each tier has at least one retaining wall or transition feature

### Blender Implementation
- Master collection "Course" containing all hole sub-collections
- Empty objects marking tee and green positions with world coordinates
- Spline curves defining pathway centerlines
- Reference planes at each tier elevation

---

## 2. HoleDesign Context

**Responsibility**: Individual hole geometry, putting surfaces, border rails, tee boxes,
cups, and per-hole obstacle integration.

### Owns
- Hole geometry (fairway shape, contours, curves)
- Tee box position and dimensions
- Green (putting surface) shape and slope
- Cup placement (108mm diameter)
- Border rails (10cm height, rounded top edge)
- Par assignment (2-4 per hole, total 27)
- Hole length (3m-10m measured along putting line)
- Green width (minimum 0.9m, typical 1.2m)

### Language
- Tee: the starting position where the ball is placed
- Fairway: the primary putting surface from tee toward the green
- Green: the final putting surface surrounding the cup
- Cup: the 108mm diameter hole where the ball finishes
- Dog-leg: a bend in the fairway direction
- Chicane: a narrowing passage between obstacles
- Banked turn: a fairway surface angled to guide the ball around a curve

### Key Rules
- Every hole has exactly one tee, one cup, and continuous fairway between them
- Border rails are continuous around all putting surfaces (no gaps except entrances)
- Par 2 holes have no major obstacles, par 3 holes have 1-2 obstacles, par 4 has 3+
- Green width never drops below 0.9m except at deliberate narrowing obstacles

### Blender Implementation
- Each hole is a separate collection named "Hole_01" through "Hole_09"
- Fairway mesh with UV-mapped artificial turf material
- Border rail mesh extruded along fairway perimeter spline
- Cup as a cylinder boolean-subtracted from the green surface

---

## 3. ObstacleMechanics Context

**Responsibility**: All mechanical, structural, and interactive obstacle elements that
affect ball path and gameplay.

### Owns
- WindmillObstacle: Dutch-style windmill, 1.5m tall, 4 blades, ground-level opening (15cm)
- LoopObstacle: 0.6m diameter vertical loop-de-loop, enclosed transparent tube
- TunnelObstacle: stone tunnel through artificial hill, split-path interior
- BridgeObstacle: narrow wooden bridge (0.6m wide) with low side rails over gully
- SpiralObstacle: 270-degree banked helical path around rock mound
- SteppingStoneObstacle: 3 raised platforms (0.5m diameter) over decorative pond
- RavineObstacle: gap (0.5m) with launch ramp, catch net, alternative winding path
- SpinnerObstacle: pinwheel-style spinners on posts (4 alternating sides)
- BumperStone: mid-fairway stone obstacles for chicane narrowing

### Language
- Blade gap: the opening between windmill blades that the ball passes through
- Rotation period: time for one complete revolution (4 seconds for windmill)
- Split path: a tunnel fork offering two routes of different risk/reward
- Launch ramp: an angled surface that propels the ball across a gap
- Catch net: safety net below a gap to return missed balls

### Key Rules
- Windmill opening is 15cm wide at ground level
- Loop-de-loop diameter is 0.6m, fully enclosed in transparent material
- Bridge width is 0.6m (deliberate narrowing from standard 1.2m fairway)
- All obstacles must permit a valid ball path (no impossible shots)
- Spinners rotate continuously but do not fully block the path

### Blender Implementation
- Windmill as armature-rigged structure with bone-driven blade rotation
- Loop as a torus segment with transparent material
- Tunnel as boolean-carved geometry through a hill mesh
- Each obstacle type is a reusable asset within its hole collection

---

## 4. Landscaping Context

**Responsibility**: All decorative, naturalistic, and garden elements that surround and
integrate with the course but do not affect ball gameplay.

### Owns
- Planting beds (flower types, placement, density)
- Rock features (boulders, rock gardens, moss-covered stones)
- Water features (waterfalls, ponds, streams, water lilies, reeds, koi)
- Feature trees (ornamental, Japanese maple, small deciduous)
- Ground cover (slope planting, ornamental grasses)
- Garden themes per hole (Dutch at H5, Japanese at H7, Alpine at H4, Butterfly at H6)
- Seating areas and scorecard stations
- Welcome signage and hole markers

### Language
- Planting bed: a defined area filled with vegetation
- Rock garden: an arrangement of stones with low-growing alpine plants
- Feature tree: a small ornamental tree placed at a visual focal point
- Ground cover: low-growing plants on slopes between tiers
- Garden theme: a coherent aesthetic style applied to a hole's surroundings

### Key Rules
- Plants must be low-maintenance species appropriate for English garden aesthetic
- Water features integrate with specific holes (H2, H5, H7, H8) and do not block play
- Rock features provide natural visual transitions between tiers
- Landscaping respects the tier boundaries defined by CourseLayout
- No vegetation overhangs putting surfaces (clear ball path)

### Blender Implementation
- Geometry nodes particle systems for grass and ground cover
- Instanced meshes for repeated plant types
- Sculpted rock meshes with PBR stone materials
- Water planes with animated shader for ponds/streams
- Separate "Landscaping" sub-collection within each hole collection

---

## 5. TerrainModeling Context

**Responsibility**: The underlying ground surface, elevation changes, retaining walls,
slopes, and structural terrain features.

### Owns
- Base terrain mesh (hillside form within 15m x 10m)
- Tier platforms (6 tiers + base, at defined elevations)
- Retaining walls (natural stone, timber sleepers, gabion baskets)
- Slope gradients between tiers
- Gully geometry (Hole 3 bridge gully)
- Ravine geometry (Hole 8)
- Artificial hill (Hole 6 tunnel hill)
- Ramps and steps connecting tiers

### Language
- Tier: a flat or near-flat platform at a defined elevation
- Retaining wall: a vertical structure holding back earth between tier levels
- Gabion basket: a wire cage filled with stones used as a retaining wall
- Timber sleeper: a horizontal timber beam used in retaining wall construction
- Slope gradient: the angle of descent between two tiers
- Gully: a narrow depression spanned by a bridge or feature

### Key Rules
- Elevation drops per hole match the profile: 0, 0.3, 0.3, 0.5, 0.5, 0.4, 0.3, 0.4, 0
- Total terrain drop is 3.0m (2.7m across holes + 0.3m in pathways)
- Retaining walls appear at every tier transition
- Slopes between tiers must be structurally plausible (max ~45 degrees)
- Terrain mesh must be watertight (no holes except deliberate features)

### Blender Implementation
- Subdivided plane sculpted into hillside terrain
- Boolean operations for gully and ravine carving
- Retaining wall meshes aligned to tier boundaries with array modifiers
- Height-based vertex groups for material assignment (grass, dirt, stone)

---

## 6. MaterialsAndTextures Context

**Responsibility**: PBR material definitions, texture mapping, procedural shaders, and
surface appearance for all course elements.

### Owns
- Artificial turf material (fairways and greens)
- Natural stone material (borders, retaining walls, tunnel)
- Timber material (bridge, sleepers, windmill structure)
- Metal material (windmill blades, cup rim, spinners)
- Water shader (ponds, streams, waterfall)
- Transparent material (loop tube, stepping stone walls)
- Plant materials (leaf, bark, petal, grass blade)
- Ground materials (dirt, gravel, non-slip pathway)

### Language
- PBR: Physically Based Rendering material with albedo, roughness, metallic, normal maps
- Roughness: how smooth or rough a surface appears (0=mirror, 1=matte)
- Metallic: whether a surface behaves like a metal or dielectric
- Normal map: a texture encoding surface micro-detail for lighting
- UV mapping: the 2D coordinate system mapping textures onto 3D surfaces
- Procedural: generated mathematically rather than from image textures

### Key Rules
- All visible surfaces must have PBR materials assigned
- Artificial turf uses a consistent green with slight variation noise
- Stone materials vary by context (rough for boulders, smoother for borders)
- Water uses a transparent, refractive shader with animated displacement
- No default grey materials in the final build

### Blender Implementation
- Shader node graphs in Blender's shader editor
- Texture paint for unique details
- Geometry nodes for procedural grass blade generation
- Material slots organized per object with clear naming convention

---

## 7. AnimationAndPhysics Context

**Responsibility**: All time-based behaviors including mechanical animation, optional
ball physics, and camera motion.

### Owns
- Windmill blade rotation keyframes/drivers (4-second period)
- Pinwheel spinner rotation keyframes/drivers
- Optional water flow animation (animated texture offset or displacement)
- Optional ball rigid body simulation
- Optional camera flyover animation path
- Animation timeline and frame range

### Language
- Keyframe: a defined state at a specific frame in the timeline
- Driver: a mathematical expression controlling a property over time
- Rotation period: time for one full 360-degree revolution
- Rigid body: a physics simulation object with mass and collision
- Follow path: a constraint that moves an object along a curve
- Frame range: the start and end frames of an animation

### Key Rules
- Windmill rotates at constant speed: 360 degrees per 4 seconds (90 deg/sec)
- Windmill uses a driver (not keyframes) for continuous looping rotation
- Spinners rotate faster than the windmill but at constant speed
- Physics simulation is optional and separate from mechanical animation
- Camera flyover follows a smooth spline path over the entire course

### Blender Implementation
- Armature with bone constraints for windmill blade rotation
- Driver expressions: `frame * (360 / (fps * 4))` for windmill
- Rigid body world setup if physics demo is included
- Camera follow-path constraint on a NURBS curve for flyover

---

## 8. RenderingPipeline Context

**Responsibility**: Camera placement, lighting setup, render engine configuration, and
output file generation.

### Owns
- Sun lamp and sky environment (HDRI or procedural)
- Golden hour lighting angle and warmth
- Camera objects (overview, per-hole, eye-level)
- Render engine selection (Cycles or EEVEE)
- Resolution settings (1920x1080 minimum)
- Output format (PNG for stills, MP4/GIF for animation)
- Render layers and compositing

### Language
- Golden hour: the period shortly after sunrise or before sunset with warm, low-angle light
- HDRI: High Dynamic Range Image used for environment lighting
- Cycles: Blender's path-tracing render engine for photorealistic output
- EEVEE: Blender's real-time render engine for faster preview
- Compositing: post-render adjustments (color grading, vignette, glare)
- Render pass: a specific data channel (diffuse, glossy, shadow, etc.)

### Key Rules
- All final renders at minimum 1920x1080
- Lighting simulates golden hour (sun elevation ~15-25 degrees, warm color temp)
- Overview camera captures entire course in one frame
- Per-hole cameras frame each hole with surrounding landscaping context
- Animation renders include windmill rotation and spinner motion

### Blender Implementation
- Sun lamp at golden hour angle with warm color temperature (~4500K)
- Sky texture or HDRI for environment
- Named camera objects: "Camera_Overview", "Camera_Hole_01" through "Camera_Hole_09"
- Render settings stored in scene properties
- Output nodes in compositor for final color grading

---

## Context Boundary Summary

| Context | Core/Supporting/Generic | Primary Entities |
|---------|------------------------|------------------|
| CourseLayout | Core | Course, Pathway, Tier |
| HoleDesign | Core | Hole, Tee, Fairway, Green, Cup |
| ObstacleMechanics | Core | Windmill, Loop, Tunnel, Bridge, Spinner |
| Landscaping | Supporting | PlantBed, RockFeature, WaterFeature |
| TerrainModeling | Supporting | TerrainMesh, RetainingWall, Slope |
| MaterialsAndTextures | Generic | Material, Texture, Shader |
| AnimationAndPhysics | Supporting | Animation, Driver, RigidBody |
| RenderingPipeline | Generic | Camera, Light, RenderSettings |
