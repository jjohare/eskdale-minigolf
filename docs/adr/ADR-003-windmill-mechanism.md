# ADR-003: Windmill Mechanism

## Status

Accepted

## Date

2026-02-15

## Context

Hole 5 ("The Windmill") is the signature hole of the course. It features a traditional Dutch-style windmill standing 1.5m tall with 4 rotating blades. The blades complete a full rotation every ~4 seconds. At ground level, the windmill has a 15cm-wide opening through which the ball must pass. The rotating blades periodically sweep past this opening, blocking the ball's path. Players must time their shot to pass through when the gap aligns.

The windmill mechanism requires:
- Continuous blade rotation at a consistent speed (90 degrees per second)
- Visual fidelity: the blades must look like a traditional windmill
- Ground-level interaction: blade tips pass through or near the ball opening
- Compatibility with the ball physics system (rigid body collision detection)
- Reliable playback across the full animation timeline without drift or stutter

The windmill is central to the project's visual identity and must appear in rendered animations and still images.

## Decision

Use **keyframe animation for blade rotation** combined with **rigid body physics for ball interaction** via a separate collision proxy.

### Windmill Structure

1. **Body**: Dutch-style windmill modeled as a tapered octagonal tower. Stone/brick material on the base, wooden cap with a rotating dome. Approximate proportions: 0.6m base diameter, tapering to 0.4m at the cap, 1.5m total height.

2. **Ground Opening**: A 15cm-wide rectangular opening at ground level on the side facing the incoming ball path. The opening is 12cm tall (sufficient for a standard golf ball at ~4.3cm diameter). Modeled as a cutout in the tower mesh.

3. **Exit Opening**: A matching opening on the opposite side of the tower, allowing the ball to pass through.

### Blade Assembly

1. **Hub**: A central rotating hub mounted on the windmill cap. The hub is a separate object (`Windmill_Hub`) parented to the windmill body.

2. **Blades**: 4 blade arms extending from the hub, each approximately 0.7m long (total span ~1.4m). Each blade is a flat lattice frame with angled sail surfaces, consistent with Dutch windmill style. The blades are joined into a single mesh and parented to the hub.

3. **Blocking Arms**: At the base of each blade, a blocking arm extends downward to sweep across the ground-level opening. These arms are part of the blade mesh and rotate with it.

### Animation (Keyframe)

1. **Rotation**: The hub object has a keyframe animation on its Z-rotation (local axis). Frame 1: 0 degrees. Frame 101: 360 degrees (at 25fps, this gives a 4-second period). The animation curve is set to **Linear** interpolation with **Cycles** modifier for infinite looping.

2. **Frame Range**: The animation is designed for a 25fps timeline. One full rotation = 100 frames = 4 seconds. The Cycles modifier on the F-Curve ensures continuous rotation without additional keyframes.

3. **NLA Strip**: The rotation animation is stored as an NLA strip (`Windmill_Rotation`) so it can be independently muted, scaled, or offset without affecting other animations in the scene.

### Physics Interaction (Rigid Body Proxy)

1. **Collision Proxy**: A simplified mesh (`Windmill_Collision`) replicates the blocking arms as flat rectangular planes. This proxy is parented to the hub and rotates with it. It is set as a **Rigid Body: Passive, Animated** object so the physics engine respects its keyframed position.

2. **Tower Collision**: The windmill tower body has a separate rigid body collision shape (Mesh type) set to Passive for the walls and opening edges.

3. **Ball Interaction**: When a rigid body ball (see ADR-012) contacts the collision proxy, it bounces back. When the gap between blocking arms aligns with the opening, the ball passes through.

### Timing Verification

At 4 seconds per rotation with 4 blades, each blade passes the opening every 1 second. The 15cm opening width and blade arm width (~5cm) give approximately 0.67 seconds of clear passage per cycle. This timing is playable (the ball at typical putting speed of ~1-2 m/s passes through in ~0.1 seconds).

## Consequences

### Positive

- **Reliable rotation**: Keyframe animation with linear interpolation and Cycles modifier produces perfectly consistent rotation speed. No physics instability or solver artifacts.
- **Deterministic timing**: The blade position at any frame is mathematically precise, enabling exact calculation of when the opening is clear.
- **Visual quality**: The windmill blades can be detailed models with proper geometry since they are not simulated physics objects.
- **Decoupled systems**: The visual windmill and the physics collision proxy are separate objects. The visual model can be as detailed as needed without impacting physics performance.
- **NLA compatibility**: The rotation animation integrates cleanly with the scene's NLA system for the camera flyover and other animated elements.

### Negative

- **Dual maintenance**: The visual blade mesh and the collision proxy must be kept in sync. If blade geometry changes, the proxy must be updated.
- **Rigid body limitation**: The Passive Animated rigid body type does not conserve energy in collisions. Ball bouncing off the blades may not look perfectly physical. Acceptable for visualization purposes.
- **No wind variation**: Keyframe animation rotates at constant speed. Real windmills vary with wind. This is acceptable for a mini golf course where consistent gameplay timing matters more than environmental realism.

## Alternatives Considered

### Option A: Rigid Body Physics Simulation

Drive the windmill blades entirely through the rigid body physics system using a motor constraint or constant force.

- **Pros**: Fully physical interaction with the ball. Blade speed responds naturally to ball impacts (slowing when hit).
- **Cons**: Physics solvers can be unstable for continuous rotation. The windmill might stall, jitter, or accelerate unpredictably. Motor constraints require careful tuning of force, damping, and friction parameters. The rotation speed is not guaranteed to match the 4-second period exactly. Baking physics adds complexity to the workflow.
- **Rejected because**: The windmill must rotate at a consistent, predictable speed for gameplay timing. Physics simulation introduces instability that undermines the core gameplay mechanic of timing the shot.

### Option C: Drivers and Constraints

Use Blender's driver system to link blade rotation to the current frame number via a Python expression (e.g., `frame * 3.6` for 360 degrees over 100 frames).

- **Pros**: No keyframes needed. Rotation is a mathematical function of time. Clean F-Curve.
- **Cons**: Drivers evaluate per-frame and can have performance overhead in complex scenes. Driver dependencies can cause evaluation order issues with other animated elements. Drivers are less visible in the timeline/dope sheet, making it harder for other artists to understand the animation setup. Driver expressions can break when files are appended or linked.
- **Rejected because**: While technically elegant, drivers are less transparent for collaboration and debugging compared to keyframe animation with a Cycles modifier. The keyframe approach achieves the same result with better discoverability in Blender's standard animation tools.
