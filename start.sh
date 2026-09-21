#!/bin/sh
set -e

echo "Starting backend..."

python -c "
from huggingface_hub import snapshot_download
import os

print('Downloading processed satellite data...')
snapshot_download(
    repo_id='Akashxo/satelliteintelligence',
    repo_type='dataset',
    allow_patterns='processed/**',
    local_dir='/app/data'
)
print('Processed satellite data ready!')
" &

exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}
