FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg intel-media-va-driver vainfo python3 python3-venv curl fonts-dejavu-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt .
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY gquarium ./gquarium

# Put late so code changes don't bust the dependency layers above.
ARG GIT_SHA=dev
ENV APP_VERSION=$GIT_SHA
LABEL org.opencontainers.image.revision=$GIT_SHA

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -fsS http://localhost:8080/health || exit 1

CMD ["python", "-m", "gquarium"]
