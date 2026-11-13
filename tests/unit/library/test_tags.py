from gquarium.library.tags import read_track
from tests.helpers import touch


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
