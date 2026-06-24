FROM python:3.11-slim

WORKDIR /app

# ffmpeg is a system dependency of the pipeline (audio extract / video mux).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-create runtime dirs (also created at runtime by config.ensure_dirs()).
RUN mkdir -p artifacts uploads logs models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
