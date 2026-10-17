FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
# Build-time placeholders only; real values come from the runtime environment.
RUN SECRET_KEY=build TOKEN_ENCRYPTION_KEY=VGVzdEtleVRlc3RLZXlUZXN0S2V5VGVzdEtleTEyMzQ= \
    DATABASE_URL=sqlite:///tmp/build.db \
    sh -c "python manage.py tailwind build && python manage.py collectstatic --noinput"

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
