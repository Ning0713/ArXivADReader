from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field

from adpaper.config import AppConfig
from adpaper.filtering import load_plugin
from adpaper.llm import LLMEnricher
from adpaper.models import Paper
from adpaper.sources.arxiv import ArxivSource, merge_arxiv_metadata
from adpaper.sources.axi import AxiDailyResult, AxiSource
from adpaper.storage import Repository, validate_date

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UpdateReport:
    status: str
    date: str
    source_mode: str = "axi"
    candidate_count: int = 0
    selected_count: int = 0
    raw_count: int = 0
    source_url: str = ""
    warnings: list[str] = field(default_factory=list)
    changed: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class UpdatePipeline:
    def __init__(self, config: AppConfig):
        self.config = config
        self.repository = Repository(config)
        self.axi = AxiSource(config.sources)
        self.plugin = load_plugin(config.filtering.plugin)
        self.arxiv = ArxivSource(
            config.sources,
            discovery_categories=self.plugin.arxiv_categories,
        )
        self.llm = LLMEnricher(
            config.llm,
            domain_name=self.plugin.display_name,
            allowed_tags=self.plugin.tags,
        )

    def run(
        self,
        date: str,
        *,
        force: bool = False,
        allow_arxiv_discovery: bool = False,
        dry_run: bool = False,
    ) -> UpdateReport:
        validate_date(date)
        if self.repository.load_daily(date) and not force:
            return UpdateReport(status="unchanged", date=date)

        warnings: list[str] = []
        axi_result: AxiDailyResult | None = None
        source_mode = "axi"
        try:
            axi_result = self.axi.fetch_daily(date)
            candidates = axi_result.candidates
            source_url = axi_result.source_url
            raw_count = axi_result.raw_count
            source_hash = axi_result.source_hash
        except Exception as exc:  # source failure must not overwrite existing data
            if not allow_arxiv_discovery:
                return UpdateReport(status="failed", date=date, warnings=[str(exc)])
            source_mode = "arxiv-fallback"
            warnings.append(f"Axi source unavailable; explicit arXiv fallback used: {exc}")
            try:
                candidates = self.arxiv.discover_for_date(date)
            except Exception as fallback_exc:
                return UpdateReport(
                    status="failed",
                    date=date,
                    source_mode=source_mode,
                    warnings=[*warnings, str(fallback_exc)],
                )
            source_url = self.config.sources.arxiv_api_url
            raw_count = len(candidates)
            source_hash = ""

        selected = self._filter(candidates, warnings)
        arxiv_warnings = self._enrich_from_arxiv(selected)
        warnings.extend(arxiv_warnings)
        if dry_run:
            return UpdateReport(
                status="preview",
                date=date,
                source_mode=source_mode,
                candidate_count=len(candidates),
                selected_count=len(selected),
                raw_count=raw_count,
                source_url=source_url,
                warnings=warnings,
                changed=False,
            )
        for paper in selected:
            self.repository.upsert_paper(paper, date)
        manifest = self.repository.save_daily(
            date=date,
            paper_ids=[paper.arxiv_id for paper in selected],
            source_url=source_url,
            source_mode=source_mode,
            candidate_count=len(candidates),
            raw_count=raw_count,
            source_hash=source_hash,
            filter_version=getattr(self.plugin, "version", self.plugin.slug),
            warnings=warnings,
        )
        self.repository.rebuild_indexes(self.config.site.base_path)
        return UpdateReport(
            status="updated",
            date=date,
            source_mode=source_mode,
            candidate_count=len(candidates),
            selected_count=manifest["selected_count"],
            raw_count=raw_count,
            source_url=source_url,
            warnings=warnings,
            changed=True,
        )

    def ingest_candidates(
        self,
        date: str,
        candidates: list[Paper],
        *,
        source_url: str = "legacy-import",
        source_mode: str = "legacy",
        force: bool = True,
    ) -> UpdateReport:
        validate_date(date)
        if self.repository.load_daily(date) and not force:
            return UpdateReport(status="unchanged", date=date)
        warnings: list[str] = []
        selected = self._filter(candidates, warnings)
        warnings.extend(self._enrich_from_arxiv(selected))
        for paper in selected:
            self.repository.upsert_paper(paper, date)
        self.repository.save_daily(
            date=date,
            paper_ids=[paper.arxiv_id for paper in selected],
            source_url=source_url,
            source_mode=source_mode,
            candidate_count=len(candidates),
            raw_count=len(candidates),
            filter_version=getattr(self.plugin, "version", self.plugin.slug),
            warnings=warnings,
        )
        self.repository.rebuild_indexes(self.config.site.base_path)
        return UpdateReport(
            status="updated",
            date=date,
            source_mode=source_mode,
            candidate_count=len(candidates),
            selected_count=len(selected),
            raw_count=len(candidates),
            source_url=source_url,
            warnings=warnings,
            changed=True,
        )

    def _filter(self, candidates: list[Paper], warnings: list[str]) -> list[Paper]:
        selected: list[Paper] = []
        seen: set[str] = set()
        for paper in candidates:
            if paper.arxiv_id in seen:
                continue
            seen.add(paper.arxiv_id)
            decision = self.plugin.evaluate(paper)
            tags = self.plugin.assign_tags(paper)
            llm_result = None
            borderline = decision.score >= self.config.filtering.llm_review_min_score
            needs_enrichment = not paper.title_zh or not paper.abstract_zh
            should_call_llm = (borderline and not decision.include) or needs_enrichment
            if self.config.llm.available and should_call_llm:
                llm_result = self.llm.enrich(paper, borderline=borderline)
            if llm_result:
                decision.classifier = "rules+llm"
                if llm_result.get("relevant") is True:
                    decision.include = True
                    decision.reasons.append("LLM 边界复核纳入")
                if llm_result.get("title_zh") and not paper.title_zh:
                    paper.title_zh = str(llm_result["title_zh"]).strip()
                if llm_result.get("abstract_zh") and not paper.abstract_zh:
                    paper.abstract_zh = str(llm_result["abstract_zh"]).strip()
                if llm_result.get("summary_zh"):
                    paper.summary_zh = str(llm_result["summary_zh"]).strip()
                llm_tags = llm_result.get("tags")
                if llm_tags:
                    tags = llm_tags
            paper.relevance = decision
            paper.tags = tags
            if decision.include:
                selected.append(paper)
        return selected

    def _enrich_from_arxiv(self, papers: list[Paper]) -> list[str]:
        if not papers:
            return []
        try:
            metadata = self.arxiv.fetch_by_ids([paper.arxiv_id for paper in papers])
        except Exception as exc:
            logger.warning("arXiv enrichment failed: %s", exc)
            return [f"arXiv metadata enrichment failed: {exc}"]
        for paper in papers:
            arxiv_paper = metadata.get(paper.arxiv_id)
            if arxiv_paper:
                merge_arxiv_metadata(paper, arxiv_paper)
        return []
