"""Main entry point for the Landsat time series pipeline."""

import argparse
import ee

from rs_timeseries.config import load_config, get_ee_project
from rs_timeseries.io import build_aoi, build_merged_collection
from rs_timeseries.preprocessing import preprocess_collection
from rs_timeseries.modeling import (
    add_harmonic_predictors,
    fit_harmonic_regression,
)
from rs_timeseries.export import export_image


def run_pipeline(config_path: str) -> None:
    """Run the Landsat LST harmonic regression pipeline and export beta coefficients."""

    # --- 1. Load config ---
    config = load_config(config_path)
    print(f"\n=== Pipeline: {config['project']['name']} ===\n")

    # --- 2. Initialize Earth Engine ---
    project_id = get_ee_project()
    if project_id:
        ee.Initialize(project=project_id)
    else:
        ee.Initialize()
    print("Earth Engine initialized.")

    # --- 3. Build and preprocess collection ---
    aoi = build_aoi(config)
    collection = build_merged_collection(config, aoi)
    n_images = collection.size().getInfo()
    print(f"Collection size: {n_images} images")

    collection = preprocess_collection(collection, config)
    print(f"✅ After preprocess: {collection.size().getInfo()} images")

    if collection.size().getInfo() > 0:
        print(f"✅ First image bands: {collection.first().bandNames().getInfo()}")
    else:
        print("❌ EMPTY COLLECTION - check preprocessing filters!")

    collection = collection.map(lambda image: add_harmonic_predictors(image, config))
    print(f"After predictors: {collection.size().getInfo()} images")

    # --- 5. Fit regression ---
    print("Fitting harmonic regression...")
    coefficients = fit_harmonic_regression(collection, config)

    # --- 6. Export beta coefficients ---
    start = config["time"]["start"][:4]
    end = config["time"]["end"][:4]
    date_suffix = f"{start}_{end}"

    coeff_name = f"beta_coeffs_{date_suffix}"
    print(f"Exporting coefficient image: {coeff_name}")
    export_image(coefficients, coeff_name, config)

    print("\n=== Coefficient export task submitted. Check GEE Tasks tab. ===\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Landsat time series analysis pipeline."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/area_harmonic_beta_coeffs.yaml",
        help="Path to the YAML configuration file.",
    )
    args = parser.parse_args()
    run_pipeline(args.config)