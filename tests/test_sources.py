from pathlib import Path

from adpaper.config import SourceConfig
from adpaper.models import normalize_arxiv_id
from adpaper.sources.arxiv import ArxivSource
from adpaper.sources.axi import AxiSource

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_arxiv_id_variants():
    assert normalize_arxiv_id("https://arxiv.org/abs/2608.00001v2") == "2608.00001"
    assert normalize_arxiv_id("arXiv:hep-th/9901001v1") == "hep-th/9901001"


def test_axi_parser_deduplicates_and_extracts_fields():
    result = AxiSource(SourceConfig()).parse_daily_html(
        (FIXTURES / "axi_daily.html").read_text(encoding="utf-8"),
        url="https://paper.axi404.top/daily/2026-08-10",
        expected_date="2026-08-10",
    )
    assert result.raw_count == 3
    assert len(result.candidates) == 2
    paper = result.candidates[0]
    assert paper.arxiv_id == "2608.00001"
    assert paper.title_zh.startswith("面向自动驾驶")
    assert paper.translation_url.endswith("2608.00001")
    assert "cs.CV" in paper.categories


def test_arxiv_atom_parser():
    papers = ArxivSource(SourceConfig()).parse_feed(
        (FIXTURES / "arxiv_feed.xml").read_text(encoding="utf-8")
    )
    assert len(papers) == 1
    assert papers[0].arxiv_id == "2608.00001"
    assert papers[0].authors == ["Jane Doe", "Alex Smith"]
    assert papers[0].pdf_url.endswith("2608.00001v2")


def test_arxiv_discovery_uses_plugin_categories(monkeypatch):
    source = ArxivSource(
        SourceConfig(),
        discovery_categories=("quant-ph", "physics.optics"),
    )
    captured: dict[str, str] = {}

    def fake_get(params: dict[str, str]) -> str:
        captured.update(params)
        return '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'

    monkeypatch.setattr(source, "_get", fake_get)
    assert source.discover_for_date("2026-08-12") == []
    assert "cat:quant-ph OR cat:physics.optics" in captured["search_query"]
