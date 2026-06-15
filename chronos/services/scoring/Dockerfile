FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction

# Copy service code
COPY services/ services/
COPY ml/ ml/
COPY api/ api/
COPY infra/ infra/

# Model checkpoints mount point
VOLUME ["/app/ml/checkpoints"]

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8003

ENTRYPOINT ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8003"]
