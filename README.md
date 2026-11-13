# g-quarium

An always-available Jellyfin Live TV channel that plays a curated random mix of music from your
existing library with a now-playing overlay. It runs headless in Docker, streams only while someone is watching, and can use VAAPI hardware encoding.

## Use it on a server

Requirements: a Linux x86-64 host with Docker and Compose v2, a readable music folder, and
optionally an Intel iGPU with VAAPI (software encoding otherwise).

```bash
# docker-compose.yml expects RENDER_GID in a .env file next to it (see docs/install.md)
docker compose pull && docker compose up -d
curl http://localhost:8080/health
```

Then open `http://<server>:8080/stream.ts` in VLC. Details: [install](docs/install.md) and
[configuration](docs/configuration.md).

## Run it locally

Prerequisites: Python 3.12, Docker (Desktop on Windows/macOS, with Linux containers) and `make`.

```bash
make setup      # create .venv and install pinned dependencies
make test       # unit tests (fast, no ffmpeg or Docker needed)
make dev        # build and run in Docker with software encoding and sample music
```

Check `http://localhost:8080/health` reports `"status": "ok"` and `"version": "dev"`, then open
`http://localhost:8080/stream.ts` in VLC. More in [development](docs/development.md).

## Project layout

| Folder | Contents |
| --- | --- |
| `gquarium/` | the application (Python package, see [architecture](docs/architecture.md)) |
| `tests/` | `unit/` (mirrors the package tree) and `integration/` (real ffmpeg and sockets) |
| `docs/` | install, configuration, development, workflows, architecture |
| `config/` | example `sources.yml` and `settings.yml` |
| `assets/` | `backgrounds/`, `fonts/`, `fish/` (mounted into the container) |
| `samples/` | small music library used by the dev setup and tests |
| `.github/workflows/` | CI ([workflows](docs/workflows.md)) |

Docs index: [install](docs/install.md) · [configuration](docs/configuration.md) ·
[development](docs/development.md) · [workflows](docs/workflows.md) ·
[architecture](docs/architecture.md)
