"""Extract pixel-level time series from an ee.ImageCollection at point coordinates.

Public API
----------
extract_point_timeseries(collection, lon, lat, bands, scale, start_year, end_year)
    -> pd.DataFrame with columns [date, <band>, ...]

extract_multipoint_timeseries(collection, points, bands, scale, start_year, end_year)
    -> pd.DataFrame with columns [point_id, lon, lat, date, <band>, ...]

The extraction is batched by year to stay within GEE's per-request memory limit.
Each year is reduced via ee.Image.reduceRegion() — the approach generalises from
single points to polygon geometries by swapping ee.Geometry.Point for a polygon.
"""

import pandas as pd
import ee


# ---------------------------------------------------------------------------
# Low-level GEE helpers
# ---------------------------------------------------------------------------

def _make_reduce_fn(
    geometry: ee.Geometry,
    scale: int,
    tile_scale: int = 4,
) -> callable:
    """Return a mapped function that reduces one image to a single ee.Feature.

    Carries all requested band values and the image timestamp (millis since
    Unix epoch) as feature properties. tileScale=4 keeps per-image memory low.
    """
    def _reduce(img: ee.Image) -> ee.Feature:
        stat = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=scale,
            bestEffort=True,
            maxPixels=1e13,
            tileScale=tile_scale,
        )
        return ee.Feature(geometry, stat).set({"millis": img.date().millis()})

    return _reduce


def _fc_to_dataframe(fc: ee.FeatureCollection, bands: list[str]) -> pd.DataFrame:
    """Pull a FeatureCollection (millis + bands) down to a local DataFrame."""
    prop_names = fc.first().propertyNames()
    prop_lists = (
        fc.reduceColumns(
            reducer=ee.Reducer.toList().repeat(prop_names.size()),
            selectors=prop_names,
        )
        .get("list")
    )
    d = ee.Dictionary.fromLists(prop_names, prop_lists).getInfo()

    df = pd.DataFrame({"millis": d["millis"]})
    for band in bands:
        df[band] = d.get(band)
    return df


# ---------------------------------------------------------------------------
# Year-batched extraction
# ---------------------------------------------------------------------------

def _extract_year(
    collection: ee.ImageCollection,
    bands: list[str],
    reduce_fn: callable,
    year: int,
) -> pd.DataFrame | None:
    """Extract one calendar year. Returns None when no scenes exist."""
    yearly = collection.select(bands).filterDate(
        f"{year}-01-01", f"{year + 1}-01-01"
    )

    if yearly.size().getInfo() == 0:
        return None

    fc = ee.FeatureCollection(yearly.map(reduce_fn))

    if fc.size().getInfo() == 0:
        return None

    return _fc_to_dataframe(fc, bands)


# ---------------------------------------------------------------------------
# Single-point extraction
# ---------------------------------------------------------------------------

def extract_point_timeseries(
    collection: ee.ImageCollection,
    lon: float,
    lat: float,
    bands: list[str],
    scale: int = 30,
    start_year: int = 1984,
    end_year: int = 2024,
    verbose: bool = True,
) -> pd.DataFrame:
    """Extract a full time series at a single coordinate for one or more bands.

    Args:
        collection:  Preprocessed ee.ImageCollection (cloud flag added if needed).
        lon:         Longitude in decimal degrees (WGS-84).
        lat:         Latitude  in decimal degrees (WGS-84).
        bands:       List of band names to extract, e.g. ["SurfT", "cloud"].
        scale:       Nominal pixel scale in metres (default 30 for Landsat).
        start_year:  First year to extract (inclusive, default 1984).
        end_year:    Last  year to extract (inclusive, default 2024).
        verbose:     Print per-year scene counts (default True).

    Returns:
        DataFrame with columns:
            date        — pd.Timestamp (UTC)
            <band> ...  — one column per requested band
        Sorted ascending by date.
    """
    geometry  = ee.Geometry.Point([lon, lat])
    reduce_fn = _make_reduce_fn(geometry, scale)
    frames    = []

    for year in range(start_year, end_year + 1):
        try:
            df_year = _extract_year(collection, bands, reduce_fn, year)
            if df_year is None:
                if verbose:
                    print(f"  {year}: no scenes — skipped")
                continue
            frames.append(df_year)
            if verbose:
                print(f"  {year}: {len(df_year)} scenes")

        except Exception as exc:
            print(f"  {year}: ERROR — {exc}")

    if not frames:
        raise RuntimeError(
            "No data extracted. Check collection, band names, and date range."
        )

    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["millis"], unit="ms")
    df = (
        df.drop(columns=["millis"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    if verbose:
        n_valid = df["SurfT"].notna().sum() if "SurfT" in df.columns else len(df)
        print(f"\nExtracted {len(df)} scenes  "
              f"({df['date'].dt.year.min()}–{df['date'].dt.year.max()})  "
              f"| clear: {n_valid}  cloudy: {len(df) - n_valid}")

    return df


# ---------------------------------------------------------------------------
# Multi-point extraction
# ---------------------------------------------------------------------------

def extract_multipoint_timeseries(
    collection: ee.ImageCollection,
    points: list[dict],
    bands: list[str],
    scale: int = 30,
    start_year: int = 1984,
    end_year: int = 2024,
    save_path: str | None = None,
) -> pd.DataFrame:
    """Extract time series at multiple coordinates and return one merged DataFrame.

    Args:
        collection:  Preprocessed ee.ImageCollection.
        points:      List of dicts with keys: point_id, lon, lat.
                     Example: [{"point_id": "ZRH", "lon": 8.55, "lat": 47.37}]
        bands:       List of band names to extract, e.g. ["SurfT", "cloud"].
        scale:       Nominal pixel scale in metres (default 30 for Landsat).
        start_year:  First year to extract (inclusive).
        end_year:    Last  year to extract (inclusive).
        save_path:   Optional CSV path to auto-save the merged result.

    Returns:
        Long-format DataFrame with columns:
            point_id, lon, lat, date, <band> ...
        Sorted by point_id then date.
    """
    all_frames = []

    for pt in points:
        pid = pt["point_id"]
        lon = pt["lon"]
        lat = pt["lat"]
        print(f"\n--- Extracting: {pid} [{lon}, {lat}] ---")

        df = extract_point_timeseries(
            collection=collection,
            lon=lon,
            lat=lat,
            bands=bands,
            scale=scale,
            start_year=start_year,
            end_year=end_year,
            verbose=True,
        )

        df.insert(0, "point_id", pid)
        df.insert(1, "lon", lon)
        df.insert(2, "lat", lat)
        all_frames.append(df)

    merged = (
        pd.concat(all_frames, ignore_index=True)
        .sort_values(["point_id", "date"])
        .reset_index(drop=True)
    )

    if save_path:
        merged.to_csv(save_path, index=False)
        print(f"\nSaved → {save_path}")

    return merged