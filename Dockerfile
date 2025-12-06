FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

FROM python:3.12-slim
ENV PIP_NO_CACHE_DIR=1
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN useradd -m orbit && chown -R orbit /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
USER orbit
EXPOSE 8000
CMD ["python", "-m", "orbit_remote_mcp", "--transport", "streamable-http"]
