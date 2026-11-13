# Architecture

Basic architecture of the g-quarium app

## Pipeline

```
 track source ─► shuffle bag ─► audio feeder (per-track ffmpeg decode to PCM, silence between)
                                      │ FIFO audio.pcm
                                      ▼
 timeline (title, artist, album, start) ─► scene renderer (Pillow frames) ─► FIFO video.raw
                                      │
                           long-running encoder ffmpeg (MPEG-TS to stdout)
                                      ▼
                       broadcaster ─► web layer: /stream.ts  /health  /now-playing
```

Python owns the clock and all content decisions, so the overlay text and the audio come from the
same timeline. ffmpeg is a dumb encoder that never restarts between tracks. Timestamps come from
sample and frame counts, not the wall clock. One clock paces both writers.

## Packages and dependency rules

Imports only flow downward. `tests/unit/test_architecture.py` enforces this table.

| Package | Responsibility | May import |
| --- | --- | --- |
| `core` | settings, logging, version | nothing from other packages |
| `library` | track model, tags (filename fallback), shuffle bag, track sources | `core` |
| `scene` | frame renderers behind the `SceneRenderer` protocol | `core`, `library.models` |
| `media` | clock, timeline, audio feeder, encoder command, FIFOs, pipeline | `core`, `library`, `scene.base` |
| `streaming` | broadcaster and the on-demand lifecycle service | `core`, `library`, `media`, `scene` |
| `web` | HTTP server adapter, router, controllers, views | `core`, `streaming`, `library.models` |
| `bootstrap` | composition root | everything |

Rules: dependency injection (collaborators arrive through constructors). Only `core/config.py`
and `bootstrap.py` read environment variables, and only `bootstrap.py` chooses concrete classes.
`scene` never imports `media` (the overlay is handed a now-playing callable and bootstrap wires the
pipeline's timeline into it). `media` pushes bytes into an `OutputSink` that `streaming` supplies
(the broadcaster), which is why `media` never imports `streaming`.

## HTTP layer (MVC-style)

Model = the services, controllers = plain functions `(request, services) -> Response`, views =
pure serializers. No framework: `server.py` is a thin adapter over the standard library server.

- `server.py` parses the socket request into a `Request`, asks the router for a controller, writes
  the `Response`. Unknown paths give 404, wrong methods 405.
- `router.py` holds the route table. `controllers/` holds `health`, `now_playing`, `stream`.
- `views.py` formats model objects. `responses.py` has `JsonResponse`, `TextResponse` and
  `StreamResponse` (an iterator of chunks plus an `on_close` callback the server always calls,
  which is how the lifecycle service learns a viewer left).
- `services.py` is the container (streaming service, settings, version) built once in
  `bootstrap.py`. There are no globals.

## Threading model

While streaming: an audio feeder thread, a video renderer thread, two encoder reader threads
(stdout, stderr), and one HTTP thread per client. While idle, only the Python process and the HTTP
server exist. A grace timer (default 30 s) stops the pipeline after the last viewer leaves. A new
viewer during the grace period cancels it.
