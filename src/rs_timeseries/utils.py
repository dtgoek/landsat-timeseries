# rs_timeseries/utils.py
import ee

def harmonize_optical_bands(image: ee.Image) -> ee.Image:
    """Add harmonized optical bands with common names across Landsat sensors."""

    has_b6_thermal = image.bandNames().contains("ST_B6")
    has_b10_thermal = image.bandNames().contains("ST_B10")

    l57 = image.select(
        ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"],
        ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"],
    )

    l89 = image.select(
        ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"],
        ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"],
    )

    optical = ee.Image(
        ee.Algorithms.If(
            has_b6_thermal,
            l57,
            ee.Algorithms.If(
                has_b10_thermal,
                l89,
                image.select([])   # ← correct empty image
            )
        )
    )

    return image.addBands(optical, overwrite=True)

def get_thermal_band(image):
    """Returns ST_B6 (L5/L7) or ST_B10 (L8/L9)."""
    thermal = ee.Algorithms.If(
        image.bandNames().contains('ST_B6'),
        image.select('ST_B6'),
        image.select('ST_B10')
    )
    return ee.Image(thermal)

def apply_scale_factors_l457(image):
    """Scale L5/L7: thermal → SurfT(°C), add Emis."""
    thermal = get_thermal_band(image)
    st_kelvin = thermal.multiply(0.00341802).add(149.0)
    surf_t = st_kelvin.subtract(273.15).rename('SurfT')
    emis = ee.Image(0.98).rename('Emis')
    return image.addBands([surf_t, emis])

def apply_scale_factors_l8(image):
    """Scale L8/L9: thermal → SurfT(°C), add Emis."""
    thermal = get_thermal_band(image)
    st_kelvin = thermal.multiply(0.00341802).add(149.0)
    surf_t = st_kelvin.subtract(273.15).rename('SurfT')
    emis = ee.Image(0.98).rename('Emis')
    return image.addBands([surf_t, emis])

def mask_clouds_l457(image, config):
    """L5/L7 cloud/snow masking."""
    cloud_bit = config.get("masking", {}).get("cloud_bit", 4)
    qa = image.select('QA_PIXEL')
    cloud_mask = qa.bitwiseAnd(1 << cloud_bit).Or(qa.bitwiseAnd(1 << 4)).eq(0)
    snow_mask = qa.bitwiseAnd(1 << 3).eq(0)  # Bit 3 = snow for L4/L5/L7
    mask = cloud_mask.And(snow_mask)
    return image.updateMask(mask)


def mask_clouds_l8(image, config):
    """L8/L9 cloud/snow/cirrus masking."""
    cloud_bit = config.get("masking", {}).get("cloud_bit", 4)
    qa = image.select('QA_PIXEL')
    cloud_mask = qa.bitwiseAnd(1 << cloud_bit).Or(qa.bitwiseAnd(1 << 4)).eq(0)
    cirrus_mask = qa.bitwiseAnd(1 << 2).eq(0)
    snow_mask = qa.bitwiseAnd(1 << 3).eq(0)  # Bit 3 = snow for L8/L9
    mask = cloud_mask.And(cirrus_mask).And(snow_mask)
    return image.updateMask(mask)

def remove_overlap(image):
    """Remove overlap pixels."""
    match = ee.Image(image.get('match'))
    return image.updateMask(match.mask().Not())