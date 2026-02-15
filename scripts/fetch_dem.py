#!/usr/bin/env python3
"""Fetch SRTM DEM and satellite imagery for Eskdale Green area."""
import sys
# Fix: remove broken Python 3.14 path that shadows venv numpy
sys.path = [p for p in sys.path if 'python3.14' not in p]

import requests
import os
import gzip
import json
import struct
import numpy as np
from PIL import Image

OUTDIR = "/home/devuser/workspace/minigolf/gis_data"
os.makedirs(OUTDIR, exist_ok=True)

# Eskdale Green village center
CENTER_LAT = 54.3956
CENTER_LON = -3.3047


def download_srtm():
    """Download SRTM 1-arc-second (30m) DEM tile from AWS."""
    tile = "N54W004"
    url = f"https://elevation-tiles-prod.s3.amazonaws.com/skadi/{tile[:3]}/{tile}.hgt.gz"
    hgt_path = os.path.join(OUTDIR, f"{tile}.hgt")

    if os.path.exists(hgt_path):
        print(f"SRTM tile already exists: {hgt_path}")
        with open(hgt_path, "rb") as f:
            return f.read()

    print(f"Downloading SRTM tile {tile}...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()

    hgt_data = gzip.decompress(r.content)
    with open(hgt_path, "wb") as f:
        f.write(hgt_data)
    print(f"SRTM HGT saved: {hgt_path} ({len(hgt_data)} bytes)")
    return hgt_data


def extract_local_dem(hgt_data, center_lat, center_lon, radius_pixels=40):
    """Extract local DEM around a point. Each pixel ≈ 30m, so 40px ≈ 1200m."""
    n = 3601  # SRTM 1-arc-second grid
    elevations = np.frombuffer(hgt_data, dtype='>i2').reshape((n, n))

    # HGT file covers N54-N55, W004-W003
    row = int((55.0 - center_lat) * (n - 1))
    col = int((center_lon - (-4.0)) * (n - 1))

    print(f"Center pixel: row={row}, col={col}")
    print(f"Elevation at center: {elevations[row, col]}m")

    r1 = max(0, row - radius_pixels)
    r2 = min(n, row + radius_pixels)
    c1 = max(0, col - radius_pixels)
    c2 = min(n, col + radius_pixels)

    local = elevations[r1:r2, c1:c2].copy()

    # Handle void values (-32768)
    local[local < -100] = local[local >= 0].min()

    # Calculate geographic bounds
    lat_n = 55.0 - (r1 / (n - 1))
    lat_s = 55.0 - (r2 / (n - 1))
    lon_w = -4.0 + (c1 / (n - 1))
    lon_e = -4.0 + (c2 / (n - 1))

    coords = {
        "center_lat": center_lat,
        "center_lon": center_lon,
        "north": lat_n,
        "south": lat_s,
        "west": lon_w,
        "east": lon_e,
        "rows": local.shape[0],
        "cols": local.shape[1],
        "elevation_range": [int(local.min()), int(local.max())],
        "center_elevation": int(elevations[row, col]),
        "pixel_size_m": 30,
    }

    np.save(os.path.join(OUTDIR, "eskdale_dem.npy"), local)
    with open(os.path.join(OUTDIR, "eskdale_coords.json"), "w") as f:
        json.dump(coords, f, indent=2)

    print(f"Local DEM: {local.shape}, range {local.min()}-{local.max()}m")
    print(f"Bounds: N={lat_n:.5f}, S={lat_s:.5f}, W={lon_w:.5f}, E={lon_e:.5f}")

    # Create heightmap PNG (normalized 0-255)
    norm = ((local - local.min()) / (local.max() - local.min()) * 255).astype(np.uint8)
    img = Image.fromarray(norm, mode='L')
    heightmap_path = os.path.join(OUTDIR, "eskdale_heightmap.png")
    img.save(heightmap_path)
    print(f"Heightmap: {heightmap_path}")

    return local, coords


def download_satellite_tiles(coords, zoom=15):
    """Download OpenStreetMap tiles for the area as a texture base."""
    import math

    def latlon_to_tile(lat, lon, z):
        lat_rad = math.radians(lat)
        n = 2 ** z
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    # Get tile range
    x1, y1 = latlon_to_tile(coords["north"], coords["west"], zoom)
    x2, y2 = latlon_to_tile(coords["south"], coords["east"], zoom)
    x_min, x_max = min(x1, x2), max(x1, x2)
    y_min, y_max = min(y1, y2), max(y1, y2)

    print(f"OSM tiles: zoom={zoom}, x={x_min}-{x_max}, y={y_min}-{y_max}")
    print(f"Total tiles: {(x_max - x_min + 1) * (y_max - y_min + 1)}")

    # Download and stitch tiles
    tile_size = 256
    width = (x_max - x_min + 1) * tile_size
    height = (y_max - y_min + 1) * tile_size
    mosaic = Image.new('RGB', (width, height))

    headers = {'User-Agent': 'MinigolfCourseBuilder/1.0 (educational project)'}

    for tx in range(x_min, x_max + 1):
        for ty in range(y_min, y_max + 1):
            # Use OpenTopoMap for better terrain visualization
            url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
            try:
                r = requests.get(url, headers=headers, timeout=30)
                if r.status_code == 200:
                    from io import BytesIO
                    tile_img = Image.open(BytesIO(r.content))
                    px = (tx - x_min) * tile_size
                    py = (ty - y_min) * tile_size
                    mosaic.paste(tile_img, (px, py))
                    print(f"  Tile {tx},{ty} OK")
                else:
                    print(f"  Tile {tx},{ty} failed: {r.status_code}")
            except Exception as e:
                print(f"  Tile {tx},{ty} error: {e}")

    satellite_path = os.path.join(OUTDIR, "eskdale_osm.png")
    mosaic.save(satellite_path)
    print(f"OSM mosaic: {satellite_path} ({width}x{height})")

    # Save tile metadata
    tile_meta = {
        "zoom": zoom,
        "x_range": [x_min, x_max],
        "y_range": [y_min, y_max],
        "pixel_size": [width, height],
        "tile_size": tile_size
    }
    with open(os.path.join(OUTDIR, "osm_tile_meta.json"), "w") as f:
        json.dump(tile_meta, f, indent=2)

    return mosaic


def create_geotiff(local_dem, coords):
    """Create GeoTIFF from local DEM using GDAL command-line."""
    # Write raw elevation data
    raw_path = os.path.join(OUTDIR, "eskdale_dem_raw.bin")
    local_dem.astype(np.int16).tofile(raw_path)

    rows, cols = local_dem.shape
    xres = (coords["east"] - coords["west"]) / cols
    yres = (coords["north"] - coords["south"]) / rows

    # Create VRT pointing to raw binary
    vrt = f"""<VRTDataset rasterXSize="{cols}" rasterYSize="{rows}">
  <SRS>EPSG:4326</SRS>
  <GeoTransform>{coords['west']}, {xres}, 0, {coords['north']}, 0, {-yres}</GeoTransform>
  <VRTRasterBand dataType="Int16" band="1">
    <SourceFilename relativeToVRT="1">eskdale_dem_raw.bin</SourceFilename>
    <ImageOffset>0</ImageOffset>
    <PixelOffset>2</PixelOffset>
    <LineOffset>{cols * 2}</LineOffset>
  </VRTRasterBand>
</VRTDataset>"""

    vrt_path = os.path.join(OUTDIR, "eskdale_dem.vrt")
    with open(vrt_path, "w") as f:
        f.write(vrt)

    print(f"VRT created: {vrt_path}")
    return vrt_path


if __name__ == "__main__":
    # 1. Download SRTM DEM
    hgt_data = download_srtm()

    # 2. Extract local area (40px = ~1200m radius)
    local_dem, coords = extract_local_dem(hgt_data, CENTER_LAT, CENTER_LON, radius_pixels=40)

    # 3. Create GeoTIFF
    create_geotiff(local_dem, coords)

    # 4. Download satellite tiles
    download_satellite_tiles(coords, zoom=16)

    print("\n=== DEM and imagery ready ===")
    print(f"Files in {OUTDIR}:")
    for f in sorted(os.listdir(OUTDIR)):
        size = os.path.getsize(os.path.join(OUTDIR, f))
        print(f"  {f}: {size:,} bytes")
