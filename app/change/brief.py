"""Per-AOI calibration narratives and optional local Ollama brief."""
import json, os
from urllib.request import Request, urlopen

def aoi_narrative(aoi_name: str, candidates: list[dict]) -> str:
    if not candidates:
        return f"No supported changes were detected for {aoi_name}."
    top = sorted(candidates, key=lambda x: x.get("priority_score", x.get("combined_score", 0) or 0), reverse=True)[:3]
    items = "; ".join(f"{x.get('change_type') or 'change'} ({float(x.get('combined_score', 0) or 0):.2f})" for x in top)
    return f"{aoi_name}: {len(candidates)} supported change(s). Highest-priority findings: {items}."

def ollama_brief(prompt: str, *, model: str | None = None, endpoint: str | None = None, timeout: float = 5) -> str | None:
    if os.getenv("SI_ENABLE_OLLAMA", "").lower() not in {"1", "true", "yes"}:
        return None
    payload = json.dumps({"model": model or os.getenv("OLLAMA_MODEL", "llama3.2"), "prompt": prompt, "stream": False}).encode()
    try:
        req = Request(endpoint or os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"), data=payload,
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode()).get("response")
    except Exception:
        return None
