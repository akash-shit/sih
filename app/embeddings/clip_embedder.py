"""
Stage 7 -- AI Embedding Generation

This project is explicitly configured to use a local RemoteCLIP checkpoint.
The embedding layer is a thin wrapper around open_clip so the rest of the
pipeline can remain stable, but loading a generic `openai` or other remote
OpenCLIP checkpoint is intentionally forbidden.
"""
from functools import lru_cache

import numpy as np
import torch
import open_clip
from PIL import Image

from app.config import CLIP_DEVICE, CLIP_MODEL_NAME, EMBEDDING_DIM, validate_remoteclip_config
from app.geospatial.rendering import true_color_image

_DEVICE = CLIP_DEVICE


@lru_cache(maxsize=1)
def _load_model():
    """Loaded once per process and cached -- embedding thousands of
    tiles must not reload the network each call."""
    checkpoint_path = validate_remoteclip_config()
    model, _, preprocess = open_clip.create_model_and_transforms(
        CLIP_MODEL_NAME, pretrained=None, device=_DEVICE
    )
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else None
        if not isinstance(state_dict, dict):
            raise ValueError("checkpoint must contain an OpenCLIP state dict")
        model.load_state_dict(state_dict)
    except Exception as exc:
        raise RuntimeError(
            "RemoteCLIP checkpoint could not be loaded as an OpenCLIP ViT-B-32 "
            f"state dict: {checkpoint_path}"
        ) from exc
    tokenizer = open_clip.get_tokenizer(CLIP_MODEL_NAME)
    model.eval()
    return model, preprocess, tokenizer


def _tile_to_rgb_image(tile_path: str) -> Image.Image:
    return true_color_image(tile_path)


def embed_image_tile(tile_path: str) -> np.ndarray:
    """Returns an L2-normalized (EMBEDDING_DIM,) float32 vector, ready
    to hand straight to FAISS (inner-product search == cosine
    similarity once vectors are normalized)."""
    model, preprocess, _ = _load_model()
    img = _tile_to_rgb_image(tile_path)
    tensor = preprocess(img).unsqueeze(0).to(_DEVICE)
    with torch.no_grad():
        feat = model.encode_image(tensor)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.squeeze(0).cpu().numpy().astype(np.float32)


def embed_image_tiles_batch(tile_paths: list[str], batch_size: int = 32) -> np.ndarray:
    """Same as embed_image_tile but batched -- use this for bulk
    ingestion, it is dramatically faster than a Python loop."""
    model, preprocess, _ = _load_model()
    vectors = []
    for i in range(0, len(tile_paths), batch_size):
        batch_paths = tile_paths[i:i + batch_size]
        imgs = torch.stack([preprocess(_tile_to_rgb_image(p)) for p in batch_paths]).to(_DEVICE)
        with torch.no_grad():
            feats = model.encode_image(imgs)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        vectors.append(feats.cpu().numpy().astype(np.float32))
    return np.concatenate(vectors, axis=0) if vectors else np.zeros((0, EMBEDDING_DIM), dtype=np.float32)


def embed_text(query: str) -> np.ndarray:
    """Turns a natural-language query into the same embedding space as
    the tiles -- this is what makes free-text search possible (Stage 9)."""
    model, _, tokenizer = _load_model()
    tokens = tokenizer([query]).to(_DEVICE)
    with torch.no_grad():
        feat = model.encode_text(tokens)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.squeeze(0).cpu().numpy().astype(np.float32)


def embed_texts_batch(queries: list[str]) -> np.ndarray:
    """Batched text embedding -- used by Stage 14 zero-shot change-type
    classification, which scores several candidate labels at once."""
    model, _, tokenizer = _load_model()
    tokens = tokenizer(queries).to(_DEVICE)
    with torch.no_grad():
        feats = model.encode_text(tokens)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().numpy().astype(np.float32)


def embed_uploaded_image(pil_image: Image.Image) -> np.ndarray:
    """For Stage 10 image-to-image search where the analyst uploads an
    arbitrary example image rather than picking an indexed tile."""
    model, preprocess, _ = _load_model()
    tensor = preprocess(pil_image.convert("RGB")).unsqueeze(0).to(_DEVICE)
    with torch.no_grad():
        feat = model.encode_image(tensor)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.squeeze(0).cpu().numpy().astype(np.float32)
