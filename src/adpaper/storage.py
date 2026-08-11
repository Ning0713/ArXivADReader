from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from adpaper.config import AppConfig
from adpaper.models import Paper, paper_anchor_id

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date(value: str) -> str:
    if not DATE_RE.fullmatch(value):
        raise ValueError(f"Date must use YYYY-MM-DD: {value!r}")
    datetime.strptime(value, "%Y-%m-%d")
    return value


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class Repository:
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = config.data_dir
        self.daily_dir = self.data_dir / "daily"
        self.papers_dir = self.data_dir / "papers"
        self.history_path = self.data_dir / "history.json"
        self.index_path = self.data_dir / "index.json"
        self.search_index_path = self.data_dir / "search-index.json"
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.papers_dir.mkdir(parents=True, exist_ok=True)

    def paper_path(self, arxiv_id: str) -> Path:
        return self.papers_dir / f"{arxiv_id.replace('/', '_')}.json"

    def load_paper(self, arxiv_id: str) -> Paper | None:
        path = self.paper_path(arxiv_id)
        if not path.exists():
            return None
        return Paper.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def upsert_paper(self, paper: Paper, date: str) -> Paper:
        validate_date(date)
        previous = self.load_paper(paper.arxiv_id)
        if previous:
            if not paper.title_zh:
                paper.title_zh = previous.title_zh
            if not paper.abstract_zh:
                paper.abstract_zh = previous.abstract_zh
            if not paper.summary_zh:
                paper.summary_zh = previous.summary_zh
            paper.seen_dates = sorted(set(previous.seen_dates + paper.seen_dates + [date]))
            paper.source = {**previous.source, **paper.source}
        else:
            paper.seen_dates = sorted(set(paper.seen_dates + [date]))
        atomic_write_json(self.paper_path(paper.arxiv_id), paper.to_dict())
        return paper

    def save_daily(
        self,
        *,
        date: str,
        paper_ids: list[str],
        source_url: str,
        source_mode: str,
        candidate_count: int,
        raw_count: int,
        source_hash: str = "",
        filter_version: str = "autonomous-driving-v1",
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        validate_date(date)
        manifest = {
            "date": date,
            "source_url": source_url,
            "source_mode": source_mode,
            "source_hash": source_hash,
            "candidate_count": candidate_count,
            "raw_count": raw_count,
            "selected_count": len(paper_ids),
            "paper_ids": list(dict.fromkeys(paper_ids)),
            "filter_version": filter_version,
            "warnings": warnings or [],
            "generated_at": datetime.now(UTC).isoformat(),
        }
        atomic_write_json(self.daily_dir / f"{date}.json", manifest)
        return manifest

    def load_daily(self, date: str) -> dict[str, Any] | None:
        validate_date(date)
        path = self.daily_dir / f"{date}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def dates(self) -> list[str]:
        values: list[str] = []
        for path in self.daily_dir.glob("*.json"):
            try:
                values.append(validate_date(path.stem))
            except ValueError:
                continue
        return sorted(set(values), reverse=True)

    def iter_daily(self) -> Iterable[dict[str, Any]]:
        for date in self.dates():
            manifest = self.load_daily(date)
            if manifest:
                yield manifest

    def rebuild_indexes(self, base_path: str = "/") -> dict[str, Any]:
        dates: list[dict[str, Any]] = []
        unique_ids: set[str] = set()
        tag_counts: dict[str, int] = {}
        search_items: list[dict[str, Any]] = []
        for manifest in self.iter_daily():
            date = manifest["date"]
            paper_ids = manifest.get("paper_ids", [])
            unique_ids.update(paper_ids)
            daily_tags: set[str] = set()
            for arxiv_id in paper_ids:
                paper = self.load_paper(arxiv_id)
                if not paper:
                    continue
                daily_tags.update(paper.all_tags)
                for tag in paper.all_tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                search_items.append(
                    {
                        "id": paper.arxiv_id,
                        "date": date,
                        "title": paper.title,
                        "title_zh": paper.title_zh,
                        "authors": paper.authors,
                        "abstract": paper.abstract,
                        "abstract_zh": paper.abstract_zh,
                        "tags": paper.all_tags,
                        "url": (
                            f"{base_path.rstrip('/')}/daily/{date}/"
                            f"#{paper_anchor_id(paper.arxiv_id)}"
                        ),
                    }
                )
            dates.append(
                {
                    "date": date,
                    "paper_count": len(paper_ids),
                    "tag_count": len(daily_tags),
                    "url": f"{base_path.rstrip('/')}/daily/{date}/",
                    "generated_at": manifest.get("generated_at", ""),
                }
            )
        generated_at = dates[0].get("generated_at", "") if dates else ""
        self._prune_orphan_papers(unique_ids)
        storage_bytes = sum(
            path.stat().st_size
            for directory in (self.daily_dir, self.papers_dir)
            for path in directory.glob("*.json")
        )
        index = {
            "generated_at": generated_at,
            "latest_date": dates[0]["date"] if dates else "",
            "total_papers": len(unique_ids),
            "total_daily_papers": sum(item["paper_count"] for item in dates),
            "total_days": len(dates),
            "storage_bytes": storage_bytes,
            "storage_mb": round(storage_bytes / (1024 * 1024), 2),
            "tag_counts": dict(sorted(tag_counts.items())),
            "dates": dates,
        }
        search_items.sort(key=lambda item: (item["date"], item["id"]), reverse=True)
        atomic_write_json(self.index_path, index)
        atomic_write_json(
            self.search_index_path,
            {"generated_at": index["generated_at"], "items": search_items},
        )
        self._rebuild_history(unique_ids, generated_at)
        return index

    def _prune_orphan_papers(self, referenced_ids: set[str]) -> None:
        for path in self.papers_dir.glob("*.json"):
            try:
                paper = Paper.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
            if paper.arxiv_id not in referenced_ids:
                path.unlink()

    def _rebuild_history(self, ids: set[str], updated_at: str) -> None:
        previous: dict[str, Any] = {}
        if self.history_path.exists():
            try:
                previous = json.loads(self.history_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                previous = {}
        papers: dict[str, Any] = {}
        for arxiv_id in sorted(ids):
            paper = self.load_paper(arxiv_id)
            if not paper:
                continue
            old = previous.get("papers", {}).get(arxiv_id, {})
            papers[arxiv_id] = {
                "title": paper.title,
                "first_seen": (
                    min(paper.seen_dates)
                    if paper.seen_dates
                    else old.get("first_seen", "")
                ),
                "dates": paper.seen_dates,
                "tags": paper.all_tags,
            }
        atomic_write_json(
            self.history_path,
            {
                "updated_at": updated_at,
                "total": len(papers),
                "papers": papers,
            },
        )
