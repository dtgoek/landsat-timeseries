"""Initialize GEE asset folders for Landsat pipeline."""

import ee
import os

# Initialize with your project
project_id = 'goekdeniz'
ee.Initialize(project=project_id)

# Create exact folder path from your YAML
folder_path = 'projects/goekdeniz/assets/landsat_timeseries'
ee.data.createAsset({'type': 'FOLDER'}, folder_path)

print(f"Folder created: {folder_path}")
print("Now re-run your pipeline!")