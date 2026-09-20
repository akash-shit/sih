"""Optional local analyst brief with deterministic guardrails.

The default backend is Ollama, but a local llama.cpp GGUF path is also
supported via LLM_BACKEND="llama_cpp" and LLM_GGUF_PATH. In either case,
we keep the same guardrail behavior: only restate the supplied facts and
never invent numbers or dates.
"""
import json
import re
from pathlib import Path

import requests

from app.config import LLM_BACKEND, LLM_GGUF_PATH, OLLAMA_HOST, OLLAMA_MODEL


def _safelist_numbers(candidate_facts: dict) -> set[str]:
    return set(re.findall(r"-?\d+(?:\.\d+)?", json.dumps(candidate_facts, default=str)))


def _is_grounded_brief(text: str, candidate_facts: dict) -> bool:
    allowed = _safelist_numbers(candidate_facts)
    if any(number not in allowed for number in re.findall(r"-?\d+(?:\.\d+)?", text)):
        return False
    lowered = text.lower()
    forbidden = ("market", "company", "financial", "investor", "economic", "accuracy", "model's performance")
    if any(term in lowered for term in forbidden):
        return False
    known_terms = [str(candidate_facts.get(key, "")).replace("_", " ").lower() for key in ("change_type", "modality")]
    return any(term and term in lowered for term in known_terms)


def _generate_with_ollama(prompt: str) -> str | None:
    response = requests.post(
        f"{OLLAMA_HOST.rstrip('/')}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0, "seed": 0}},
        timeout=7,
    )
    response.raise_for_status()
    text = response.json().get("response")
    if not isinstance(text, str) or not text.strip():
        return None
    return text.strip()


def _generate_with_llama_cpp(prompt: str) -> str | None:
    try:
        from llama_cpp import Llama
    except ImportError:
        return None

    gguf_path = Path(LLM_GGUF_PATH)
    if not gguf_path.is_file():
        return None

    model = Llama(model_path=str(gguf_path), n_ctx=2048, n_gpu_layers=0)
    text = model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.0,
    )
    content = text.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


def generate_llm_brief(candidate_facts: dict) -> str | None:
    prompt = (
        "Only restate the supplied facts in hedged analyst-report prose. "
        "Never invent a date, coordinate, score, confidence, or confirmed fact. "
        'Use language such as \"The system detected...\" and \"Candidate interpretation...\". '
        "Example (placeholder only): Candidate interpretation: evidence is consistent with change on 0000-00-00.\n"
        f"FACTS:\n{json.dumps(candidate_facts, sort_keys=True, default=str)}"
    )
    try:
        if LLM_BACKEND == "llama_cpp":
            text = _generate_with_llama_cpp(prompt)
        else:
            text = _generate_with_ollama(prompt)
        if not isinstance(text, str) or not text.strip():
            return None
        if not _is_grounded_brief(text, candidate_facts):
            strict_prompt = (
                "Write one short, cautious analyst brief using only the supplied facts. "
                "Do not include any digits, dates, percentages, scores, coordinates, or other numbers. "
                "Do not mention models, markets, or facts not present in the input. "
                "Use qualitative language and state that this is a candidate interpretation.\n"
                f"FACTS:\n{json.dumps(candidate_facts, sort_keys=True, default=str)}"
            )
            text = None
            for _ in range(3):
                if LLM_BACKEND == "llama_cpp":
                    text = _generate_with_llama_cpp(strict_prompt)
                else:
                    text = _generate_with_ollama(strict_prompt)
                if isinstance(text, str) and text.strip() and _is_grounded_brief(text, candidate_facts):
                    break
            if not isinstance(text, str) or not text.strip() or not _is_grounded_brief(text, candidate_facts):
                constrained_prompt = (
                    "Return exactly one sentence and nothing else. Use this template with no digits: "
                    "Candidate interpretation: the optical evidence indicates a possible change with no clear category; analyst confirmation is required. "
                    "Do not add any other claim."
                )
                if LLM_BACKEND == "llama_cpp":
                    text = _generate_with_llama_cpp(constrained_prompt)
                else:
                    text = _generate_with_ollama(constrained_prompt)
            if not isinstance(text, str) or not text.strip() or not _is_grounded_brief(text, candidate_facts):
                return None
        return text.strip()
    except (requests.RequestException, ValueError, TypeError, KeyError, OSError, RuntimeError):
        return None
