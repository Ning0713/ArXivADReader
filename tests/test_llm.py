import json

from adpaper.config import LlmConfig
from adpaper.llm import LLMEnricher
from adpaper.models import Paper


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "relevant": True,
                                "primary_tag": "not-allowed",
                                "secondary_tags": ["量子网络"],
                            }
                        )
                    }
                }
            ]
        }


class _Client:
    request_json = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, endpoint, *, headers, json):
        self.__class__.request_json = json
        return _Response()


def test_llm_prompt_and_tag_fallback_follow_domain_plugin(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-only")
    monkeypatch.setattr("adpaper.llm.httpx.Client", _Client)
    enricher = LLMEnricher(
        LlmConfig(),
        domain_name="量子计算",
        allowed_tags=("量子算法", "量子网络"),
    )
    result = enricher.enrich(
        Paper(arxiv_id="2608.00001", title="A Quantum Research Paper"),
        borderline=True,
    )

    prompt = json.loads(_Client.request_json["messages"][1]["content"])
    assert prompt["target_domain"] == "量子计算"
    assert prompt["allowed_tags"] == ["量子算法", "量子网络"]
    assert result["tags"].primary == "量子算法"
    assert result["tags"].secondary == ["量子网络"]
