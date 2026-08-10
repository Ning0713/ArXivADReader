from __future__ import annotations

import json

from adpaper.storage import Repository


def validate_repository(repository: Repository) -> list[str]:
    errors: list[str] = []
    seen_global: set[str] = set()
    for date in repository.dates():
        manifest = repository.load_daily(date)
        if not manifest:
            errors.append(f"missing manifest: {date}")
            continue
        ids = manifest.get("paper_ids", [])
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate paper ID in daily manifest: {date}")
        for arxiv_id in ids:
            if not repository.paper_path(arxiv_id).exists():
                errors.append(f"{date} references missing paper: {arxiv_id}")
            paper = repository.load_paper(arxiv_id)
            if not paper:
                continue
            if not paper.title:
                errors.append(f"paper has empty title: {arxiv_id}")
            if len(paper.tags.secondary) > 2:
                errors.append(f"paper has too many secondary tags: {arxiv_id}")
            seen_global.add(arxiv_id)
    if repository.index_path.exists():
        try:
            index = json.loads(repository.index_path.read_text(encoding="utf-8"))
            if index.get("total_papers") != len(seen_global):
                errors.append("index total_papers does not match daily manifests")
        except json.JSONDecodeError:
            errors.append("index.json is invalid JSON")
    return errors

