FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SATSEARCH_CLIP_DEVICE=cpu \
    CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
    REMOTECLIP_CHECKPOINT_PATH=/app/models/RemoteCLIP-ViT-B-32.pt
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgdal-dev gdal-bin libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY backend/ ./backend/
COPY README.md PROJECT_WORKFLOW.md ./
COPY --from=frontend-build /build/frontend/dist ./frontend/dist
RUN mkdir -p /app/data /app/models
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
