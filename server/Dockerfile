FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Build dependencies for packages such as PyCairo, ManimPango, and PyAV.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libavdevice-dev \
        libcairo2-dev \
        libffi-dev \
        libglib2.0-dev \
        libpango1.0-dev \
        pkg-config \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

# Runtime dependencies used by Manim, PyAV, text rendering, and ffmpeg MP4 -> GIF conversion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-dejavu-core \
        fonts-noto-core \
        libcairo2 \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY . .

EXPOSE 8080

CMD ["sh", "-c", "TOKEN_TARGET=${GOOGLE_TOKEN_PATH:-/tmp/token.json}; TOKEN_SEED=${GOOGLE_TOKEN_SEED_PATH:-/secrets/token.json}; if [ ! -f \"$TOKEN_TARGET\" ]; then if [ -f \"$TOKEN_SEED\" ]; then mkdir -p \"$(dirname \"$TOKEN_TARGET\")\" && cp \"$TOKEN_SEED\" \"$TOKEN_TARGET\"; elif [ -f /app/token.seed.json ]; then mkdir -p \"$(dirname \"$TOKEN_TARGET\")\" && cp /app/token.seed.json \"$TOKEN_TARGET\"; fi; fi; exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
