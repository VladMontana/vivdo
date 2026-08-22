FROM python:3.13-slim

# Установка системных зависимостей (ffmpeg необходим для yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Установка Deno (JS runtime для yt-dlp)
COPY --from=denoland/deno:bin /deno /bin/deno

# Настройка переменных окружения uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"


WORKDIR /app

# Копируем метаданные проекта и ставим зависимости (с кешированием uv)
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Копируем исходный код и устанавливаем проект
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
