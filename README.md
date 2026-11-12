# g-quarium
On-Demand livestream with custom music and aquarium background for use with Jellyfin Live TV.

## How To Install

## Testing Locally
g-quarium is configured for local testing in a dev environment.

### Requirements
1. `make` and `cmake` must be installed in order to set up the venv that installs the rest of the requirements

### How To Run
1. Set up the virtual environment to install the needed dependencies (see [requirements.txt](./requirements.txt) and [requirements-dev.txt](./requirements-dev.txt) for a full list of what will be installed)
```bash
make setup
```
2. run the unit tests
```bash
make test
```

3. launch the docker container locally
    * if running from windows, launch Docker Desktop first! Otherwise, you'll get a "open //./pipe/dockerDesktopLinuxEngine: system cannot find file specified" error
```bash
make dev
```

4. check [http://localhost:8080/health](http://localhost:8080/health) on your local machine and confirm it reports "ok" for status, and "dev" for version
    * Plug the url into the browser, or use a curl command to send a GET 