FROM python:3.12-slim AS runtime

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
    && addgroup --system carapace \
    && adduser --system --ingroup carapace --uid 10001 carapace \
    && chown -R carapace:carapace /app

USER carapace

ENTRYPOINT ["carapace"]
CMD ["verify", "examples/payment-promise.json", "examples/execution-valid.json"]
