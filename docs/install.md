# Install

## Prerequisites and compatibility

- Linux x86-64 host with Docker and Compose v2. The published image is `amd64` only.
- Optional: an Intel iGPU with VAAPI (`/dev/dri`). Without it, set `ENCODER=software`.
- A music folder the container can read (mounted read-only at `/music`).
- Port 8080 free.
- If the package on `ghcr.io` is private: `docker login ghcr.io` with a personal token that has
  only the `read:packages` scope.

## Install

1. Copy `docker-compose.yml` to the server.
2. Create a `.env` next to it with the render group's numeric id (`getent group render`):
   `RENDER_GID=105`
3. Edit the music path under `volumes:` if yours is not `/media/jellyfin/Music`.
4. `docker compose pull`

## Run

```bash
docker compose up -d
curl http://localhost:8080/health      # status ok, pipeline idle, your track count
```

Open `http://<server>:8080/stream.ts` in VLC to test. `docker compose logs -f g-quarium` shows
the log. `docker compose down` stops it.

## Update and roll back

`docker compose pull && docker compose up -d`, then confirm `/health` shows the version you
expect. To roll back, pin the image in `docker-compose.yml` to an earlier `:<sha>` or version tag.

## Uninstall

`docker compose down`, then remove the image with `docker rmi ghcr.io/czaree/g-quarium`.
