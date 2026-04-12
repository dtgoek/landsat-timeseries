## Project structure

This repository follows a modular structure for Landsat-based time series extraction and analysis in alpine environments.

```text
landsat-timeseries/
├── configs/                 # YAML configuration files
├── data/
│   ├── raw/                 # Unmodified input data
│   ├── interim/             # Intermediate extraction and processing outputs
│   ├── processed/           # Analysis-ready datasets
│   └── timeseries/          # Additional time series storage
├── notebooks/               # Exploration and pipeline tests
├── outputs/                 # Final exported products
├── reports/                 # Figures and notes for communication
├── src/rs_timeseries/       # Reusable package code
└── tests/                   # Unit tests
```

## Data flow

The processing workflow is organized into clear stages:

1. **Configuration**  
   Runtime settings such as area of interest, time range, sensors, and preprocessing options are defined in `configs/swiss_alps_lst.yaml`.

2. **Raw input data**  
   Source datasets such as DEMs, station files, and shapefiles are stored in `data/raw/`.  
   Example: `data/raw/stations/imis/imis_stations.geojson`

3. **Collection building**  
   Landsat image collections are assembled in `src/rs_timeseries/io.py`.

4. **Preprocessing**  
   Scaling, harmonization, cloud handling, and related preparation steps are implemented in `src/rs_timeseries/preprocessing.py`.

5. **Extraction**  
   Point-based time series extraction is handled in `src/rs_timeseries/extraction.py`.

6. **Interim outputs**  
   Per-station CSV files and merged extraction tables are stored in `data/interim/`.

7. **Processed outputs**  
   Cleaned and analysis-ready products are written to `data/processed/`.

8. **Final outputs and reporting**  
   Export-ready deliverables go to `outputs/`, and figures or notes for interpretation go to `reports/`.

## Main code modules

- `config.py` — load configuration and environment settings
- `io.py` — build AOI and merged Landsat collections
- `preprocessing.py` — prepare image collections for extraction
- `extraction.py` — extract point time series and save outputs
- `export.py` — export helpers
- `products.py` — derived product generation
- `modeling.py` — downstream analysis and modeling utilities
- `utils.py` — shared helper functions

## Output conventions

Recommended storage locations:

- Raw station inputs: `data/raw/stations/`
- Per-station extracted CSVs: `data/interim/stations_lst/`
- Merged time series tables: `data/interim/timeseries/`
- Analysis-ready tables: `data/processed/tables/`
- Final exported products: `outputs/`
- Figures: `reports/figures/`

Example filenames:

- `ALI2_lst_1984-2022.csv`
- `AMD2_lst_1984-2022.csv`
- `imis_lst_1984-2022.csv`

## Notes

- `data/raw/` should contain only immutable source data.
- `data/interim/` is intended for outputs directly produced by extraction or preprocessing.
- `data/processed/` should contain cleaned, analysis-ready products.
- Notebooks are used for testing, exploration, and diagnostics, while reusable logic should remain in `src/rs_timeseries/`.