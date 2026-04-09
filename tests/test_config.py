"""Tests for config loading."""

import pytest
from rs_timeseries.config import load_config


def test_config_loads_successfully():
    """Config file should load and return a dictionary."""
    config = load_config("configs/swiss_alps_lst.yaml")
    assert isinstance(config, dict)


def test_config_has_required_keys():
    """Config must contain the sections the pipeline depends on."""
    config = load_config("configs/swiss_alps_lst.yaml")
    for key in ["project", "aoi", "time", "sensors", "masking", "model", "export"]:
        assert key in config, f"Missing required config section: {key}"


def test_config_target_band():
    """Target band should be SurfT for the LST workflow."""
    config = load_config("configs/swiss_alps_lst.yaml")
    assert config["model"]["target_band"] == "SurfT"


def test_config_file_not_found():
    """A missing config file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("configs/nonexistent.yaml")
