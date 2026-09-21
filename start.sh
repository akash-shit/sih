#!/bin/sh
set -e

echo "Starting backend..."

uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000} &
SERVER_PID=$!

echo "Downloading satellite data from Hugging Face in background..."

python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Akashxo/satelliteintelligence', repo_type='dataset', local_dir='/app/data/raw')" > /tmp/hf-download.log 2>&1 &

wait $SERVER_PID
