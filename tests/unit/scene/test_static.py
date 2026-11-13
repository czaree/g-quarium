from pathlib import Path

from PIL import ImageFont

from gquarium.core.config import Settings
from gquarium.library.models import Track
from gquarium.media.timeline import Timeline
from gquarium.scene.static import StaticScene
from gquarium.scene.text import fit_text, has_glyph

W, H = 320, 180


def make_scene(tmp_path, track=None):
    timeline = Timeline()
    if track is not None:
        timeline.add(0.0, track)
    settings = Settings(width=W, height=H, assets_dir=tmp_path)
    return StaticScene(settings, timeline.state_at), timeline


def test_frame_is_raw_rgb_of_the_right_size(tmp_path):
    """
    validate background created is RGB color and configured dimensions
    """
    scene, _ = make_scene(tmp_path)
    assert len(scene.frame(0.0)) == W * H * 3


def test_overlay_changes_with_the_track(tmp_path):
    """
    validate "now playing" overlay text changes when new track plays
    """
    a, _ = make_scene(tmp_path, Track(Path("a.mp3"), "Song A", "Artist A", "Album A"))
    b, _ = make_scene(tmp_path, Track(Path("b.mp3"), "Song B", "Artist B", "Album B"))
    assert a.frame(5.0) != b.frame(5.0)


def test_overlay_fades_in(tmp_path):
    """
    validate text overlay fades in
    """
    scene, _ = make_scene(tmp_path, Track(Path("a.mp3"), "Song"))
    start, mid, done = scene.frame(0.0), scene.frame(0.5), scene.frame(2.0)
    assert start != mid != done


def test_static_scene_reuses_the_frame_between_changes(tmp_path):
    """
    validate static background remains the same during a track change
    """
    scene, _ = make_scene(tmp_path, Track(Path("a.mp3"), "Song"))
    first = scene.frame(3.0)
    assert scene.frame(4.0) is first


def test_new_track_triggers_a_new_overlay(tmp_path):
    """
    validate playing a new track triggers a new "now playing" message
    """
    scene, timeline = make_scene(tmp_path, Track(Path("a.mp3"), "Song A"))
    before = scene.frame(5.0)
    timeline.add(6.0, Track(Path("b.mp3"), "Song B"))
    assert scene.frame(8.0) != before


def test_fit_text_shortens_with_ellipsis():
    """
    validate a very long song is truncated (using ...) instead of overflowing
    """
    font = ImageFont.load_default(size=20)
    text = "A very long song title that cannot possibly fit in this width"
    fitted = fit_text(text, font, 120)
    assert fitted.endswith("…") and font.getlength(fitted) <= 120
    assert fit_text("short", font, 500) == "short"


def test_has_glyph_detects_missing_characters():
    """
    validate has_glyph() detects unknown characters (would render as 
    box or similar)
    """
    font = ImageFont.load_default(size=20)
    assert has_glyph(font, "A")
    assert not has_glyph(font, "\uffff")


def test_non_latin_and_accented_titles_render_without_crashing(tmp_path):
    track = Track(Path("a.mp3"), "夜に駆ける", "Sigur Rós", "Ágætis byrjun")
    scene, _ = make_scene(tmp_path, track)
    assert len(scene.frame(3.0)) == W * H * 3


def test_overlay_switch_is_logged_at_debug(tmp_path, caplog):
    """
    validate each overlay track switch leaves one debug line (missing-overlay diagnostics)
    """
    scene, timeline = make_scene(tmp_path, Track(Path("a.mp3"), "Song A"))
    with caplog.at_level("DEBUG", logger="gquarium.scene.static"):
        scene.frame(1.0)
        scene.frame(2.0)  # same track: no new line
        timeline.add(6.0, Track(Path("b.mp3"), "Song B"))
        scene.frame(7.0)
    switches = [r.getMessage() for r in caplog.records if "overlay switched" in r.getMessage()]
    assert len(switches) == 2
    assert "Song A" in switches[0] and "Song B" in switches[1]


def test_no_track_shows_the_app_name_card(tmp_path):
    """
    validate the empty-library card is labelled with the configured app name
    """
    named = StaticScene(Settings(width=W, height=H, assets_dir=tmp_path, app_name="radio-x"),
                        Timeline().state_at)
    default = StaticScene(Settings(width=W, height=H, assets_dir=tmp_path), Timeline().state_at)
    assert named.frame(5.0) != default.frame(5.0)
