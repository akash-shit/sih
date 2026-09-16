"""Optional local Ollama analyst brief with deterministic guardrails."""
import json
import re
import requests
from app.config import OLLAMA_HOST, OLLAMA_MODEL


def generate_llm_brief(candidate_facts: dict) -> str | None:
    prompt = (
        "Only restate the supplied facts in hedged analyst-report prose. "
        "Never invent a date, coordinate, score, confidence, or confirmed fact. "
        'Use language such as \"The system detected...\" and \"Candidate interpretation...\". '
        "Example (placeholder only): Candidate interpretation: evidence is consistent with change on 0000-00-00.\n"
        f"FACTS:\n{json.dumps(candidate_facts, sort_keys=True, default=str)}"
    )
    try:
        response = requests.post(f"{OLLAMA_HOST.rstrip('/')}/api/generate", json={
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        }, timeout=7)
        response.raise_for_status()
        text = response.json().get("response")
        if not isinstance(text, str) or not text.strip():
            return None
        allowed = set(re.findall(r"-?\d+(?:\.\d+)?", json.dumps(candidate_facts, default=str)))
        if any(number not in allowed for number in re.findall(r"-?\d+(?:\.\d+)?", text)):
            return None
        return text.strip()
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return None
