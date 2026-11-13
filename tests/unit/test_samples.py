from pathlib import Path

from mutagen import File

MUSIC = Path(__file__).resolve().parents[2] / "samples" / "music"
AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".m4a", ".opus", ".wav"}


def audio_files():
    return sorted(p for p in MUSIC.rglob("*") if p.suffix.lower() in AUDIO_EXTS)


def test_sample_library_is_not_empty():
    assert audio_files(), f"no audio files under {MUSIC}"


def test_samples_are_decodable_audio():
    for path in audio_files():
        audio = File(path)  # no tags needed, just a parseable audio file
        assert audio is not None, f"cannot parse {path.name}"
        assert audio.info.length > 0, f"{path.name} has zero length"