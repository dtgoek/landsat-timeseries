"""Extract pixel-level time series from an ee.ImageCollection at point coordinates."""

import pathlib
from pathlib import Path
import pandas as pd
import geopandas as gpd
import ee


def _sample_point(
    collection: ee.ImageCollection,
    lon: float,
    lat: float,
    bands: list[str],
    scale: int,
) -> pd.DataFrame | None:
    """Sample a collection at a single point, memory-safe."""
    
    pt = ee.Geometry.Point([lon, lat])
    
    def sample_image(img):
        vals = img.select(bands).reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=pt,
            scale=scale,
            bestEffort=True,
            maxPixels=1e4,  # safe for point
            tileScale=4,
        )
        return ee.Feature(None, vals).set({
            'millis': img.get('system:time_start'),
            'scene_id': img.id(),
            'time': img.date().format('HH:mm:ss'),
        })
    
    fc = ee.FeatureCollection(collection.map(sample_image))
    fc = fc.filter(ee.Filter.notNull(bands))
    data = fc.getInfo()["features"]
    
    if not data:
        return None
    
    rows = []
    for feature in data:
        props = feature['properties']
        if any(props.get(band) is not None for band in bands):
            rows.append(props)
    
    return pd.DataFrame(rows) if rows else None


def _extract_year(collection: ee.ImageCollection, bands: list[str], lon: float, lat: float, scale: int, year: int) -> pd.DataFrame | None:
    """Extract one year, filtered server-side."""
    
    year_collection = (
        collection
        .filterDate(f"{year}-01-01", f"{year+1}-01-01")
        .select(bands)
    )
    
    if year_collection.size().getInfo() == 0:
        return None
    
    return _sample_point(year_collection, lon, lat, bands, scale)


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
    """Extract a full time series at a single coordinate for one or more bands."""
    
    frames = []
    
    for year in range(start_year, end_year + 1):
        try:
            df_year = _extract_year(collection, bands, lon, lat, scale, year)
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
        raise RuntimeError("No data extracted. Check collection, band names, and date range.")
    
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["millis"], unit="ms")
    df = df.drop(columns=["millis"]).sort_values("date").reset_index(drop=True)
    
    if verbose:
        n_valid = df["SurfT"].notna().sum() if "SurfT" in df.columns else len(df)
        print(f"\nExtracted {len(df)} scenes "
              f"({df['date'].dt.year.min()}–{df['date'].dt.year.max()}) "
              f"| clear: {n_valid} cloudy: {len(df) - n_valid}")
    
    return df


def extract_multipoint_timeseries(
    collection: ee.ImageCollection,
    points: list[dict],
    bands: list[str],
    output_folder: str | Path,  # Folder for ALL output files
    scale: int = 30,
    start_year: int = 1984,
    end_year: int = 2024,
    variable: str = "lst",
    save_merged: bool = True,
) -> pd.DataFrame:
    """Save each point + merged timeseries to output_folder."""
    
    import os
    
    os.makedirs(output_folder, exist_ok=True)
    all_frames = []
    
    for pt in points:
        pid = pt.get("point_id")
        lon = pt.get("lon")
        lat = pt.get("lat")
        
        if pid is None or lon is None or lat is None:
            print(f"Skipping invalid point: {pt}")
            continue
            
        print(f"\n--- {variable.upper()}: {pid} [{lon:.2f}, {lat:.2f}] ---")
        
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
        
        # Add metadata
        df.insert(0, "point_id", pid)
        df.insert(1, "lon", lon)
        df.insert(2, "lat", lat)
        for key, value in pt.items():
            if key not in ["point_id", "lon", "lat"]:
                df[key] = value
        
        all_frames.append(df)
        
        # Auto filename
        safe_pid = str(pid).replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
        point_csv = output_folder / f"{safe_pid}_{variable}_{start_year}-{end_year}.csv"
        df.to_csv(point_csv, index=False)
        print(f"Saved {len(df)} scenes → {point_csv}")
    
    merged = pd.concat(all_frames, ignore_index=True).sort_values(["point_id", "date"]).reset_index(drop=True)
    
    if save_merged:
        merged_csv = output_folder / f"merged_{variable}_{start_year}-{end_year}.csv"
        merged.to_csv(merged_csv, index=False)
        print(f"\nSaved merged → {merged_csv}")
    
    return merged

def load_points_from_geojson(
    geojson_path: str | pathlib.Path,
    point_id_col: str | None = None,
    keep_cols: list[str] | None = None,
) -> list[dict]:
    """Load point coordinates + optional extra columns from GeoJSON."""
    
    import geopandas as gpd
    
    gdf = gpd.read_file(geojson_path)
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.is_valid]
    
    if gdf.empty:
        raise ValueError("No valid Point geometries found.")
    
    # Auto-detect point_id_col
    if point_id_col is None:
        candidate_cols = ["station", "station_id", "point_id", "id", "name"]
        point_id_col = next((col for col in candidate_cols if col in gdf.columns), None)
    
    if point_id_col is None:
        raise ValueError(f"No ID column. Found: {list(gdf.columns)}")
    
    print(f"Loaded {len(gdf)} points using '{point_id_col}'")
    
    points = []
    for _, row in gdf.iterrows():
        if row.geometry is not None and row.geometry.geom_type == 'Point':
            point_data = {
                "point_id": str(row[point_id_col]),
                "lon": float(row.geometry.x),
                "lat": float(row.geometry.y),
            }
            
            # Add kept columns
            if keep_cols:
                for col in keep_cols:
                    if col in gdf.columns:
                        point_data[col] = row[col]
            
            points.append(point_data)
    
    return points