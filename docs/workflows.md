# Workflows

## ci.yml

**Triggers:** pushes to `main`, tags matching `v*`, and pull requests.

### Jobs

1. `test` (every trigger): installs ffmpeg and the pinned dev dependencies, runs `ruff check .`,
   then the unit tests, then the integration tests.
2. `publish` (everything except pull requests, after `test` passes): builds the Docker image and
   pushes it to `ghcr.io/<owner>/<repo>`.

**Image tags:** `latest` (pushes to `main`), `sha-<short sha>` (every publish) and the version
(`1.2.3` from a `v1.2.3` tag). The git SHA is also baked into the image (`GIT_SHA` build arg), so
`/health` reports it.

**Permissions:** `contents: read` and `packages: write`, using the built-in `GITHUB_TOKEN`; no
secrets to create. Image names must be lowercase.

**Package visibility:** the first published package is private. Make it public in the package's
settings so the server can pull without logging in, or `docker login ghcr.io` on the server with a
token that has only `read:packages`.

**Cutting a release:** `git tag v1.5.0 && git push origin v1.5.0`. CI publishes `:1.5.0` (and
`:sha-...`). Pin that tag in the server's compose file to roll back or hold a version.

**Reading a failure:** open the run on GitHub's Actions tab, expand the red step. `ruff` shows the
file and rule; `pytest` shows the failing test. Re-run from the run's page ("Re-run failed jobs").
Reproduce locally with `make lint` and `make test-all`.

VAAPI can't be tested in CI (no iGPU on the runners); it stays a manual check on the server.