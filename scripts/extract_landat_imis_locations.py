#!/usr/bin/env python
"""Extract Landsat LST time-series at IMIS stations."""

import ee
from pathlib import Path
from rs_timeseries.config import load_config
from rs_timeseries.io import build_aoi, build_merged_collection
from rs_timeseries.preprocessing import preprocess_collection
from rs_timeseries.extraction import extract_multipoint_timeseries, load_points_from_geojson

def main():
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT = SCRIPT_DIR.parent

    config_path = ROOT / "configs" / "sample_pts_landsat578.yaml"
    points_path = ROOT / "data" / "raw" / "stations" / "imis" / "imis_stations.geojson"
    output_dir = ROOT / "outputs" / "imis_stations_landsat"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    config["masking"]["remove_overlap"] = False
    config["masking"]["apply_cloud_mask"] = False

    ee.Initialize()

    aoi = build_aoi(config)
    raw_collection = build_merged_collection(config, aoi)
    collection = preprocess_collection(raw_collection, config)

    bands = ["SurfT", "cloud"]

    points = load_points_from_geojson(
        points_path,
        point_id_col="station",   # change if your column name differs
        keep_cols=None,
    )

    merged_csv = output_dir / "merged_lst_1984-2022.csv"

    df_multi = extract_multipoint_timeseries(
        collection=collection.select(bands),
        points=points,
        bands=bands,
        output_folder=ROOT / "outputs" / "imis_stations_landsat",
        scale=30,
        start_year=1984,
        end_year=2022,
        variable="lst",
        save_merged=False
    )


    print(f"Extraction complete! {len(df_multi)} rows")
    print(df_multi.groupby('point_id').size())

if __name__ == "__main__":
    main()