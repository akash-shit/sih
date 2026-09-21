#!/bin/sh
set -e

echo "Downloading satellite data..."

python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Akashxo/satelliteintelligence', repo_type='dataset', local_dir='/app/data/raw')"

echo "Data downloaded successfully."

exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}
