"""Export Earth Engine images to Google Drive or GEE Assets."""

import ee


def export_image(image: ee.Image, name: str, config: dict) -> ee.batch.Task:
    """Export a single image to Drive or as a GEE Asset.

    Args:
        image: The image to export.
        name: Filename for the exported image (without extension).
        config: Project configuration dictionary.

    Returns:
        The submitted GEE export task.
    """
    export_cfg = config["export"]
    aoi = config["aoi"]

    region = ee.Geometry.Rectangle(
        [aoi["xmin"], aoi["ymin"], aoi["xmax"], aoi["ymax"]]
    )

    destination = export_cfg["destination"]

    if destination == "drive":
        task = ee.batch.Export.image.toDrive(
            image=image.clip(region),
            description=name,
            folder=export_cfg["folder"],
            scale=export_cfg["scale"],
            crs=export_cfg["crs"],
            maxPixels=int(float(export_cfg["max_pixels"])),
            fileFormat="GeoTIFF",
        )
    elif destination == "asset":
        asset_root = export_cfg["asset_root"]
        asset_id = f"{asset_root}/{name}"

        task = ee.batch.Export.image.toAsset(
            image=image.clip(region),
            description=name,
            assetId=asset_id,
            scale=export_cfg["scale"],
            crs=export_cfg["crs"],
            maxPixels=int(float(export_cfg["max_pixels"])),
        )
    else:
        raise ValueError(f"Unknown export destination: {destination}")

    task.start()
    print(f"  Export started: {name} → {destination}")
    return task


def export_all_products(
    products: dict,
    config: dict,
    date_suffix: str,
) -> None:
    """Export all products in the products dictionary.

    Args:
        products: Dictionary of product name → ee.Image.
        config: Project configuration dictionary.
        date_suffix: Date range string appended to filenames.
    """
    for product_name, image in products.items():
        filename = f"{product_name}_{date_suffix}"
        export_image(image, filename, config)
