from app.change import llm_brief


def test_llm_brief_connection_failure_is_safe(monkeypatch):
    def fail(*args, **kwargs):
        raise llm_brief.requests.ConnectionError("offline")
    monkeypatch.setattr(llm_brief.requests, "post", fail)
    assert llm_brief.generate_llm_brief({"combined_score": 0.4}) is None
