from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from adpaper.config import SourceConfig
from adpaper.models import Paper, normalize_arxiv_id, normalize_space

DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
CATEGORY_RE = re.compile(r"\b(?:cs|eess|stat)\.[A-Z]{2}\b")


@dataclass(slots=True)
class AxiDailyResult:
    date: str
    source_url: str
    source_hash: str
    candidates: list[Paper]
    raw_count: int


class AxiSource:
    def __init__(self, config: SourceConfig):
        self.config = config

    def fetch_daily(self, date: str) -> AxiDailyResult:
        datetime.strptime(date, "%Y-%m-%d")
        url = f"{self.config.axi_base_url.rstrip('/')}/daily/{date}"
        last_error: Exception | None = None
        for attempt in range(1, self.config.retries + 1):
            try:
                with httpx.Client(
                    timeout=self.config.timeout_seconds,
                    follow_redirects=True,
                    headers={"User-Agent": self.config.user_agent},
                ) as client:
                    response = client.get(url)
                    response.raise_for_status()
                return self.parse_daily_html(response.text, url=url, expected_date=date)
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.config.retries:
                    time.sleep(min(2 ** (attempt - 1), 8))
        raise RuntimeError(f"Unable to fetch Axi daily page {url}: {last_error}")

    def parse_daily_html(
        self,
        html: str,
        *,
        url: str,
        expected_date: str | None = None,
    ) -> AxiDailyResult:
        soup = BeautifulSoup(html, "html.parser")
        paper_nodes = soup.select(".paper[data-arxiv-id]")
        if not paper_nodes:
            raise ValueError("Axi page does not contain paper nodes")

        page_date = self._page_date(soup) or expected_date or ""
        if expected_date and page_date and expected_date != page_date:
            raise ValueError(f"Axi returned date {page_date}, expected {expected_date}")

        candidates: list[Paper] = []
        seen: set[str] = set()
        for node in paper_nodes:
            raw_id = node.get("data-arxiv-id", "")
            try:
                arxiv_id = normalize_arxiv_id(str(raw_id))
            except ValueError:
                continue
            if arxiv_id in seen:
                continue
            seen.add(arxiv_id)

            arxiv_link = self._link(node, "link-arxiv", "arxiv.org/abs")
            pdf_link = self._link(node, "link-pdf", "arxiv.org/pdf")
            translation_link = self._link(node, "link-hjfy", "hjfy")
            paper = Paper(
                arxiv_id=arxiv_id,
                title=self._text(node, ".paper-title"),
                title_zh=self._text(node, ".paper-title-zh"),
                authors=self._authors(node),
                abstract=self._text(node, ".abstract-en"),
                abstract_zh=self._text(node, ".abstract-zh"),
                categories=self._categories(node),
                arxiv_url=urljoin(url, arxiv_link) if arxiv_link else "",
                pdf_url=urljoin(url, pdf_link) if pdf_link else "",
                axi_url=f"{url}#paper-{arxiv_id.replace('.', '-')}",
                translation_url=urljoin(url, translation_link) if translation_link else "",
                source={"axi": url},
                fetched_at=datetime.now(UTC).isoformat(),
            )
            if paper.title:
                candidates.append(paper)

        if not candidates:
            raise ValueError("Axi page contained no valid paper records")
        return AxiDailyResult(
            date=page_date,
            source_url=url,
            source_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
            candidates=candidates,
            raw_count=len(paper_nodes),
        )

    @staticmethod
    def _text(node: Tag, selector: str) -> str:
        child = node.select_one(selector)
        return normalize_space(child.get_text(" ", strip=True) if child else "")

    @classmethod
    def _authors(cls, node: Tag) -> list[str]:
        text = cls._text(node, ".paper-authors")
        return [text] if text else []

    @classmethod
    def _categories(cls, node: Tag) -> list[str]:
        values: list[str] = []
        category_text = cls._text(node, ".paper-categories")
        number_text = cls._text(node, ".paper-number")
        button = node.select_one("[data-paper-category]")
        button_value = button.get("data-paper-category", "") if button else ""
        for source in (category_text, number_text, str(button_value)):
            values.extend(CATEGORY_RE.findall(source))
        return list(dict.fromkeys(values))

    @staticmethod
    def _link(node: Tag, class_name: str, href_fragment: str) -> str:
        link = node.select_one(f"a.{class_name}") or node.select_one(f'a[href*="{href_fragment}"]')
        return str(link.get("href", "")) if link else ""

    @staticmethod
    def _page_date(soup: BeautifulSoup) -> str:
        date_node = soup.select_one(".header-date")
        if date_node:
            match = DATE_RE.search(date_node.get_text(" ", strip=True))
            if match:
                return match.group(0)
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        match = DATE_RE.search(title)
        return match.group(0) if match else ""

