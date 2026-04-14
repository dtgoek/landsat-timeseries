# Landsat LST Time-Series Pipeline

This repository contains a Google Earth Engine based workflow for **Landsat land surface temperature (LST) time-series analysis**. The current pipeline builds a multi-sensor Landsat collection, preprocesses the imagery, applies harmonic regression, and exports coefficient layers that can be used to derive **mean annual land surface temperature (MALST), seasonal amplitude, phase, and long-term LST trends**.

The project also includes utilities for **sampling Landsat-derived variables at point coordinates**, which can be used for validation, station comparison, or extraction of time-series values at field sites.

## What the pipeline does

- Builds a merged Landsat time series in Google Earth Engine.
- Applies preprocessing steps such as scaling, harmonization, optional cloud masking, and optional alongtrack scene overlap removal.
- Fits a harmonic regression model to Landsat LST through time.
- Exports beta coefficients as Earth Engine assets or GeoTIFFs.
- Supports downstream calculation of LST trend and seasonal metrics.
- Includes tools for sampling image values at point locations.

## Typical workflow

1. Define the study area and time range in a YAML config file.
2. Build and preprocess the Landsat image collection.
3. Add harmonic predictor bands and fit the regression model.
4. Export coefficient images.
5. Derive trend and seasonal products or sample values at point coordinates.

## Folder structure

```text
landsat-timeseries/
├── configs/                  # YAML configuration files
├── src/
│   └── rs_timeseries/
│       ├── main.py           # Main pipeline entry point
│       ├── config.py         # Config loading and EE project handling
│       ├── io.py             # AOI creation and collection building
│       ├── preprocessing.py  # Scaling, masking, overlap removal
│       ├── modeling.py       # Harmonic predictors and regression
│       ├── products.py       # Derived LST products
│       ├── export.py         # Export to Drive or EE Assets
│       └── utils.py          # Helper functions
├── scripts/                  # Optional helper or visualization scripts
├── notebooks/                # Exploration and testing notebooks
└── README.md
```

## Current focus

The current version is focused on:
- exporting Landsat harmonic regression beta coefficients,
- deriving LST trend-related products,
- calculate Landsat LST trends including interative outlier filter (thresholding model-observation difference)
- and extracting values at point coordinates for further analysis.

## next
- implement Theil–Sen estimator
