from __future__ import annotations

import json
import re
from typing import Any

import httpx

from adpaper.config import LlmConfig
from adpaper.models import Paper, TagAssignment

JSON_RE = re.compile(r"\{[\s\S]*\}")


class LLMEnricher:
    def __init__(self, config: LlmConfig, allowed_tags: tuple[str, ...]):
        self.config = config
        self.allowed_tags = set(allowed_tags)

    def enrich(self, paper: Paper, *, borderline: bool) -> dict[str, Any] | None:
        if not self.config.available:
            return None
        prompt = {
            "task": "Classify and enrich an autonomous-driving research paper.",
            "rules": [
                "Keep high recall. Never reject an explicit autonomous-driving paper.",
                "Return JSON only, without Markdown.",
                "Use at most one primary tag and two secondary tags from the allowed list.",
            ],
            "allowed_tags": sorted(self.allowed_tags),
            "borderline_rule_review": borderline,
            "paper": {
                "id": paper.arxiv_id,
                "title": paper.title,
                "title_zh": paper.title_zh,
                "abstract": paper.abstract,
                "abstract_zh": paper.abstract_zh,
                "categories": paper.categories,
            },
            "schema": {
                "relevant": "boolean",
                "title_zh": "string",
                "abstract_zh": "string",
                "summary_zh": "string",
                "primary_tag": "string",
                "secondary_tags": "array of strings",
                "reason": "string",
            },
        }
        endpoint = f"{self.config.effective_base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json={
                        "model": self.config.effective_model,
                        "temperature": 0,
                        "messages": [
                            {"role": "system", "content": "You are a careful academic classifier."},
                            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                        ],
                    },
                )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            match = JSON_RE.search(content)
            if not match:
                return None
            value = json.loads(match.group(0))
            secondary = [tag for tag in value.get("secondary_tags", []) if tag in self.allowed_tags]
            primary = value.get("primary_tag", "")
            if primary not in self.allowed_tags:
                primary = ""
            value["tags"] = TagAssignment(
                primary=primary or "感知", secondary=secondary
            ).normalized()
            return value
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None
