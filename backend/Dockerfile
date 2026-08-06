FROM python:3.12-slim

WORKDIR /app

# Install system deps (required by some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the data directory exists (SQLite DB lives here; mounted as a volume)
RUN mkdir -p /app/data

EXPOSE 8000

# Run with uvicorn — single worker is appropriate for SQLite
# (SQLite doesn't handle concurrent writes well, documented in report)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
