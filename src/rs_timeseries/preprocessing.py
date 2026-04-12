"""Preprocessing: scaling, optional cloud masking, cloud flagging, overlap removal."""

import ee
from . import utils


def preprocess_collection(
    collection: ee.ImageCollection,
    config: dict,
) -> ee.ImageCollection:
    """Apply scaling, optional cloud masking, harmonize optical bands,
    and remove scene overlap.

    Config:
        masking:
            apply_cloud_mask: bool
            remove_overlap: bool

        bands:
            optical: list[str]
                Harmonized optical names, e.g. ["Red", "NIR", "SWIR1"]
    """

    apply_cloud_mask = config.get("masking", {}).get("apply_cloud_mask", True)
    cloud_bit = config.get("masking", {}).get("cloud_bit", 3)
    requested_optical = config.get("bands", {}).get("optical", [])

    def scale_and_prepare(image: ee.Image) -> ee.Image:
        qa = image.select("QA_PIXEL")

        cloud_flag = (
            qa.bitwiseAnd(1 << cloud_bit)
            .Or(qa.bitwiseAnd(1 << 4))   # cloud shadow
            .gt(0)
            .rename("cloud")
            .uint8()
            .unmask(0)
        )

        has_b6 = image.bandNames().contains("ST_B6")
        has_b10 = image.bandNames().contains("ST_B10")

        scaled = ee.Algorithms.If(
            has_b6,
            utils.apply_scale_factors_l457(image),
            ee.Algorithms.If(
                has_b10,
                utils.apply_scale_factors_l8(image),
                image
            ),
        )
        scaled = ee.Image(scaled)

        scaled = utils.harmonize_optical_bands(scaled)

        prepared = ee.Algorithms.If(
            apply_cloud_mask,
            ee.Algorithms.If(
                has_b6,
                utils.mask_clouds_l457(scaled, config),
                ee.Algorithms.If(
                    has_b10,
                    utils.mask_clouds_l8(scaled, config),
                    scaled
                ),
            ),
            scaled,
        )
        prepared = ee.Image(prepared)

        final_bands = ["SurfT", "Emis", "cloud"] + requested_optical

        return (
            prepared
            .addBands(cloud_flag, overwrite=True)
            .select(final_bands)
            .copyProperties(image, image.propertyNames())
        )

    preprocessed = collection.map(scale_and_prepare)

    if config.get("masking", {}).get("remove_overlap", False):
        overlap_filter = ee.Filter.And(
            ee.Filter.equals("WRS_PATH", None, "WRS_PATH"),
            ee.Filter.greaterThan("system:time_start", None, "system:time_start"),
            ee.Filter.maxDifference(100000, "system:time_start", None, "system:time_start")
        )

        joined = ee.ImageCollection(
            ee.Join.saveBest("match", "measure", True)
            .apply(preprocessed, preprocessed, overlap_filter)
        )

        def safe_remove_overlap(image: ee.Image) -> ee.Image:
            has_match = image.propertyNames().contains("match")
            return ee.Image(
                ee.Algorithms.If(
                    has_match,
                    utils.remove_overlap(image),
                    image,
                )
            ).copyProperties(image, image.propertyNames())

        preprocessed = joined.map(safe_remove_overlap)

    return preprocessed