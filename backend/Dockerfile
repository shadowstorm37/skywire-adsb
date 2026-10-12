FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies against a stub package first so this layer is cached
# until pyproject.toml changes. The install is editable, so the real source
# copied below is what gets imported.
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py && pip install --no-cache-dir -e .

COPY . .
