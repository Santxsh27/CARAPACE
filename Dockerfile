FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY schemas ./schemas
COPY examples ./examples
COPY tests ./tests

RUN python -m pip install --no-cache-dir . \
    && groupadd --gid 10001 carapace \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin carapace \
    && mkdir -p /data \
    && chown -R carapace:carapace /app /data

FROM base AS test

RUN python -m pip install --no-cache-dir ".[test]"

USER carapace

ENTRYPOINT ["python", "-m", "unittest"]
CMD ["discover", "-s", "tests", "-v"]

FROM base AS runtime

USER carapace

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=2)"]

CMD ["python", "-m", "carapace_api"]
