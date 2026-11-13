import pytest

from gquarium.core.config import Settings
from gquarium.media.encoder import build_encoder_cmd


def test_software_command():
    """
    validate ffmpeg command with software encoding configured
    """
    cmd = build_encoder_cmd(Settings(encoder="software", width=640, height=360, fps=12),
                            "/tmp/a.pcm", "/tmp/v.raw")
    assert "libx264" in cmd and "h264_vaapi" not in cmd
    assert "640x360" in cmd and "/tmp/a.pcm" in cmd and "/tmp/v.raw" in cmd
    assert cmd[cmd.index("-g") + 1] == "12"
    assert cmd[-1] == "pipe:1" and "mpegts" in cmd


def test_vaapi_command_uploads_frames_to_the_gpu():
    """
    validate ffmpeg command with vaapi encoding configured
    """
    cmd = build_encoder_cmd(Settings(encoder="vaapi", vaapi_device="/dev/dri/renderD128"),
                            "a", "v")
    assert "h264_vaapi" in cmd and "libx264" not in cmd
    assert cmd[cmd.index("-vaapi_device") + 1] == "/dev/dri/renderD128"
    assert cmd[cmd.index("-vf") + 1] == "format=nv12,hwupload"


def test_unknown_encoder_is_rejected():
    """
    validate unknown encoder config is rejected correctly
    """
    with pytest.raises(ValueError):
        build_encoder_cmd(Settings(encoder="nvenc"), "a", "v")
