"""Tests for OpenAlexRetriever."""

import pytest
from omegaconf import open_dict

from zotero_arxiv_daily.retriever.openalex_retriever import OpenAlexRetriever, invert_abstract
from tests.canned_responses import SAMPLE_OPENALEX_API_RESPONSE


def _set_openalex(config, **overrides):
    cfg = {
        "filter_type": "search",
        "search": ["speech health detection"],
        "topic_ids": None,
        "days": 2,
        "max_results": 200,
        "mailto": None,
    }
    cfg.update(overrides)
    with open_dict(config.source):
        config.source.openalex = cfg


def test_invert_abstract_reconstructs_order():
    idx = {"world": [1], "hello": [0], "again": [2]}
    assert invert_abstract(idx) == "hello world again"


def test_invert_abstract_handles_missing():
    assert invert_abstract(None) is None
    assert invert_abstract({}) is None


def test_openalex_retrieve_search(config, mock_openalex_api, monkeypatch):
    monkeypatch.setattr("zotero_arxiv_daily.retriever.base.sleep", lambda _: None)
    monkeypatch.setattr("zotero_arxiv_daily.retriever.openalex_retriever.sleep", lambda _: None)
    _set_openalex(config)
    retriever = OpenAlexRetriever(config)
    papers = retriever.retrieve_papers()
    # 3 works in the fixture, but the abstract-less one is skipped -> 2 papers.
    assert len(papers) == 2
    titles = {p.title for p in papers}
    assert "An openalex paper" in titles
    assert "Abstract-less openalex paper" not in titles


def test_openalex_convert_to_paper_full(config):
    _set_openalex(config)
    retriever = OpenAlexRetriever(config)
    raw = SAMPLE_OPENALEX_API_RESPONSE["results"][0]
    paper = retriever.convert_to_paper(raw)
    assert paper is not None
    assert paper.source == "openalex"
    assert paper.title == "An openalex paper"
    assert paper.abstract == "We present a novel method"
    assert paper.authors == ["Alice Zhang", "Bob Li"]
    assert paper.url == "https://doi.org/10.1000/openalex-1"
    assert paper.pdf_url == "https://example.org/openalex-1.pdf"
    assert paper.full_text is None


def test_openalex_convert_skips_missing_abstract(config):
    _set_openalex(config)
    retriever = OpenAlexRetriever(config)
    raw = SAMPLE_OPENALEX_API_RESPONSE["results"][1]  # abstract_inverted_index is None
    assert retriever.convert_to_paper(raw) is None


def test_openalex_convert_url_fallback_no_doi(config):
    _set_openalex(config)
    retriever = OpenAlexRetriever(config)
    raw = SAMPLE_OPENALEX_API_RESPONSE["results"][2]  # no DOI, no OA PDF
    paper = retriever.convert_to_paper(raw)
    assert paper.url == "https://example.org/openalex-3"  # landing page fallback
    assert paper.pdf_url is None


def test_openalex_debug_limits_results(config, mock_openalex_api, monkeypatch):
    monkeypatch.setattr("zotero_arxiv_daily.retriever.base.sleep", lambda _: None)
    monkeypatch.setattr("zotero_arxiv_daily.retriever.openalex_retriever.sleep", lambda _: None)
    _set_openalex(config)
    with open_dict(config):
        config.executor.debug = True
    retriever = OpenAlexRetriever(config)
    raw = retriever._retrieve_raw_papers()
    assert len(raw) <= 10


def test_openalex_search_requires_search_list(config):
    _set_openalex(config, filter_type="search", search=None)
    with pytest.raises(ValueError, match="search must be a non-empty list"):
        OpenAlexRetriever(config)


def test_openalex_topic_requires_topic_ids(config):
    _set_openalex(config, filter_type="topic", topic_ids=None)
    with pytest.raises(ValueError, match="topic_ids must be a non-empty list"):
        OpenAlexRetriever(config)


def test_openalex_invalid_filter_type(config):
    _set_openalex(config, filter_type="bogus")
    with pytest.raises(ValueError, match="filter_type must be"):
        OpenAlexRetriever(config)
