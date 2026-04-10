"""Extract pixel time series at specific coordinates."""

import ee
import pandas as pd


def extract_timeseries_at_points(
    collection: ee.ImageCollection,
    coordinates: list,
    target_band: str,
    scale: int = 30,
) -> pd.DataFrame:
    """Extract a time series of pixel values at a list of coordinates.

    For each date in the collection, the pixel value at each coordinate
    is sampled and returned as a row in a DataFrame.

    Args:
        collection: Preprocessed ImageCollection with the target band.
        coordinates: List of (longitude, latitude) tuples.
        target_band: Band name to extract (e.g. 'SurfT').
        scale: Spatial resolution in metres (30 for Landsat).

    Returns:
        DataFrame with columns: date, value, lon, lat.
    """
    # Create a FeatureCollection of point locations
    points = ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point([lon, lat]), {"id": i})
        for i, (lon, lat) in enumerate(coordinates)
    ])

    def extract_image(image):
        """Sample the target band at all points for one image."""
        date = image.date().format("YYYY-MM-dd")
        sampled = image.select(target_band).sampleRegions(
            collection=points,
            scale=scale,
            geometries=True,
        )
        # Attach the date to each sampled feature
        return sampled.map(lambda f: f.set("date", date))

    # Apply extraction to every image, then flatten into one table
    extracted = collection.map(extract_image).flatten()
    records = extracted.getInfo()["features"]

    rows = []
    for feature in records:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        rows.append({
            "date": props.get("date"),
            "value": props.get(target_band),
            "lon": coords,
            "lat": coords,
        })

    return pd.DataFrame(rows)
