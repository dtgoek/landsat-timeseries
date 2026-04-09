"""Preprocessing: scale factors, cloud masking, overlap removal."""

import ee


def apply_scale_factors_l457(image: ee.Image) -> ee.Image:
    """Apply USGS Landsat Collection 2 scale factors for Landsat 5/7.

    Raw DN → physical units:
    - Surface reflectance (SR_B*): DN × 0.0000275 + (−0.2) → [0, 1]
    - Surface temperature (ST_B6): DN × 0.00341802 + 149.0 → Kelvin

    Args:
        image: Raw Landsat 5 or 7 image.

    Returns:
        Scaled image with updated bands.
    """
    optical = image.select("SR_B.").multiply(0.0000275).add(-0.2)
    thermal = image.select("ST_B6").multiply(0.00341802).add(149.0)
    emissivity = image.select("ST_EMIS").multiply(0.0001)
    return (
        image
        .addBands(optical, overwrite=True)
        .addBands(thermal, overwrite=True)
        .addBands(emissivity, overwrite=True)
    )


def apply_scale_factors_l8(image: ee.Image) -> ee.Image:
    """Apply USGS Landsat Collection 2 scale factors for Landsat 8.

    Same as L5/7 but uses ST_B10 instead of ST_B6 for temperature.

    Args:
        image: Raw Landsat 8 image.

    Returns:
        Scaled image with updated bands.
    """
    optical = image.select("SR_B.").multiply(0.0000275).add(-0.2)
    thermal = image.select("ST_B10").multiply(0.00341802).add(149.0)
    emissivity = image.select("ST_EMIS").multiply(0.0001)
    return (
        image
        .addBands(optical, overwrite=True)
        .addBands(thermal, overwrite=True)
        .addBands(emissivity, overwrite=True)
    )


def mask_clouds_l457(image: ee.Image, config: dict) -> ee.Image:
    """Mask clouds in Landsat 5/7 using QA_PIXEL bit flags.

    Bit flags work by reading individual binary digits from an integer.
    qa.bitwiseAnd(1 << 3) isolates bit 3 (cloud). If it equals 0,
    the pixel is clear.

    Args:
        image: Scaled Landsat 5 or 7 image.
        config: Project configuration dictionary.

    Returns:
        Cloud-masked image with bands renamed to SurfT and Emis.
    """
    qa = image.select("QA_PIXEL")
    cloud_bit = config["masking"]["cloud_bit"]
    confidence_bit = config["masking"]["cloud_confidence_bit"]

    no_cloud = qa.bitwiseAnd(1 << cloud_bit).eq(0)
    no_cloud_conf = qa.bitwiseAnd(1 << confidence_bit).eq(0)

    masked = (
        image
        .updateMask(no_cloud)
        .updateMask(no_cloud_conf)
        .select(["ST_B6", "ST_EMIS"], ["SurfT", "Emis"])
    )
    # Preserve the image timestamp so the time series stays in order
    return masked.copyProperties(image, ["system:time_start"])


def mask_clouds_l8(image: ee.Image, config: dict) -> ee.Image:
    """Mask clouds in Landsat 8 using QA_PIXEL bit flags.

    Args:
        image: Scaled Landsat 8 image.
        config: Project configuration dictionary.

    Returns:
        Cloud-masked image with bands renamed to SurfT and Emis.
    """
    qa = image.select("QA_PIXEL")
    cloud_bit = config["masking"]["cloud_bit"]
    confidence_bit = config["masking"]["cloud_confidence_bit"]

    no_cloud = qa.bitwiseAnd(1 << cloud_bit).eq(0)
    no_cloud_conf = qa.bitwiseAnd(1 << confidence_bit).eq(0)

    masked = (
        image
        .updateMask(no_cloud)
        .updateMask(no_cloud_conf)
        .select(["ST_B10", "ST_EMIS"], ["SurfT", "Emis"])
    )
    return masked.copyProperties(image, ["system:time_start"])


def remove_overlap(image: ee.Image) -> ee.Image:
    """Mask pixels that overlap with the next along-track scene.

    Uses the result of a GEE Join that matched each image with its
    spatial neighbour. Pixels present in the next image are masked out.

    Args:
        image: Image with a 'match' property set by the join.

    Returns:
        Image with overlapping pixels masked.
    """
    next_image = ee.Image(image.get("match"))
    return image.updateMask(next_image.mask().Not())


def preprocess_collection(
    collection: ee.ImageCollection,
    config: dict,
) -> ee.ImageCollection:
    """Apply scaling, cloud masking, and overlap removal to a collection.

    Detects sensor type per image by checking which thermal band exists
    (ST_B6 = L5/L7, ST_B10 = L8), then applies the correct functions.

    Args:
        collection: Merged and sorted raw Landsat ImageCollection.
        config: Project configuration dictionary.

    Returns:
        Preprocessed ImageCollection with SurfT and Emis bands.
    """
    def scale_and_mask(image):
        # ee.Algorithms.If is the GEE equivalent of Python's if/else.
        # We need it here because the condition is evaluated server-side
        # (in the GEE cloud), not locally in Python.
        has_b6 = image.bandNames().contains("ST_B6")
        has_b10 = image.bandNames().contains("ST_B10")

        scaled = ee.Algorithms.If(
            has_b6,
            apply_scale_factors_l457(image),
            ee.Algorithms.If(has_b10, apply_scale_factors_l8(image), image),
        )
        scaled = ee.Image(scaled)

        masked = ee.Algorithms.If(
            has_b6,
            mask_clouds_l457(scaled, config),
            ee.Algorithms.If(has_b10, mask_clouds_l8(scaled, config), scaled),
        )
        return ee.Image(masked)

    preprocessed = collection.map(scale_and_mask)

    if config["masking"]["remove_overlap"]:
        # Find pairs of images from the same path acquired within 100 seconds
        overlap_filter = ee.Filter.And(
            ee.Filter.equals("WRS_PATH", None, "WRS_PATH"),
            ee.Filter.greaterThan(
                "system:time_start", None, "system:time_start"
            ),
            ee.Filter.maxDifference(
                100000, "system:time_start", None, "system:time_start"
            ),
        )
        joined = ee.ImageCollection(
            ee.Join.saveBest("match", "measure", True)
            .apply(preprocessed, preprocessed, overlap_filter)
        )
        has_match = joined.filter(ee.Filter.notNull(["match"]))
        preprocessed = has_match.map(remove_overlap)

    return preprocessed
