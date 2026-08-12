from __future__ import annotations

import json
import re
from typing import Any

import httpx

from adpaper.config import LlmConfig
from adpaper.models import Paper, TagAssignment

JSON_RE = re.compile(r"\{[\s\S]*\}")


class LLMEnricher:
    def __init__(
        self,
        config: LlmConfig,
        *,
        domain_name: str,
        allowed_tags: tuple[str, ...],
    ):
        self.config = config
        self.domain_name = domain_name
        self.allowed_tags = tuple(dict.fromkeys(allowed_tags))
        if not self.allowed_tags:
            raise ValueError("The domain plugin must define at least one tag")
        self.allowed_tag_set = set(self.allowed_tags)

    def enrich(self, paper: Paper, *, borderline: bool) -> dict[str, Any] | None:
        if not self.config.available:
            return None
        prompt = {
            "task": f"Classify and enrich a research paper for the {self.domain_name} domain.",
            "target_domain": self.domain_name,
            "rules": [
                f"Keep high recall. Never reject a paper explicitly about {self.domain_name}.",
                "Return JSON only, without Markdown.",
                "Use at most one primary tag and two secondary tags from the allowed list.",
            ],
            "allowed_tags": list(self.allowed_tags),
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
            secondary = [
                tag for tag in value.get("secondary_tags", []) if tag in self.allowed_tag_set
            ]
            primary = value.get("primary_tag", "")
            if primary not in self.allowed_tag_set:
                primary = self.allowed_tags[0]
            value["tags"] = TagAssignment(primary=primary, secondary=secondary).normalized()
            return value
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None
