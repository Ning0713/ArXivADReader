from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

ARXIV_ID_RE = re.compile(
    r"(?i)(?:arxiv:|https?://arxiv\.org/(?:abs|pdf)/)?"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z][a-z0-9.-]*/\d{7}))"
    r"(?:v\d+)?(?:\.pdf)?"
)


def normalize_arxiv_id(value: str) -> str:
    """Return a canonical arXiv identifier without URL, version, or PDF suffix."""
    match = ARXIV_ID_RE.search((value or "").strip())
    if not match:
        raise ValueError(f"Invalid arXiv identifier: {value!r}")
    return match.group("id")


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def paper_anchor_id(arxiv_id: str) -> str:
    return "paper-" + re.sub(r"[^A-Za-z0-9_-]+", "-", normalize_arxiv_id(arxiv_id)).strip("-")


@dataclass(slots=True)
class TagAssignment:
    primary: str = "未分类"
    secondary: list[str] = field(default_factory=list)

    def normalized(self) -> TagAssignment:
        primary = normalize_space(self.primary) or "未分类"
        seen = {primary}
        secondary: list[str] = []
        for tag in self.secondary:
            tag = normalize_space(tag)
            if tag and tag not in seen:
                seen.add(tag)
                secondary.append(tag)
            if len(secondary) == 2:
                break
        return TagAssignment(primary=primary, secondary=secondary)

    @property
    def all(self) -> list[str]:
        normalized = self.normalized()
        return [normalized.primary, *normalized.secondary]


@dataclass(slots=True)
class RelevanceResult:
    include: bool
    score: float
    matched_terms: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    classifier: str = "rules"


@dataclass(slots=True)
class Paper:
    arxiv_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    title_zh: str = ""
    abstract_zh: str = ""
    categories: list[str] = field(default_factory=list)
    published_at: str = ""
    arxiv_url: str = ""
    pdf_url: str = ""
    axi_url: str = ""
    translation_url: str = ""
    summary_zh: str = ""
    tags: TagAssignment = field(default_factory=TagAssignment)
    relevance: RelevanceResult = field(
        default_factory=lambda: RelevanceResult(include=False, score=0)
    )
    source: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = ""
    seen_dates: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.arxiv_id = normalize_arxiv_id(self.arxiv_id)
        self.title = normalize_space(self.title)
        self.title_zh = normalize_space(self.title_zh)
        self.abstract = normalize_space(self.abstract)
        self.abstract_zh = normalize_space(self.abstract_zh)
        self.authors = [
            normalize_space(author) for author in self.authors if normalize_space(author)
        ]
        self.categories = list(
            dict.fromkeys(normalize_space(cat) for cat in self.categories if cat)
        )
        self.tags = self.tags.normalized()
        self.seen_dates = sorted(set(self.seen_dates))
        if not self.arxiv_url:
            self.arxiv_url = f"https://arxiv.org/abs/{self.arxiv_id}"
        if not self.pdf_url:
            self.pdf_url = f"https://arxiv.org/pdf/{self.arxiv_id}.pdf"

    @property
    def all_tags(self) -> list[str]:
        return self.tags.all

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Paper:
        payload = dict(data)
        tags = payload.get("tags") or {}
        relevance = payload.get("relevance") or {}
        payload["tags"] = tags if isinstance(tags, TagAssignment) else TagAssignment(**tags)
        payload["relevance"] = (
            relevance
            if isinstance(relevance, RelevanceResult)
            else RelevanceResult(**relevance)
        )
        return cls(**payload)
