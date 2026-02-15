#!/usr/bin/env python3
"""Blender WebSocket communication utility for the mini golf project."""

import websocket
import json
import sys
import os
import time

BLENDER_WS_URL = os.environ.get("BLENDER_WS_URL", "ws://127.0.0.1:8765")

def send_command(tool: str, params: dict = None, timeout: int = 120) -> dict:
    """Send a command to Blender via WebSocket and return the result."""
    ws = websocket.create_connection(BLENDER_WS_URL, timeout=timeout)
    msg = {"id": str(int(time.time() * 1000)), "tool": tool}
    if params:
        msg["params"] = params
    ws.send(json.dumps(msg))
    result = json.loads(ws.recv())
    ws.close()
    if result.get("status") == "error":
        raise RuntimeError(f"Blender error: {result.get('error', 'unknown')}")
    return result.get("data", result)

def execute_python(code: str, timeout: int = 120) -> dict:
    """Execute Python code in Blender."""
    return send_command("execute_python", {"code": code}, timeout)

def get_scene_info() -> dict:
    """Get current scene information."""
    return send_command("get_scene_info")

def render_image(output_path: str, resolution_x: int = 1920, resolution_y: int = 1080,
                 samples: int = 64, engine: str = "EEVEE") -> dict:
    """Render the current scene to an image file."""
    return execute_python(f"""
import bpy
bpy.context.scene.render.engine = '{"BLENDER_EEVEE_NEXT" if engine == "EEVEE" else "CYCLES"}'
bpy.context.scene.render.resolution_x = {resolution_x}
bpy.context.scene.render.resolution_y = {resolution_y}
if hasattr(bpy.context.scene, 'eevee'):
    bpy.context.scene.eevee.taa_render_samples = {samples}
elif hasattr(bpy.context.scene, 'cycles'):
    bpy.context.scene.cycles.samples = {samples}
bpy.context.scene.render.filepath = '{output_path}'
bpy.ops.render.render(write_still=True)
print('Rendered to {output_path}')
""")

def screenshot(output_path: str, max_size: int = 800) -> dict:
    """Capture viewport screenshot."""
    return send_command("get_viewport_screenshot", {
        "filepath": output_path, "max_size": max_size
    })

def clear_scene() -> dict:
    """Remove all objects from the scene."""
    return execute_python("""
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)
for mesh in list(bpy.data.meshes):
    bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)
print('Scene cleared')
""")

def create_collection(name: str, parent: str = None) -> dict:
    """Create a Blender collection."""
    parent_code = f"bpy.data.collections['{parent}']" if parent else "bpy.context.scene.collection"
    return execute_python(f"""
import bpy
col = bpy.data.collections.new('{name}')
{parent_code}.children.link(col)
print('Created collection: {name}')
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: blender_ws.py <command> [args]")
        print("Commands: scene, clear, render <path>, exec <code>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "scene":
        print(json.dumps(get_scene_info(), indent=2))
    elif cmd == "clear":
        print(json.dumps(clear_scene(), indent=2))
    elif cmd == "render" and len(sys.argv) > 2:
        print(json.dumps(render_image(sys.argv[2]), indent=2))
    elif cmd == "exec" and len(sys.argv) > 2:
        print(json.dumps(execute_python(sys.argv[2]), indent=2))
    elif cmd == "tools":
        print(json.dumps(send_command("list_tools"), indent=2))
    else:
        print(f"Unknown command: {cmd}")
