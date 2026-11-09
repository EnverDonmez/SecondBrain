FROM python:3.12.14-slim-bookworm
WORKDIR /app
COPY pyproject.toml /app/
COPY README.md LICENSE NOTICE requirements.lock requirements.hashes.json /app/
COPY scripts/install_locked.py /app/scripts/
COPY second_brain /app/second_brain
RUN PIP_NO_CACHE_DIR=1 python scripts/install_locked.py && useradd --create-home --uid 10001 brain && mkdir /app/data && chown brain:brain /app/data
USER brain
VOLUME ["/app/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=2)"
# Container listens internally; Compose restricts the published port to host loopback.
CMD ["python", "-m", "second_brain.container_entry"]
