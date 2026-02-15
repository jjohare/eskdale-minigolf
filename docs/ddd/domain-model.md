# Domain Model - Tiered Mini Golf Course

## Strategic Design Overview

This document defines the strategic domain decomposition for the 9-hole tiered mini golf
course Blender build project. The domain model follows DDD strategic patterns to organize
the complexity of a 15m x 10m hillside course with 3m elevation drop, 9 individually
designed holes, animated obstacles, naturalistic landscaping, and PBR rendering pipeline.

---

## Core Domain: Course Design

The core domain encapsulates the primary business value -- designing a playable, visually
compelling mini golf course. This is where the deepest domain knowledge resides and where
modeling precision matters most.

### Subdomains

#### Hole Design
- Individual hole geometry (tee, fairway, green, cup)
- Obstacle placement and integration
- Par assignment and playability validation
- Border rail profiles and putting surface contours
- Each hole as a discrete Blender collection

#### Obstacle Mechanics
- Windmill structure and blade rotation (Hole 5 signature)
- Loop-de-loop enclosed track (0.6m diameter vertical loop)
- Tunnel split-path routing (Hole 6 stone tunnel)
- Bridge elevated sections (Hole 3 wooden bridge)
- Stepping stone platforms (Hole 7)
- Ravine gap with launch ramp (Hole 8)
- Pinwheel spinners (Hole 9 gauntlet)

#### Course Topology
- Switchback/zigzag layout pattern across the hillside
- Hole sequencing and flow (H1 top to H9 bottom)
- Elevation profile management across 6 tiers
- Pathway connections with non-slip surfaces
- Overall footprint within the 13m x 9m active area

### Why This Is Core
Without accurate hole design, obstacle mechanics, and course topology, the entire project
fails its purpose. These elements define what makes the course a playable mini golf
experience versus a generic 3D terrain model.

---

## Supporting Domain: Landscaping

Landscaping transforms the course from a functional layout into a naturalistic English
garden aesthetic. It is not the primary deliverable but is essential for visual quality
and the project's success criteria.

### Subdomains

#### Planting Design
- Flower beds (tulips at windmill, wildflowers at tunnel, seasonal at entrance)
- Ornamental grasses and ground cover on slopes
- Low-maintenance shrubs between holes
- Feature trees (small ornamental, Japanese maple at Hole 7)
- Alpine rock garden succulents (Hole 4 spiral center)

#### Water Features
- Cascading waterfall alongside Hole 2
- Small pond with reeds at windmill base (Hole 5)
- Shallow decorative pond with water lilies (Hole 7)
- Stream at ravine bottom (Hole 8)
- Animated water shaders (optional)

#### Rock and Stone Elements
- Boulder clusters for natural feel
- Moss-covered rocks at Hole 2
- Central rock mound at Hole 4 spiral
- Dramatic rock faces in ravine (Hole 8)
- Rock gardens integrated throughout

#### Lighting
- LED accent lighting along pathways for evening play
- Integrated into landscaping zones rather than rendering pipeline

### Relationship to Core
Landscaping depends on Course Design for spatial boundaries and elevation data.
Planting zones fill the spaces between holes defined by the Course Topology.
Water features integrate with specific hole designs (Holes 2, 5, 7, 8).

---

## Supporting Domain: Animation

Animation brings the course to life and is critical for the signature Hole 5 windmill
and the Hole 9 spinner gauntlet. It sits between the core obstacle mechanics and the
rendering pipeline.

### Subdomains

#### Mechanical Animation
- Windmill blade rotation: continuous, 4-second period, 4 blades
- Pinwheel spinner rotation: continuous, alternating sides
- Blade tip ground-level sweep blocking the passage opening

#### Physics Simulation (Optional)
- Rigid body ball simulation demo
- Ball path through loop-de-loop
- Ball interaction with ramp launches

#### Camera Animation (Optional)
- Flyover camera path for presentation
- Per-hole detail camera sweeps

### Relationship to Core
Animation directly extends Obstacle Mechanics. The windmill's animation defines its
gameplay behavior (timing the shot through the blade gap). Without animation, the
windmill and spinners are static decorations rather than functional obstacles.

---

## Generic Domain: Rendering

Rendering is a technical necessity shared across all Blender projects. No mini-golf-specific
knowledge is needed -- standard PBR workflows, lighting rigs, and camera setups apply.

### Subdomains

#### Materials and Textures
- PBR materials: artificial turf, natural stone, timber, metal, water
- Geometry nodes for grass/vegetation procedural generation
- Transparent materials for loop-de-loop tube and stepping stone walls

#### Lighting
- Outdoor natural lighting: sun + sky environment
- Golden hour time of day (warm tones, dramatic shadows)
- Optional evening LED accent simulation

#### Camera Setup
- Bird's eye overview (top-down)
- Per-hole detail shots (9 angles)
- Eye-level walk-through perspective
- Flyover animation path

#### Output
- Minimum resolution: 1920x1080
- Rendered overview images
- Per-hole detail renders
- Windmill animation render (video/GIF)

### Why This Is Generic
These rendering concerns apply to any architectural visualization in Blender.
The domain knowledge lives in Course Design and Landscaping; rendering merely
presents it. Off-the-shelf Blender workflows and HDRI environments satisfy
all requirements here.

---

## Domain Priorities

| Priority | Domain | Investment Level | Rationale |
|----------|--------|-----------------|-----------|
| 1 | Course Design (Core) | Highest | Defines the entire product |
| 2 | Landscaping (Supporting) | High | Success criteria requirement |
| 3 | Animation (Supporting) | Medium | Signature hole + spinners |
| 4 | Rendering (Generic) | Low | Standard Blender workflows |

## Key Invariants

1. The course MUST fit within 15m x 10m footprint
2. Total elevation drop MUST be approximately 3m (2.7m holes + 0.3m pathways)
3. Every hole MUST have a valid ball path from tee to cup
4. Hole lengths MUST be between 3m and 10m
5. Green width MUST be minimum 0.9m
6. Cup diameter MUST be 108mm (standard)
7. Border rail height MUST be 10cm with rounded top edge
8. Total par MUST equal 27 (par 3 average across 9 holes)
9. The windmill blade rotation period MUST be approximately 4 seconds
10. Each hole MUST exist as a separate Blender collection
