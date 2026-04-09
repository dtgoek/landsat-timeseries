"""Build Landsat image collections in Google Earth Engine."""

import ee

LANDSAT_COLLECTIONS = {
    "L5": "LANDSAT/LT05/C02/T1_L2",
    "L7": "LANDSAT/LE07/C02/T1_L2",
    "L8": "LANDSAT/LC08/C02/T1_L2",
}

L7_END_DATE = "2020-01-01"


def build_aoi(config: dict) -> ee.Geometry:
    """Create an Earth Engine bounding box geometry from config."""
    aoi = config["aoi"]
    return ee.Geometry.Rectangle(
        [aoi["xmin"], aoi["ymin"], aoi["xmax"], aoi["ymax"]]
    )


def load_landsat_collection(
    sensor: str,
    start: str,
    end: str,
    aoi: ee.Geometry,
) -> ee.ImageCollection:
    """Load a single Landsat sensor collection filtered by date and area."""
    asset_id = LANDSAT_COLLECTIONS[sensor]

    if sensor == "L7":
        end = min(end, L7_END_DATE)

    return (
        ee.ImageCollection(asset_id)
        .filterDate(start, end)
        .filterBounds(aoi)
    )


def build_merged_collection(config: dict, aoi: ee.Geometry) -> ee.ImageCollection:
    """Build and merge Landsat collections from all requested sensors."""
    start = config["time"]["start"]
    end = config["time"]["end"]
    sensors = config["sensors"]["use"]

    collections = [
        load_landsat_collection(sensor, start, end, aoi)
        for sensor in sensors
    ]

    merged = collections[0]        # ← must start with first collection
    for col in collections[1:]:
        merged = merged.merge(col)

    return merged.sort("system:time_start")