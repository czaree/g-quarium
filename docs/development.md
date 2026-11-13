# Development

Last updated for phase 1.5.

## Prerequisites

Python 3.12, Docker (Docker Desktop with Linux containers on Windows/macOS) and `make`.

## First-time setup

```bash
make setup     # creates .venv, installs requirements-dev.txt (pinned)
make test      # should pass in a few seconds
```

## Make targets

| Target | What it does |
| --- | --- |
| `setup` | create `.venv` and install pinned dev dependencies |
| `test` | unit tier: no ffmpeg, sockets, sleeps or Docker. Runs on every machine |
| `test-all` | unit and integration tiers. Requires Linux (named pipes) and ffmpeg |
| `lint` | `ruff check . --fix` |
| `build` | `docker build` tagged `g-quarium:dev` with the current git SHA |
| `dev` | run `docker-compose.dev.yml`: software encode, sample music, live code mount |
| `clean` | `docker compose down -v` for the dev stack |

On Windows or macOS, `make test-all` skips what needs named pipes. Run it inside the container
or in CI for the full set.

## What successful setup looks like

`make dev` logs a line like `g-quarium starting version=dev encoder=software tracks=4`.
`http://localhost:8080/health` returns:

```json
{"status": "ok", "app": "g-quarium", "version": "dev", "pipeline": "idle",
 "tracks": 4, "clients": 0, "now_playing": {"playing": false}}
```

Opening `http://localhost:8080/stream.ts` in VLC plays music over the overlay. `/health` then
shows `"pipeline": "running"`, `"clients": 1` and the current track under `now_playing`. Close
VLC and the pipeline stops after `IDLE_GRACE_S` (10 s in the dev stack).

The dev stack mounts `./gquarium` into the container read-only: edit code, then restart the
container (`docker compose -f docker-compose.dev.yml restart`) to apply it.

## Layout

See [architecture](architecture.md) for the rules. In short: `core` (settings, logging),
`library` (tracks, tags, shuffle, sources), `scene` (frames), `media` (clock, audio, encoder,
pipeline), `streaming` (broadcaster, lifecycle service), `web` (server, router, controllers,
views), and `bootstrap.py`, which wires them together. Run with `python -m gquarium`.

## Adding an endpoint

1. A controller in `gquarium/web/controllers/<name>.py`: `(request, services) -> Response`.
2. A view in `gquarium/web/views.py` if it formats model data (formatting lives only there).
3. A route in `gquarium/web/router.py` (`ROUTES`).
4. A unit test in `tests/unit/web/controllers/` using the `services` fixture (fake services).

## Adding a module or test

Put code in the package that owns the responsibility and respect the import rules
(`tests/unit/test_architecture.py` fails if you don't). Read settings only via `Settings`. Never
call `os.environ` outside `core/config.py` and `bootstrap.py`. Unit tests mirror the package tree
under `tests/unit/`. Anything that needs ffmpeg or a socket goes in `tests/integration/` with
`pytestmark = pytest.mark.integration`.

## Test tiers

- **Unit** (`tests/unit`): no ffmpeg, sockets, sleeps or Docker. Files only under `tmp_path`. Time
  and timers are injected (`Clock(time_source=...)`, `StreamingService(timer_factory=...)`).
- **Integration** (`tests/integration`): real ffmpeg pipeline smoke test and an HTTP end-to-end
  test over a real socket.
- **Manual**: VAAPI on the server, Jellyfin tuner and guide, real clients, 30-minute A/V sync.

`tests/unit/test_docs.py` fails if an environment variable is missing from
[configuration](configuration.md) or a relative link in the README or `docs/` is broken.

## Common problems

- *`open //./pipe/dockerDesktopLinuxEngine`*: start Docker Desktop first.
- *pip SSL errors in `make setup`*: check proxy/certificates. The install fails fast on purpose.
- *Strange `make` errors on Windows*: `.gitattributes` forces LF line endings. Re-checkout if
  files were converted to CRLF.
