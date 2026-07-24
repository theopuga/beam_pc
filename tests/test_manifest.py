from beam_pc.data.manifest import DatasetEntry, load_manifest, scan_dataset_dir, write_manifest


def test_manifest_roundtrip(tmp_path):
    entries = [
        DatasetEntry(image_path="iphone_13/a.jpg", device_label="iphone_13", source="own_photo"),
        DatasetEntry(image_path="thinkpad_t480/b.png", device_label="thinkpad_t480",
                     source="synthetic", split="val"),
    ]
    path = tmp_path / "manifest.jsonl"
    write_manifest(entries, path)
    assert load_manifest(path) == entries


def test_manifest_rejects_bad_source(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        write_manifest([DatasetEntry("x.jpg", "dev", source="ifixit_scrape")], tmp_path / "m.jsonl")


def test_scan_dataset_dir(tmp_path):
    (tmp_path / "iphone_13").mkdir()
    (tmp_path / "iphone_13" / "a.jpg").touch()
    (tmp_path / "iphone_13" / "notes.txt").touch()
    entries = scan_dataset_dir(tmp_path)
    assert len(entries) == 1
    assert entries[0].device_label == "iphone_13"
    assert entries[0].image_path.endswith("a.jpg")
