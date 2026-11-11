#!/usr/bin/env bash
set -euo pipefail

ENC="${ENC:-vaapi}"                      # vaapi | software
MUSIC="${MUSIC:-/music}"
OUT="${OUT:-/out/spike_${ENC}.mp4}"
IMG="${IMG:-}"                           # optional path to a still image
DUR="${DUR:-60}"
DEV="${VAAPI_DEVICE:-/dev/dri/renderD128}"

TRACK="$(find "$MUSIC" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' \
  -o -iname '*.m4a' -o -iname '*.opus' \) | shuf -n 1)"
[ -n "$TRACK" ] || { echo 'no audio files found'; exit 1; }
echo "track: $TRACK"

if [ -n "$IMG" ]; then
  VIN=(-loop 1 -framerate 15 -i "$IMG")
else
  VIN=(-f lavfi -i 'color=c=0x1a3a5a:s=854x480:r=15')
fi

SCALE='scale=854:480:force_original_aspect_ratio=increase,crop=854:480,fps=15'

if [ "$ENC" = vaapi ]; then
  ENCARGS=(-vaapi_device "$DEV" -vf "$SCALE,format=nv12,hwupload" -c:v h264_vaapi -qp 24)
else
  ENCARGS=(-vf "$SCALE,format=yuv420p" -c:v libx264 -preset veryfast -b:v 1500k)
fi

time ffmpeg -hide_banner -y "${VIN[@]}" -i "$TRACK" -t "$DUR" \
  "${ENCARGS[@]}" -c:a aac -b:a 128k -shortest -movflags +faststart "$OUT"