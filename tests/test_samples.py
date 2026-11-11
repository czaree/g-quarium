from pathlib import Path

from mutagen import File

MUSIC = Path(__file__).parent.parent / "samples" / "music"


def audio_files():
    """
    helper function which fetches
    """
    return sorted(MUSIC.rglob("*.mp3"))


def test_sample_library_has_nested_and_flat_layouts():
    """
    validates music samples have the needed folder structure

    nested {album-name}/{track}.mp3 and {artist-name}/{album-name}/{track}.mp3
    are both expected structures to find under the Jellyfin Music folder
    (see https://jellyfin.org/docs/general/server/media/music/)
    """
    files = audio_files()
    assert len(files) >= 5
    depths = {len(p.relative_to(MUSIC).parts) for p in files}
    assert depths == {2, 3}, "need both flat (Album/track) and nested (Artist/Album/track)"


def test_tagged_sample_is_readable_by_mutagen():
    path = MUSIC / "STAROSTIN" / "Lofi Chill" / "lofi-chill-background-music-30-sec.mp3"
    tags = File(path, easy=True)
    assert tags["title"] == ["lofi-chill-background-music-30-sec"]
    assert tags["artist"] == ["STAROSTIN"]
    assert tags["album"] == ["Lofi Chill"]


def test_untagged_sample_has_no_title():
    tags = File(MUSIC / "Compilation" / "prettyjohn1-lofi-chill-untagged.mp3", easy=True)
    assert not (tags and tags.get("title"))
