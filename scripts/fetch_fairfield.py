#!/usr/bin/env python3
"""Fetch DEM and satellite imagery centered on Fairfield, Eskdale Green."""
import sys
sys.path = [p for p in sys.path if 'python3.14' not in p]

import requests
import os
import gzip
import json
import math
import numpy as np
from PIL import Image
from io import BytesIO

OUTDIR = "/home/devuser/workspace/minigolf/gis_data"
os.makedirs(OUTDIR, exist_ok=True)

# Fairfield exact coordinates (from postcode CA19 1UA research)
FAIRFIELD_LAT = 54.3876
FAIRFIELD_LON = -3.3224
FAIRFIELD_ELEV = 50  # meters ASL approximately


def load_srtm():
    """Load the already-downloaded SRTM tile."""
    hgt_path = os.path.join(OUTDIR, "N54W004.hgt")
    if not os.path.exists(hgt_path):
        print("Downloading SRTM tile...")
        r = requests.get(
            "https://elevation-tiles-prod.s3.amazonaws.com/skadi/N54/N54W004.hgt.gz",
            timeout=120
        )
        r.raise_for_status()
        with open(hgt_path, "wb") as f:
            f.write(gzip.decompress(r.content))

    with open(hgt_path, "rb") as f:
        data = f.read()
    return np.frombuffer(data, dtype='>i2').reshape((3601, 3601))


def extract_dem_patch(elevations, lat, lon, radius_px=25):
    """Extract a DEM patch centered on lat/lon. 25px = ~750m radius."""
    n = 3601
    row = int((55.0 - lat) * (n - 1))
    col = int((lon - (-4.0)) * (n - 1))

    r1, r2 = max(0, row - radius_px), min(n, row + radius_px)
    c1, c2 = max(0, col - radius_px), min(n, col + radius_px)

    patch = elevations[r1:r2, c1:c2].copy()
    patch[patch < -100] = patch[patch >= 0].min()

    lat_n = 55.0 - (r1 / (n - 1))
    lat_s = 55.0 - (r2 / (n - 1))
    lon_w = -4.0 + (c1 / (n - 1))
    lon_e = -4.0 + (c2 / (n - 1))

    center_elev = int(elevations[row, col])
    print(f"Center elevation: {center_elev}m")
    print(f"DEM patch: {patch.shape}, range {patch.min()}-{patch.max()}m")
    print(f"Bounds: N={lat_n:.5f}, S={lat_s:.5f}, W={lon_w:.5f}, E={lon_e:.5f}")

    return patch, {
        "center_lat": lat, "center_lon": lon,
        "north": lat_n, "south": lat_s, "west": lon_w, "east": lon_e,
        "rows": int(patch.shape[0]), "cols": int(patch.shape[1]),
        "elevation_range": [int(patch.min()), int(patch.max())],
        "center_elevation": center_elev,
        "pixel_size_m": 30,
    }


def latlon_to_tile(lat, lon, z):
    """Convert lat/lon to OSM tile coordinates."""
    lat_rad = math.radians(lat)
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_latlon(x, y, z):
    """Convert tile coordinates to lat/lon (NW corner of tile)."""
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def download_osm_tiles(lat, lon, zoom=17, margin_tiles=2):
    """Download OSM tiles around a point."""
    cx, cy = latlon_to_tile(lat, lon, zoom)

    x_min = cx - margin_tiles
    x_max = cx + margin_tiles
    y_min = cy - margin_tiles
    y_max = cy + margin_tiles

    tile_size = 256
    width = (x_max - x_min + 1) * tile_size
    height = (y_max - y_min + 1) * tile_size

    print(f"OSM tiles: zoom={zoom}, x={x_min}-{x_max}, y={y_min}-{y_max}")
    print(f"Total: {(x_max - x_min + 1) * (y_max - y_min + 1)} tiles, {width}x{height}px")

    mosaic = Image.new('RGB', (width, height))
    headers = {'User-Agent': 'MinigolfCourseBuilder/1.0'}

    for tx in range(x_min, x_max + 1):
        for ty in range(y_min, y_max + 1):
            url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
            try:
                r = requests.get(url, headers=headers, timeout=30)
                if r.status_code == 200:
                    tile_img = Image.open(BytesIO(r.content))
                    px = (tx - x_min) * tile_size
                    py = (ty - y_min) * tile_size
                    mosaic.paste(tile_img, (px, py))
            except Exception as e:
                print(f"  Tile {tx},{ty} error: {e}")

    # Calculate geographic bounds of mosaic
    nw_lat, nw_lon = tile_to_latlon(x_min, y_min, zoom)
    se_lat, se_lon = tile_to_latlon(x_max + 1, y_max + 1, zoom)

    return mosaic, {
        "zoom": zoom,
        "north": nw_lat, "south": se_lat,
        "west": nw_lon, "east": se_lon,
        "width": width, "height": height,
        "center_px_x": int((lon - nw_lon) / (se_lon - nw_lon) * width),
        "center_px_y": int((nw_lat - lat) / (nw_lat - se_lat) * height),
    }


def create_terrain_texture(dem_patch, coords, osm_img, osm_meta):
    """Create a richly textured terrain image by combining OSM with procedural."""
    # Resize OSM to match DEM grid
    rows, cols = dem_patch.shape
    # For Blender: we want ~2K texture resolution
    tex_size = 2048

    # Crop OSM image to match DEM extent
    # Calculate pixel positions in OSM mosaic that correspond to DEM bounds
    osm_w = osm_meta["west"]
    osm_e = osm_meta["east"]
    osm_n = osm_meta["north"]
    osm_s = osm_meta["south"]

    dem_w = coords["west"]
    dem_e = coords["east"]
    dem_n = coords["north"]
    dem_s = coords["south"]

    # Pixel positions
    px_left = int((dem_w - osm_w) / (osm_e - osm_w) * osm_meta["width"])
    px_right = int((dem_e - osm_w) / (osm_e - osm_w) * osm_meta["width"])
    px_top = int((osm_n - dem_n) / (osm_n - osm_s) * osm_meta["height"])
    px_bottom = int((osm_n - dem_s) / (osm_n - osm_s) * osm_meta["height"])

    # Clamp
    px_left = max(0, px_left)
    px_right = min(osm_meta["width"], px_right)
    px_top = max(0, px_top)
    px_bottom = min(osm_meta["height"], px_bottom)

    cropped = osm_img.crop((px_left, px_top, px_right, px_bottom))
    texture = cropped.resize((tex_size, tex_size), Image.LANCZOS)

    # Create heightmap at texture resolution
    norm_dem = ((dem_patch - dem_patch.min()) / max(1, dem_patch.max() - dem_patch.min()) * 255).astype(np.uint8)
    heightmap = Image.fromarray(norm_dem, mode='L').resize((tex_size, tex_size), Image.LANCZOS)

    # Create a hillshade for enhanced 3D feel
    dem_float = np.array(heightmap.resize((tex_size, tex_size)), dtype=float)
    # Gradient for hillshade
    dy, dx = np.gradient(dem_float)
    # Light from NW
    azimuth = 315 * math.pi / 180
    altitude = 45 * math.pi / 180
    slope = np.arctan(np.sqrt(dx**2 + dy**2))
    aspect = np.arctan2(-dy, dx)
    shade = (
        np.cos(altitude) * np.cos(slope) +
        np.sin(altitude) * np.sin(slope) *
        np.cos(azimuth - aspect)
    )
    shade = ((shade - shade.min()) / (shade.max() - shade.min()) * 255).astype(np.uint8)
    hillshade = Image.fromarray(shade, mode='L')

    # Blend: OSM texture with hillshade overlay
    texture_arr = np.array(texture, dtype=float)
    shade_arr = np.array(hillshade, dtype=float) / 255.0

    # Multiply blend
    for c in range(3):
        texture_arr[:, :, c] = texture_arr[:, :, c] * (0.4 + 0.6 * shade_arr)

    blended = Image.fromarray(texture_arr.astype(np.uint8))

    return blended, heightmap


if __name__ == "__main__":
    print("=== Fairfield, Eskdale Green DEM + Imagery ===")
    print(f"Coordinates: {FAIRFIELD_LAT}, {FAIRFIELD_LON}")

    # 1. Load and extract DEM
    elevations = load_srtm()
    dem_patch, coords = extract_dem_patch(elevations, FAIRFIELD_LAT, FAIRFIELD_LON, radius_px=25)

    # Save DEM data
    np.save(os.path.join(OUTDIR, "fairfield_dem.npy"), dem_patch)
    with open(os.path.join(OUTDIR, "fairfield_coords.json"), "w") as f:
        json.dump(coords, f, indent=2)

    # Save 16-bit heightmap for Blender
    norm16 = ((dem_patch - dem_patch.min()) / max(1, dem_patch.max() - dem_patch.min()) * 65535).astype(np.uint16)
    heightmap16 = Image.fromarray(norm16, mode='I;16')
    heightmap16.save(os.path.join(OUTDIR, "fairfield_heightmap_16bit.png"))

    # 2. Download OSM tiles at zoom 17 (high detail)
    print("\n--- Downloading OSM tiles (zoom 17) ---")
    osm_img, osm_meta = download_osm_tiles(FAIRFIELD_LAT, FAIRFIELD_LON, zoom=17, margin_tiles=3)
    osm_path = os.path.join(OUTDIR, "fairfield_osm_z17.png")
    osm_img.save(osm_path)
    with open(os.path.join(OUTDIR, "fairfield_osm_meta.json"), "w") as f:
        json.dump(osm_meta, f, indent=2)
    print(f"OSM saved: {osm_path}")

    # 3. Create textured terrain
    print("\n--- Creating terrain texture ---")
    texture, heightmap = create_terrain_texture(dem_patch, coords, osm_img, osm_meta)
    texture.save(os.path.join(OUTDIR, "fairfield_terrain_texture.png"))
    heightmap.save(os.path.join(OUTDIR, "fairfield_heightmap.png"))
    print("Terrain texture and heightmap saved")

    # 4. Mark Fairfield position in the texture
    print("\n--- Marking Fairfield location ---")
    # Calculate Fairfield's pixel position in DEM grid
    dem_row = int((coords["north"] - FAIRFIELD_LAT) / (coords["north"] - coords["south"]) * coords["rows"])
    dem_col = int((FAIRFIELD_LON - coords["west"]) / (coords["east"] - coords["west"]) * coords["cols"])
    print(f"Fairfield in DEM grid: row={dem_row}, col={dem_col}")
    print(f"Fairfield elevation from DEM: {dem_patch[min(dem_row, dem_patch.shape[0]-1), min(dem_col, dem_patch.shape[1]-1)]}m")

    # Calculate meters per pixel for Blender scaling
    lat_span_m = (coords["north"] - coords["south"]) * 111320  # degrees to meters
    lon_span_m = (coords["east"] - coords["west"]) * 111320 * math.cos(math.radians(FAIRFIELD_LAT))
    print(f"\nTerrain dimensions: {lat_span_m:.0f}m (N-S) x {lon_span_m:.0f}m (E-W)")
    print(f"DEM resolution: {lat_span_m / coords['rows']:.1f}m/pixel")

    # Save Blender import metadata
    blender_meta = {
        "fairfield_lat": FAIRFIELD_LAT,
        "fairfield_lon": FAIRFIELD_LON,
        "fairfield_dem_row": dem_row,
        "fairfield_dem_col": dem_col,
        "terrain_width_m": lon_span_m,
        "terrain_height_m": lat_span_m,
        "dem_rows": coords["rows"],
        "dem_cols": coords["cols"],
        "elev_min": int(dem_patch.min()),
        "elev_max": int(dem_patch.max()),
        "elev_range": int(dem_patch.max() - dem_patch.min()),
        "fairfield_elev": int(dem_patch[min(dem_row, dem_patch.shape[0]-1), min(dem_col, dem_patch.shape[1]-1)]),
        "texture_size": 2048,
        # For Blender: the mini golf course should go at these normalized coords
        "golf_x_norm": dem_col / coords["cols"],  # 0-1 position
        "golf_y_norm": 1.0 - (dem_row / coords["rows"]),  # flip for Blender Y
    }
    with open(os.path.join(OUTDIR, "fairfield_blender_meta.json"), "w") as f:
        json.dump(blender_meta, f, indent=2)

    print(f"\n=== Files ready for Blender import ===")
    for fn in sorted(os.listdir(OUTDIR)):
        if fn.startswith("fairfield"):
            sz = os.path.getsize(os.path.join(OUTDIR, fn))
            print(f"  {fn}: {sz:,} bytes")
