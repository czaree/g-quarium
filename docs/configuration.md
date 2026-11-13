# Configuration

## Precedence

Today, settings come from environment variables, then the built-in defaults. Later on, the
order becomes environment variable, then `config/settings.yml`, then the built-in default.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_NAME` | `g-quarium` | Runtime name: log prefix, `/health` `app` field, empty-library overlay label |
| `APP_VERSION` | `dev` | Git SHA baked in by the Docker build (`GIT_SHA`); shown shortened to 7 characters |
| `MUSIC_DIR` | `/music` | Where the music library is mounted |
| `ASSETS_DIR` | `/assets` | Folder holding `backgrounds/`, `fonts/` and `fish/` |
| `ENCODER` | `vaapi` | `vaapi` or `software` (libx264) |
| `VAAPI_DEVICE` | `/dev/dri/renderD128` | Render node used by the VAAPI encoder |
| `WIDTH` | `854` | Output width in pixels |
| `HEIGHT` | `480` | Output height in pixels |
| `FPS` | `15` | Output frame rate (also the keyframe interval, so one keyframe per second) |
| `VIDEO_BITRATE_K` | `1500` | Video bitrate in kbit/s |
| `IDLE_GRACE_S` | `30` | Seconds to keep the pipeline alive after the last viewer leaves |
| `NOW_PLAYING_DELAY_S` | `0` | Trim knob: shifts the overlay later relative to the audio. See the note below |
| `LEAD_S` | `0.5` | How far ahead of real time audio and video are fed to the encoder |
| `SCENE` | `static` | `static`. `aquarium` is accepted but falls back to static until Phase 4 |
| `PORT` | `8080` | HTTP port inside the container |
| `LOG_LEVEL` | `info` | Global log level (`debug`, `info`, `warning`, `error`) |
| `LOG_LEVELS` | empty | Per-module overrides, e.g. `media.pipeline=debug,web=info` |

**`NOW_PLAYING_DELAY_S`:** the overlay is drawn into the same stream as the audio, so `0` is
already in sync. A positive value makes the overlay *lag*: for that many seconds at the start of
every stream it shows the "No music found" card, and each track change appears that much late.

Coming later: `CHANNEL_NAME`, `JELLYFIN_URL`, `JELLYFIN_API_KEY`, `PATH_MAP`.

## Config files (Phase 2)

`config/sources.example.yml` and `config/settings.example.yml` show the planned format. Copy
them to `config/sources.yml` and `config/settings.yml` (both gitignored). **They are not read
yet**: the app currently plays everything under `MUSIC_DIR`.

## Assets

- `assets/backgrounds/`: PNG/JPG/WebP. The first readable image (alphabetically) is cropped to the
  output size. With none, a deep-blue gradient is used.
- `assets/fonts/`: your own `.ttf`/`.otf`/`.ttc`, tried before the system fonts (DejaVu, and Noto
  CJK for Chinese/Japanese/Korean titles, both installed in the image).
- `assets/fish/`: used by the aquarium scene

## Volumes and permissions

`/music` is mounted as read-only. `./config` and `./assets` are mounted from the compose folder.
The pipeline keeps its named pipes in the container's own `/tmp`, never on a mount.
