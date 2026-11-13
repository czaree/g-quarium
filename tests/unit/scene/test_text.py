from PIL import ImageFont

from gquarium.scene.text import FontSet, fit_text, has_glyph


def test_font_set_falls_back_to_builtin_font(tmp_path):
    """
    validate with no asset or system fonts, the built-in font is still returned
    """
    fonts = FontSet(tmp_path, system_fonts=())
    assert len(fonts.candidates(20)) == 1
    assert fonts.font_for("Hello", 20) is not None


def test_font_set_caches_per_size(tmp_path):
    """
    validate font lists are built once per size
    """
    fonts = FontSet(tmp_path, system_fonts=())
    assert fonts.candidates(20) is fonts.candidates(20)
    assert fonts.candidates(20) is not fonts.candidates(24)


def test_unreadable_font_asset_is_skipped(tmp_path):
    """
    validate a corrupt file in assets/fonts is ignored instead of crashing
    """
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "broken.ttf").write_bytes(b"nope")
    fonts = FontSet(tmp_path, system_fonts=())
    assert len(fonts.candidates(20)) == 1


def test_fit_text_leaves_short_text_alone():
    """
    validate text that already fits is returned unchanged
    """
    font = ImageFont.load_default(size=20)
    assert fit_text("ok", font, 500) == "ok"
    assert has_glyph(font, "A")
