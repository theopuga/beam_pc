"""Offline tests for the device registry loader."""

import json

import pytest

from beam_pc.data.devices import Device, label_for, load_devices


def _write(tmp_path, entries):
    path = tmp_path / "devices.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


GOOD = {"label": "iphone_13", "ifixit_category": "iPhone 13", "repair_types": ["battery"]}


def test_label_for():
    assert label_for("iPhone 13") == "iphone_13"
    assert label_for("Samsung Galaxy S23") == "samsung_galaxy_s23"
    assert label_for("MacBook Pro") == "macbook_pro"


def test_load_devices_happy_path(tmp_path):
    devices = load_devices(_write(tmp_path, [GOOD]))
    assert devices == [Device(label="iphone_13", ifixit_category="iPhone 13", repair_types=["battery"])]
    assert devices[0].min_photos == 30  # default


def test_load_devices_rejects_bad_label(tmp_path):
    with pytest.raises(ValueError, match="bad label"):
        load_devices(_write(tmp_path, [{**GOOD, "label": "iPhone 13"}]))


def test_load_devices_rejects_duplicates(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        load_devices(_write(tmp_path, [GOOD, GOOD]))


def test_load_devices_rejects_empty_repairs(tmp_path):
    with pytest.raises(ValueError, match="repair_types"):
        load_devices(_write(tmp_path, [{**GOOD, "repair_types": []}]))
