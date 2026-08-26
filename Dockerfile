FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

COPY --chown=app:app . .
RUN mkdir -p /app/logs && chown -R app:app /app

USER app

CMD ["python", "main.py"]
