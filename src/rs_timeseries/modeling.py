"""Generic time series models: harmonic regression."""

import math
import ee


def add_harmonic_predictors(image: ee.Image, config: dict) -> ee.Image:
    """Add harmonic regression predictor bands to an image.

    The four predictors are:
    - constant = 1 everywhere (intercept term)
    - t = years since time_origin (linear trend term)
    - cos1 = cos(2π·t) (cosine of annual cycle)
    - sin1 = sin(2π·t) (sine of annual cycle)

    The combination of cos and sin represents a sinusoidal cycle of
    any amplitude and phase. Together they capture the seasonal pattern.

    Args:
        image: Preprocessed image with the target band present.
        config: Project configuration dictionary.

    Returns:
        Image with added predictor bands.
    """
    time_origin = config["model"]["time_origin"]
    target_band = config["model"]["target_band"]

    date = ee.Date(image.get("system:time_start"))
    # t = fractional years since the reference date
    years = date.difference(ee.Date(time_origin), "year")
    # One full cycle = 2π radians per year
    angle = ee.Image.constant(years).multiply(2 * math.pi).float()

    constant = ee.Image.constant(1).rename("constant")
    t = ee.Image.constant(years).float().rename("t")
    cos1 = angle.cos().rename("cos1")
    sin1 = angle.sin().rename("sin1")

    # Clip to image extent and apply the same mask as the target band.
    # ee.Image.constant() creates a global image with no spatial bounds,
    # so we must constrain it to match the target image.
    mask = image.select(target_band).mask()
    geom = image.geometry()

    def prepare(band):
        return band.clip(geom).updateMask(mask)

    return (
        image
        .addBands(prepare(constant))
        .addBands(prepare(t))
        .addBands(prepare(cos1))
        .addBands(prepare(sin1))
    )


def fit_harmonic_regression(
    collection: ee.ImageCollection,
    config: dict,
) -> ee.Image:
    """Fit a harmonic regression model to the time series.

    Uses GEE's ee.Reducer.linearRegression which solves the system
    β = (X'X)⁻¹ X'Y (ordinary least squares) for every pixel
    in parallel on the GEE servers.

    Args:
        collection: ImageCollection with predictor and target bands.
        config: Project configuration dictionary.

    Returns:
        Image with coefficient bands: b0, b1, b2, b3.
    """
    target_band = config["model"]["target_band"]
    predictors = ["constant", "t", "cos1", "sin1"]

    # linearRegression expects the first numX bands to be predictors
    # and the last numY bands to be the dependent variable(s)
    regression_input = collection.select(predictors + [target_band])
    result = regression_input.reduce(
        ee.Reducer.linearRegression(numX=len(predictors), numY=1)
    )

    # The output is a 2D array image. We flatten it into named bands.
    coefficients = (
        result
        .select("coefficients")
        .arrayProject([0])          # ← [0] is required — collapses rows into 1D
        .arrayFlatten([predictors]) # assign band names
        .rename(["b0", "b1", "b2", "b3"])
    )
    return coefficients


def add_fitted_values(image: ee.Image, coefficients: ee.Image) -> ee.Image:
    """Compute fitted values and squared residuals for one image.

    fitted = b0 + b1·t + b2·cos1 + b3·sin1
    squared_error = (SurfT − fitted)²

    These are used downstream to compute RMSE across the time series.

    Args:
        image: Image with predictor bands and target band.
        coefficients: Image with b0, b1, b2, b3 bands.

    Returns:
        Image with added 'fitted' and 'squared_error' bands.
    """
    predictors = ["constant", "t", "cos1", "sin1"]
    coeff_names = ["b0", "b1", "b2", "b3"]

    # Multiply each predictor by its coefficient, then sum
    fitted = (
        image.select(predictors)
        .multiply(coefficients.select(coeff_names))
        .reduce("sum")
        .rename("fitted")
    )
    squared_error = (
        image.select("SurfT")
        .subtract(fitted)
        .pow(2)
        .rename("squared_error")
    )
    return image.addBands(fitted).addBands(squared_error)
