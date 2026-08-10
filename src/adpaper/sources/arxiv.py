from __future__ import annotations

import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from adpaper.config import SourceConfig
from adpaper.models import Paper, normalize_arxiv_id, normalize_space

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


class ArxivSource:
    def __init__(self, config: SourceConfig):
        self.config = config

    def fetch_by_ids(self, ids: list[str], batch_size: int = 50) -> dict[str, Paper]:
        canonical = list(dict.fromkeys(normalize_arxiv_id(value) for value in ids))
        papers: dict[str, Paper] = {}
        for offset in range(0, len(canonical), batch_size):
            batch = canonical[offset : offset + batch_size]
            params = {"id_list": ",".join(batch), "max_results": str(len(batch))}
            xml = self._get(params)
            for paper in self.parse_feed(xml):
                papers[paper.arxiv_id] = paper
            if offset + batch_size < len(canonical):
                time.sleep(3)
        return papers

    def discover_for_date(self, date: str, max_results: int = 2000) -> list[Paper]:
        parsed = datetime.strptime(date, "%Y-%m-%d")
        day = parsed.strftime("%Y%m%d")
        query = (
            "(cat:cs.CV OR cat:cs.RO OR cat:cs.AI OR cat:cs.LG) "
            f"AND submittedDate:[{day}0000 TO {day}2359]"
        )
        params = {
            "search_query": query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        return self.parse_feed(self._get(params))

    def _get(self, params: dict[str, str]) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.config.retries + 1):
            try:
                with httpx.Client(
                    timeout=self.config.timeout_seconds,
                    follow_redirects=True,
                    headers={"User-Agent": self.config.user_agent},
                ) as client:
                    response = client.get(self.config.arxiv_api_url, params=params)
                    response.raise_for_status()
                    return response.text
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self.config.retries:
                    time.sleep(min(3 * attempt, 9))
        encoded = urllib.parse.urlencode(params)
        raise RuntimeError(f"Unable to fetch arXiv API ({encoded}): {last_error}")

    @staticmethod
    def parse_feed(xml: str) -> list[Paper]:
        root = ET.fromstring(xml)
        papers: list[Paper] = []
        for entry in root.findall(f"{ATOM}entry"):
            id_text = entry.findtext(f"{ATOM}id", default="")
            try:
                arxiv_id = normalize_arxiv_id(id_text)
            except ValueError:
                continue
            links = entry.findall(f"{ATOM}link")
            arxiv_url = next(
                (link.get("href", "") for link in links if link.get("rel") == "alternate"),
                "",
            )
            pdf_url = next(
                (
                    link.get("href", "")
                    for link in links
                    if link.get("title") == "pdf" or link.get("type") == "application/pdf"
                ),
                "",
            )
            authors = [
                normalize_space(author.findtext(f"{ATOM}name", default=""))
                for author in entry.findall(f"{ATOM}author")
            ]
            categories = [
                category.get("term", "")
                for category in entry.findall(f"{ATOM}category")
                if category.get("term")
            ]
            primary = entry.find(f"{ARXIV}primary_category")
            if primary is not None and primary.get("term"):
                categories.insert(0, primary.get("term", ""))
            papers.append(
                Paper(
                    arxiv_id=arxiv_id,
                    title=entry.findtext(f"{ATOM}title", default=""),
                    abstract=entry.findtext(f"{ATOM}summary", default=""),
                    authors=authors,
                    categories=list(dict.fromkeys(categories)),
                    published_at=entry.findtext(f"{ATOM}published", default=""),
                    arxiv_url=arxiv_url,
                    pdf_url=pdf_url,
                    source={"arxiv": arxiv_url or f"https://arxiv.org/abs/{arxiv_id}"},
                )
            )
        return papers


def merge_arxiv_metadata(axi: Paper, arxiv: Paper) -> Paper:
    """Keep Axi display content while filling canonical metadata from arXiv."""
    axi.title = axi.title or arxiv.title
    axi.abstract = axi.abstract or arxiv.abstract
    axi.authors = arxiv.authors or axi.authors
    axi.categories = list(dict.fromkeys([*arxiv.categories, *axi.categories]))
    axi.published_at = arxiv.published_at or axi.published_at
    axi.arxiv_url = arxiv.arxiv_url or axi.arxiv_url
    axi.pdf_url = arxiv.pdf_url or axi.pdf_url
    axi.source = {**axi.source, **arxiv.source}
    return axi

