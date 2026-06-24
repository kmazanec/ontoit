FROM python:3.12-slim

WORKDIR /app

# System deps: pymupdf and pdfplumber wheels are self-contained, so no extra
# apt packages are needed for the slim image.

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
COPY assets ./assets

EXPOSE 8000

# Render and most free hosts set $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
