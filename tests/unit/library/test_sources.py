from gquarium.library.sources import DirectorySource, scan_tracks
from tests.helpers import touch


def test_scan_finds_nested_and_flat_and_ignores_other_files(tmp_path):
    """
    validate library scanner only checks files in expected Jellyfin 
    Music/ folder format
    """
    touch(tmp_path, "Artist", "Album", "01 Song.mp3")
    touch(tmp_path, "Flat Album", "track.FLAC")
    touch(tmp_path, "Flat Album", "cover.jpg")
    found = scan_tracks(tmp_path, (".mp3", ".flac"))
    assert [p.name for p in found] == ["01 Song.mp3", "track.FLAC"]


def test_scan_missing_folder_is_empty(tmp_path):
    """
    validate path to missing folder is read as empty
    """
    assert scan_tracks(tmp_path / "invalid", (".mp3",)) == []


def test_directory_source_scans_its_root(tmp_path):
    """
    validate DirectorySource is today's scan behind the TrackSource interface
    """
    touch(tmp_path, "A", "one.mp3")
    touch(tmp_path, "A", "notes.txt")
    source = DirectorySource(tmp_path, (".mp3",))
    assert [p.name for p in source.scan()] == ["one.mp3"]
