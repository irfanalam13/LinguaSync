# Backend API gateway image.
# IMPORTANT: build from the REPO ROOT so the root-level `shared/` package is in context:
#     docker build -f Voice_backend/Dockerfile -t linguasync-backend .
# (Render: set rootDir=., dockerfilePath=Voice_backend/Dockerfile — see render.yaml.)
FROM python:3.11-slim

WORKDIR /app

# ffmpeg is a system dependency of the pipeline (audio extract / video mux).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY Voice_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Repo-root shared/ package (imported as `from shared...`) + the backend app.
COPY shared/ ./shared/
COPY Voice_backend/ ./Voice_backend/
WORKDIR /app/Voice_backend

# Pre-create runtime dirs (also created at runtime by config.ensure_dirs()).
RUN mkdir -p artifacts uploads logs models

EXPOSE 8000
# app/__init__.py inserts parents[2] (=/app) onto sys.path so `shared` resolves.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
