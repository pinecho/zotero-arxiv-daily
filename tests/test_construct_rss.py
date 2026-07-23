"""Tests for zotero_arxiv_daily.construct_rss: render_feed / render_item."""

import xml.dom.minidom as minidom

from omegaconf import OmegaConf

from zotero_arxiv_daily.construct_rss import render_feed
from tests.canned_responses import make_sample_paper


def _rss_config(**overrides):
    cfg = {
        "output_path": "public/feed.xml",
        "title": "Test Feed",
        "link": "https://example.github.io/repo",
        "description": "desc",
        "language": "en",
        "self_link": None,
        "stylesheet": "rss.xsl",
    }
    cfg.update(overrides)
    return OmegaConf.create(cfg)


def test_render_feed_is_wellformed_xml():
    papers = [make_sample_paper(score=7.5, tldr="A great paper.", affiliations=["MIT"])]
    xml = render_feed(papers, _rss_config())
    # Parsing raises if the document is not well-formed.
    minidom.parseString(xml)
    assert "<item>" in xml
    assert xml.count("<item>") == 1


def test_render_feed_channel_metadata():
    xml = render_feed([], _rss_config(title="My Papers", link="https://host/x"))
    assert "<title>My Papers</title>" in xml
    assert "<link>https://host/x</link>" in xml
    # atom:self defaults to link + /feed.xml
    assert 'href="https://host/x/feed.xml" rel="self"' in xml


def test_render_feed_empty_is_valid_and_has_no_items():
    xml = render_feed([], _rss_config())
    minidom.parseString(xml)
    assert "<item>" not in xml


def test_render_feed_stylesheet_pi_present_and_absent():
    with_pi = render_feed([], _rss_config(stylesheet="rss.xsl"))
    assert "xml-stylesheet" in with_pi
    without_pi = render_feed([], _rss_config(stylesheet=None))
    assert "xml-stylesheet" not in without_pi


def test_render_feed_escapes_special_characters():
    paper = make_sample_paper(title="Speech & <health> detection", score=7.0, tldr="ok")
    xml = render_feed([paper], _rss_config())
    minidom.parseString(xml)  # must stay well-formed
    # The title (outside CDATA) must be escaped.
    assert "<title>Speech &amp; &lt;health&gt; detection</title>" in xml


def test_render_feed_item_links_to_paper_url():
    paper = make_sample_paper(
        url="https://doi.org/10.1/xyz", pdf_url=None, score=7.0, tldr="ok"
    )
    xml = render_feed([paper], _rss_config())
    assert "<link>https://doi.org/10.1/xyz</link>" in xml
    assert 'isPermaLink="true">https://doi.org/10.1/xyz</guid>' in xml


def test_render_feed_description_is_cdata_html():
    paper = make_sample_paper(score=7.3, tldr="TLDR text here", affiliations=["MIT"])
    xml = render_feed([paper], _rss_config())
    assert "<![CDATA[" in xml
    assert "TLDR text here" in xml
    assert "Sample Paper Title" in xml


def test_render_feed_strips_redundant_tldr_prefix():
    p1 = make_sample_paper(score=7.0, tldr="**TLDR:** StellarTTS is a fast model.")
    xml1 = render_feed([p1], _rss_config())
    assert "StellarTTS is a fast model." in xml1
    assert "**TLDR:**" not in xml1
    # A bold title that is not a TLDR label must be left intact.
    p2 = make_sample_paper(score=7.0, tldr="**Audio-Zero** is the first framework.")
    xml2 = render_feed([p2], _rss_config())
    assert "**Audio-Zero**" in xml2


def test_render_feed_shows_source_label():
    arxiv_paper = make_sample_paper(source="arxiv", score=7.0, tldr="ok")
    xml = render_feed([arxiv_paper], _rss_config())
    # Source is a labelled row inside the card, no emoji.
    assert "<strong>Source:</strong> arXiv (preprint)" in xml
    assert "📚" not in xml
    # No venue -> generic published label.
    openalex_paper = make_sample_paper(source="openalex", venue=None, score=7.0, tldr="ok")
    assert "<strong>Source:</strong> OpenAlex (published)" in render_feed([openalex_paper], _rss_config())


def test_render_feed_shows_openalex_venue():
    paper = make_sample_paper(source="openalex", venue="Frontiers in Digital Health", score=7.0, tldr="ok")
    xml = render_feed([paper], _rss_config())
    assert "<strong>Source:</strong> OpenAlex · Frontiers in Digital Health" in xml


def test_render_feed_source_row_after_relevance():
    paper = make_sample_paper(source="arxiv", score=7.0, tldr="ok")
    xml = render_feed([paper], _rss_config())
    # Source row must appear below the Relevance row and above the TLDR row.
    assert xml.index("Relevance:") < xml.index("Source:") < xml.index("TLDR:")
