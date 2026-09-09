"""
Stage 14 -- Change-Type Interpretation

Refinement 3.5 from the architecture review: zero-shot text-prompt
classification is a CANDIDATE interpretation, not ground truth. We
always return a confidence alongside the label, and the caller (the
review-queue UI / evaluation report) is expected to present it as
such -- never as a certainty.

Method: embed the "after" tile once, embed each candidate label as a
short natural-language prompt, and take a softmax over the tile-to-label
cosine similarities. This is exactly CLIP's own zero-shot classification
recipe, just applied to a satellite tile instead of a photo.
"""
from dataclasses import dataclass

import numpy as np

from app.embeddings.clip_embedder import embed_image_tile, embed_texts_batch

# Prompt engineering matters more than the label word alone -- these
# phrasings are written the way CLIP's training data (natural image
# captions) would describe them, not as bare category names.
CHANGE_TYPE_PROMPTS = {
    "construction": "a satellite photo of a newly constructed building or structure",
    "vegetation_clearance": "a satellite photo of cleared or deforested land where vegetation used to be",
    "water_extent_change": "a satellite photo showing a river or water body that has expanded or receded",
    "road_development": "a satellite photo of a newly built road or paved track",
    "no_clear_category": "a satellite photo with no distinct man-made change",
}


@dataclass
class ChangeTypeResult:
    change_type: str
    confidence: float
    all_scores: dict


def classify_change_type(after_tile_path: str) -> ChangeTypeResult:
    labels = list(CHANGE_TYPE_PROMPTS.keys())
    prompts = list(CHANGE_TYPE_PROMPTS.values())

    image_vec = embed_image_tile(after_tile_path)
    text_vecs = embed_texts_batch(prompts)

    sims = text_vecs @ image_vec  # cosine similarity, vectors are pre-normalized
    # Temperature-scaled softmax, same constant (100) CLIP itself uses
    # at inference time -- sharpens the distribution over near-tied logits.
    exp = np.exp(sims * 100)
    probs = exp / exp.sum()

    all_scores = {label: float(p) for label, p in zip(labels, probs)}
    best_idx = int(np.argmax(probs))
    return ChangeTypeResult(
        change_type=labels[best_idx],
        confidence=float(probs[best_idx]),
        all_scores=all_scores,
    )
