from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class SiteConfig:
    title: str = "AutoDrive Papers"
    subtitle: str = "Daily Autonomous Driving Research Digest"
    domain: str = "adpaper.ning0713.top"
    base_path: str = "/"
    output_dir: str = "site"


@dataclass(slots=True)
class SourceConfig:
    axi_base_url: str = "https://paper.axi404.top"
    arxiv_api_url: str = "https://export.arxiv.org/api/query"
    timeout_seconds: float = 45
    retries: int = 3
    user_agent: str = "ArXivADReader/0.1 (+https://github.com/Ning0713/ArXivADReader)"


@dataclass(slots=True)
class FilterConfig:
    plugin: str = "plugins.autonomous_driving:plugin"
    llm_review_min_score: float = 10


@dataclass(slots=True)
class LlmConfig:
    enabled: bool = True
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout_seconds: float = 60

    @property
    def api_key(self) -> str:
        return os.getenv("LLM_API_KEY", "").strip()

    @property
    def effective_base_url(self) -> str:
        return (os.getenv("LLM_BASE_URL") or self.base_url).rstrip("/")

    @property
    def effective_model(self) -> str:
        return os.getenv("LLM_MODEL") or self.model

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.api_key)


@dataclass(slots=True)
class PathConfig:
    data_dir: str = "data"
    templates_dir: str = "templates"
    static_dir: str = "static"


@dataclass(slots=True)
class AppConfig:
    root: Path
    site: SiteConfig = field(default_factory=SiteConfig)
    sources: SourceConfig = field(default_factory=SourceConfig)
    filtering: FilterConfig = field(default_factory=FilterConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    paths: PathConfig = field(default_factory=PathConfig)

    @property
    def data_dir(self) -> Path:
        return (self.root / self.paths.data_dir).resolve()

    @property
    def output_dir(self) -> Path:
        return (self.root / self.site.output_dir).resolve()

    @property
    def templates_dir(self) -> Path:
        return (self.root / self.paths.templates_dir).resolve()

    @property
    def static_dir(self) -> Path:
        return (self.root / self.paths.static_dir).resolve()


def _section(cls: type, values: dict[str, Any] | None):
    allowed = cls.__dataclass_fields__.keys()
    return cls(**{key: value for key, value in (values or {}).items() if key in allowed})


def load_config(path: str | Path = "config/config.yml") -> AppConfig:
    config_path = Path(path).resolve()
    root = config_path.parent.parent if config_path.parent.name == "config" else Path.cwd()
    values: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            values = yaml.safe_load(handle) or {}
    config = AppConfig(root=root)
    config.site = _section(SiteConfig, values.get("site"))
    config.sources = _section(SourceConfig, values.get("sources"))
    config.filtering = _section(FilterConfig, values.get("filtering"))
    config.llm = _section(LlmConfig, values.get("llm"))
    config.paths = _section(PathConfig, values.get("paths"))
    if not config.site.base_path.startswith("/"):
        raise ValueError("site.base_path must start with '/'")
    return config
