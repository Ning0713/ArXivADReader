from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from adpaper.models import Paper, normalize_arxiv_id
from adpaper.pipeline import UpdatePipeline
from adpaper.storage import atomic_write_json

DATE_IN_NAME_RE = re.compile(r"(?:papers_)?(20\d{2})(\d{2})(\d{2})")
DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")


@dataclass(slots=True)
class MigrationReport:
    root: str
    dates_seen: list[str] = field(default_factory=list)
    dates_updated: list[str] = field(default_factory=list)
    dates_fallback: list[str] = field(default_factory=list)
    candidates_imported: int = 0
    warnings: list[str] = field(default_factory=list)


def _date_from_name(name: str) -> str | None:
    match = DATE_IN_NAME_RE.search(name)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else None


def _date_from_text(text: str) -> str | None:
    match = DATE_RE.search(text)
    return match.group(0) if match else None


def _raw_paper(value: dict[str, object]) -> Paper | None:
    raw_id = value.get("Id") or value.get("id") or value.get("arxiv_id")
    if not raw_id:
        return None
    try:
        arxiv_id = normalize_arxiv_id(str(raw_id))
    except ValueError:
        return None
    authors = value.get("Authors") or value.get("authors") or ""
    return Paper(
        arxiv_id=arxiv_id,
        title=str(value.get("Title") or value.get("title") or ""),
        title_zh=str(value.get("TitleZh") or value.get("title_zh") or ""),
        authors=[str(authors)] if authors else [],
        abstract=str(value.get("Abstract") or value.get("abstract") or ""),
        abstract_zh=str(value.get("AbstractZh") or value.get("abstract_zh") or ""),
        source={"legacy": "AutoClaw workspace snapshot"},
    )


def _legacy_json_candidates(root: Path) -> dict[str, list[Paper]]:
    grouped: dict[str, list[Paper]] = {}
    for path in root.rglob("papers_*.json"):
        date = _date_from_name(path.stem)
        if not date:
            continue
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(values, dict):
            values = values.get("papers", [])
        if not isinstance(values, list):
            continue
        papers = [
            paper
            for value in values
            if isinstance(value, dict) and (paper := _raw_paper(value))
        ]
        grouped.setdefault(date, []).extend(papers)
    return grouped


def _history_candidates(root: Path) -> dict[str, list[Paper]]:
    grouped: dict[str, list[Paper]] = {}
    path = root / "paper-history.json"
    if not path.exists():
        return grouped
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return grouped
    for value in payload.get("recommended_papers", []):
        if not isinstance(value, dict):
            continue
        paper = _raw_paper(value)
        date = value.get("date")
        if paper and isinstance(date, str) and DATE_RE.fullmatch(date):
            grouped.setdefault(date, []).append(paper)
    return grouped


def discover_legacy_dates(root: Path) -> list[str]:
    dates: set[str] = set()
    for path in root.rglob("papers_*"):
        date = _date_from_name(path.stem)
        if date:
            dates.add(date)
        if path.suffix.lower() == ".txt":
            try:
                date = _date_from_text(path.read_text(encoding="utf-8", errors="ignore")[:200_000])
            except OSError:
                date = None
            if date:
                dates.add(date)
    dates.update(_history_candidates(root))
    return sorted(dates)


def migrate(root: Path, pipeline: UpdatePipeline, *, refetch: bool = True) -> MigrationReport:
    root = root.resolve()
    report = MigrationReport(root="<legacy-root>")
    json_candidates = _legacy_json_candidates(root)
    history_candidates = _history_candidates(root)
    dates = discover_legacy_dates(root)
    report.dates_seen = dates
    for date in dates:
        if refetch:
            result = pipeline.run(date, force=True)
            if result.status == "updated":
                report.dates_updated.append(date)
                report.candidates_imported += result.candidate_count
                continue
            report.warnings.extend([f"{date}: {warning}" for warning in result.warnings])

        candidates = json_candidates.get(date) or history_candidates.get(date, [])
        unique = list({paper.arxiv_id: paper for paper in candidates}.values())
        if not unique:
            report.warnings.append(f"{date}: no structured legacy candidates available")
            continue
        result = pipeline.ingest_candidates(
            date,
            unique,
            source_url="legacy-import",
            source_mode="legacy",
            force=True,
        )
        report.dates_fallback.append(date)
        report.candidates_imported += result.candidate_count
        report.warnings.extend([f"{date}: {warning}" for warning in result.warnings])

    report_path = pipeline.repository.data_dir / "migration-report.json"
    atomic_write_json(report_path, asdict(report))
    return report
