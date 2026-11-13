"""
the encoder command: a pure function, unit-tested without ffmpeg.
"""

from gquarium.core.config import Settings
from gquarium.media.audio import SAMPLE_RATE


def build_encoder_cmd(s: Settings, audio_fifo: str, video_fifo: str) -> list[str]:
    """
    ffmpeg command: raw PCM + raw RGB frames in, MPEG-TS on stdout.

    timestamps come from sample/frame counts. Both writers are paced by one
    Python clock, so audio and video stay aligned without ffmpeg's wall-clock
    timestamping.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin",
        "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "2",
        "-thread_queue_size", "512", "-probesize", "32", "-analyzeduration", "0",
        "-i", audio_fifo,
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-video_size", f"{s.width}x{s.height}",
        "-framerate", str(s.fps),
        "-thread_queue_size", "64", "-probesize", "32", "-analyzeduration", "0",
        "-i", video_fifo,
        "-map", "1:v", "-map", "0:a",
    ]
    bitrate = [
        "-b:v", f"{s.video_bitrate_k}k",
        "-maxrate", f"{int(s.video_bitrate_k * 1.2)}k",
        "-bufsize", f"{s.video_bitrate_k * 2}k",
        "-g", str(s.fps),  # a keyframe every second, so late joiners sync quickly
    ]
    if s.encoder == "vaapi":
        cmd += ["-vaapi_device", s.vaapi_device, "-vf", "format=nv12,hwupload",
                "-c:v", "h264_vaapi", *bitrate]
    elif s.encoder == "software":
        cmd += ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                "-tune", "zerolatency", *bitrate]
    else:
        raise ValueError(f"unknown ENCODER {s.encoder!r} (use vaapi or software)")
    cmd += [
        "-c:a", "aac", "-b:a", "128k",
        "-f", "mpegts", "-muxdelay", "0", "-flush_packets", "1",
        "-mpegts_flags", "+resend_headers+pat_pmt_at_frames", "-pat_period", "0.5",
        "pipe:1",
    ]
    return cmd
