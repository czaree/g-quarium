import random
from pathlib import Path

from app.library import ShuffleBag, read_track, scan_tracks


def touch(root: Path, *parts: str) -> Path:
    path = root.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not really audio")
    return path


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


def test_untagged_nested_file_uses_filename_and_folders(tmp_path):
    """
    validate file without metadata tagged falls back to folder path
    album/artist info
    """
    path = touch(tmp_path, "Some Artist", "Some Album", "03 - My_Song.mp3")
    track = read_track(path, tmp_path)
    assert (track.title, track.artist, track.album) == ("My Song", "Some Artist", "Some Album")


def test_untagged_flat_file_has_album_but_no_artist(tmp_path):
    """
    validate file without metadata tagged and one level deep populates
    using parent as album name
    """
    path = touch(tmp_path, "Lofi Mix", "rainy day.mp3")
    track = read_track(path, tmp_path)
    assert (track.title, track.artist, track.album) == ("rainy day", "", "Lofi Mix")


def test_year_like_filenames_are_not_stripped(tmp_path):
    """
    validate year in track filename is not stripped
    """
    path = touch(tmp_path, "A", "1984 Song.mp3")
    assert read_track(path, tmp_path).title == "1984 Song"


def test_bag_plays_everything_once_per_cycle():
    """
    validate shuffle system plays every track exactly once
    """
    items = [Path(f"{i}.mp3") for i in range(5)]
    bag = ShuffleBag(lambda: items, random.Random(1))
    assert sorted(bag.next() for _ in range(5)) == sorted(items)


def test_bag_never_repeats_across_cycle_boundary():
    """
    validate no single track repeats in a cycle
    """
    items = [Path("a.mp3"), Path("b.mp3")]
    bag = ShuffleBag(lambda: items, random.Random(3))
    seq = [bag.next() for _ in range(200)]
    assert all(x != y for x, y in zip(seq, seq[1:], strict=False))


def test_bag_empty_library_returns_none_and_recovers():
    """
    validate an empty music library returns nothing, but updates
    when a new track is added
    """
    items: list[Path] = []
    bag = ShuffleBag(lambda: items)
    assert bag.next() is None
    items.append(Path("new.mp3"))
    assert bag.next() == Path("new.mp3")
