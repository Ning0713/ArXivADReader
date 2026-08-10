from __future__ import annotations

import json
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from adpaper.config import AppConfig
from adpaper.filtering import load_plugin
from adpaper.models import Paper, paper_anchor_id
from adpaper.storage import Repository


class SiteBuilder:
    def __init__(self, config: AppConfig):
        self.config = config
        self.repository = Repository(config)
        self.plugin = load_plugin(config.filtering.plugin)
        self.environment = Environment(
            loader=FileSystemLoader(config.templates_dir),
            autoescape=select_autoescape(("html", "xml")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.environment.globals.update(url=self.url, paper_anchor=self.paper_anchor)

    def url(self, path: str = "") -> str:
        base = self.config.site.base_path.rstrip("/")
        suffix = path.lstrip("/")
        return f"{base}/{suffix}" if suffix else f"{base}/"

    @staticmethod
    def paper_anchor(arxiv_id: str) -> str:
        return paper_anchor_id(arxiv_id)

    def build(self) -> Path:
        self.repository.rebuild_indexes(self.config.site.base_path)
        index = json.loads(self.repository.index_path.read_text(encoding="utf-8"))
        output = self.config.output_dir
        self._prepare_output(output)
        assets = output / "assets"
        shutil.copytree(self.config.static_dir, assets, dirs_exist_ok=True)
        shutil.copy2(self.repository.search_index_path, assets / "search-index.json")
        (output / "CNAME").write_text(self.config.site.domain + "\n", encoding="ascii")
        (output / ".nojekyll").write_text("", encoding="ascii")

        index_html = self.environment.get_template("index.html.j2").render(
            site=self.config.site,
            index=index,
        )
        (output / "index.html").write_text(index_html, encoding="utf-8")

        for date in self.repository.dates():
            manifest = self.repository.load_daily(date)
            if not manifest:
                continue
            papers = [
                paper
                for arxiv_id in manifest.get("paper_ids", [])
                if (paper := self.repository.load_paper(arxiv_id)) is not None
            ]
            groups = self._groups(papers)
            page_dir = output / "daily" / date
            page_dir.mkdir(parents=True, exist_ok=True)
            html = self.environment.get_template("daily.html.j2").render(
                site=self.config.site,
                index=index,
                manifest=manifest,
                papers=papers,
                groups=groups,
                translated_count=sum(bool(paper.title_zh or paper.abstract_zh) for paper in papers),
            )
            (page_dir / "index.html").write_text(html, encoding="utf-8")
        return output

    def _groups(self, papers: list[Paper]) -> list[dict[str, Any]]:
        grouped: OrderedDict[str, list[Paper]] = OrderedDict((tag, []) for tag in self.plugin.tags)
        for paper in papers:
            grouped.setdefault(paper.tags.primary, []).append(paper)
        return [
            {"name": name, "id": f"category-{index}", "papers": values}
            for index, (name, values) in enumerate(grouped.items())
            if values
        ]

    def _prepare_output(self, output: Path) -> None:
        root = self.config.root.resolve()
        resolved = output.resolve()
        if resolved == root or root not in resolved.parents:
            raise ValueError(f"Refusing to build outside project root: {resolved}")
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)
