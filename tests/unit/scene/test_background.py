from PIL import Image

from gquarium.scene.background import load_background


def test_gradient_when_no_backgrounds_folder(tmp_path):
    """
    validate a missing assets/backgrounds folder gives a full-size gradient
    """
    img = load_background(tmp_path, 64, 36)
    assert img.size == (64, 36) and img.mode == "RGB"


def test_background_image_is_cropped_to_output_size(tmp_path):
    """
    validate an image in assets/backgrounds is used and fitted to the output size
    """
    (tmp_path / "backgrounds").mkdir()
    Image.new("RGB", (200, 200), (255, 0, 0)).save(tmp_path / "backgrounds" / "red.png")
    img = load_background(tmp_path, 64, 36)
    assert img.size == (64, 36)
    assert img.getpixel((10, 10)) == (255, 0, 0)


def test_unreadable_background_falls_back_to_gradient(tmp_path):
    """
    validate a corrupt image is skipped
    """
    (tmp_path / "backgrounds").mkdir()
    (tmp_path / "backgrounds" / "bad.png").write_bytes(b"not an image")
    assert load_background(tmp_path, 64, 36).size == (64, 36)


def test_singular_background_folder_is_not_read(tmp_path):
    """
    validate the folder name is 'backgrounds' (plural), matching the repo's assets layout
    """
    (tmp_path / "background").mkdir()
    Image.new("RGB", (64, 36), (255, 0, 0)).save(tmp_path / "background" / "red.png")
    assert load_background(tmp_path, 64, 36).getpixel((10, 10)) != (255, 0, 0)
