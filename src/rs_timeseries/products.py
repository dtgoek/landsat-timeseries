"""Derive analysis products from harmonic regression coefficients."""

import math
import ee


def compute_malst(b0: ee.Image) -> ee.Image:
    """Mean Annual LST.
    Unit: Kelvin. Scale factor: 100 (divide output by 100 to recover K).
    """
    return b0.multiply(100).int16().rename("MALST")


def compute_lst_trend(b1: ee.Image) -> ee.Image:
    """Linear LST trend.
    Unit: K/year. Scale factor: 1000 (divide by 1000 to recover K/yr).
    """
    return b1.multiply(1000).int16().rename("LSTtrend")


def compute_amplitude(b2: ee.Image, b3: ee.Image) -> ee.Image:
    """Annual amplitude of the harmonic cycle.
    Amplitude = sqrt(b2² + b3²) = hypot(b2, b3).
    Unit: Kelvin. Scale factor: 1000.
    """
    return b3.hypot(b2).multiply(1000).int16().rename("Amplitude")


def compute_phase(b2: ee.Image, b3: ee.Image) -> ee.Image:
    """Phase of the harmonic cycle.
    Phase = atan2(b3, b2), scaled from [-π, π] to [0, 10000].
    Divide by 10000 and rescale to recover radians.
    """
    return (
        b3.atan2(b2)
        .unitScale(-math.pi, math.pi)
        .multiply(10000)
        .uint16()
        .rename("Phase")
    )


def compute_rmse(fitted_collection: ee.ImageCollection) -> ee.Image:
    """Root Mean Squared Error of the harmonic fit.
    RMSE = sqrt( mean( (observed − fitted)² ) )
    Unit: Kelvin. Scale factor: 100.
    """
    return (
        fitted_collection.select("squared_error")
        .reduce(ee.Reducer.mean())
        .sqrt()
        .multiply(100)
        .uint16()
        .rename("RMSE")
    )


def compute_counts(collection: ee.ImageCollection, target_band: str) -> ee.Image:
    """Count of valid (unmasked) observations per pixel."""
    return (
        collection.select(target_band)
        .count()
        .uint16()
        .rename("Counts")
    )


def derive_all_products(
    coefficients: ee.Image,
    fitted_collection: ee.ImageCollection,
    config: dict,
) -> dict:
    """Compute all requested output products.

    Only products that are set to true in the config are computed.
    This avoids unnecessary GEE computation.

    Args:
        coefficients: Image with b0, b1, b2, b3 bands.
        fitted_collection: Collection with 'squared_error' band added.
        config: Project configuration dictionary.

    Returns:
        Dictionary mapping product name to ee.Image.
    """
    target_band = config["model"]["target_band"]
    requested = config["export"]["products"]

    b0 = coefficients.select("b0")
    b1 = coefficients.select("b1")
    b2 = coefficients.select("b2")
    b3 = coefficients.select("b3")

    products = {}
    if requested.get("malst"):
        products["malst"] = compute_malst(b0)
    if requested.get("trend"):
        products["trend"] = compute_lst_trend(b1)
    if requested.get("amplitude"):
        products["amplitude"] = compute_amplitude(b2, b3)
    if requested.get("phase"):
        products["phase"] = compute_phase(b2, b3)
    if requested.get("rmse"):
        products["rmse"] = compute_rmse(fitted_collection)
    if requested.get("counts"):
        products["counts"] = compute_counts(fitted_collection, target_band)

    return products


def export_b0_raw(b0: ee.Image) -> ee.Image:
    """Raw b0 coefficient in Kelvin, float32."""
    return b0.float().rename("b0_raw")

def export_b1_raw(b1: ee.Image) -> ee.Image:
    """Raw b1 trend coefficient in K/year, float32."""
    return b1.float().rename("b1_raw")

def export_b2_raw(b2: ee.Image) -> ee.Image:
    """Raw cosine coefficient, float32."""
    return b2.float().rename("b2_raw")

def export_b3_raw(b3: ee.Image) -> ee.Image:
    """Raw sine coefficient, float32."""
    return b3.float().rename("b3_raw")