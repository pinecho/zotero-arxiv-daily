from .protocol import Paper
from .construct_email import get_block_html
from omegaconf import DictConfig
from email.utils import format_datetime
from xml.sax.saxutils import escape
from datetime import datetime, timezone
import re

# Some models echo a "TLDR:" / "**TL;DR:**" label at the start of their output;
# the card already labels the field, so strip a leading one to avoid duplication.
# A colon is required so genuine text that merely starts with "TLDR" is left alone.
_TLDR_PREFIX_RE = re.compile(r'^\s*\**\s*TL;?DR\s*:\s*\**\s*', re.IGNORECASE)


def _clean_tldr(text: str) -> str:
    return _TLDR_PREFIX_RE.sub('', text) if text else text


def _format_authors(authors: list[str]) -> str:
    """Same truncation rule as the e-mail renderer: show ends, elide the middle."""
    author_list = list(authors)
    if len(author_list) <= 5:
        return ', '.join(author_list)
    return ', '.join(author_list[:3] + ['...'] + author_list[-2:])


def _format_affiliations(affiliations: list[str] | None) -> str:
    if not affiliations:
        return 'Unknown Affiliation'
    shown = ', '.join(affiliations[:5])
    if len(affiliations) > 5:
        shown += ', ...'
    return shown


# Human-readable source labels shown on each item so readers can tell a
# published journal paper from a preprint at a glance.
SOURCE_LABELS = {
    "arxiv": "arXiv (preprint)",
    "openalex": "OpenAlex (journal / published)",
    "biorxiv": "bioRxiv (preprint)",
    "medrxiv": "medRxiv (preprint)",
}


def _source_badge(source: str) -> str:
    label = SOURCE_LABELS.get(source, source)
    return (
        f'<div style="font-family: Arial, sans-serif; font-size: 13px; '
        f'color: #888; margin: 0 0 6px 2px;">📚 Source: {label}</div>'
    )


def render_item(paper: Paper, build_date: str) -> str:
    """Render a single ``Paper`` as an RSS ``<item>``.

    The HTML card produced by :func:`construct_email.get_block_html` is reused
    verbatim as the item description (wrapped in CDATA). The item links to the
    landing page / DOI (``paper.url``); the card's button falls back to that URL
    when no open-access PDF is available.
    """
    rate = round(paper.score, 1) if paper.score is not None else 'Unknown'
    authors = _format_authors(paper.authors)
    affiliations = _format_affiliations(paper.affiliations)
    link_url = paper.pdf_url or paper.url
    tldr = _clean_tldr(paper.tldr or paper.abstract or '')
    description_html = _source_badge(paper.source) + get_block_html(
        paper.title, authors, rate, tldr, link_url, affiliations
    )
    guid = paper.url or link_url
    is_permalink = "true" if guid.startswith("http") else "false"
    return (
        "    <item>\n"
        f"      <title>{escape(paper.title)}</title>\n"
        f"      <link>{escape(paper.url or link_url)}</link>\n"
        f"      <guid isPermaLink=\"{is_permalink}\">{escape(guid)}</guid>\n"
        f"      <category>{escape(paper.source)}</category>\n"
        f"      <pubDate>{build_date}</pubDate>\n"
        f"      <description><![CDATA[{description_html}]]></description>\n"
        "    </item>"
    )


def render_feed(papers: list[Paper], rss_config: DictConfig) -> str:
    """Render the ranked papers as an RSS 2.0 feed document.

    An empty ``papers`` list produces a valid, item-less channel so the feed can
    always be published (GitHub Pages needs a file, and RSS readers handle an
    empty channel gracefully).
    """
    title = rss_config.get("title", "Zotero-arXiv-Daily")
    link = rss_config.get("link", "")
    description = rss_config.get("description", "Daily paper recommendations based on your Zotero library.")
    language = rss_config.get("language", "en")
    self_link = rss_config.get("self_link", "") or (link.rstrip("/") + "/feed.xml" if link else "")
    stylesheet = rss_config.get("stylesheet", None)

    build_date = format_datetime(datetime.now(timezone.utc))
    items = "\n".join(render_item(p, build_date) for p in papers)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    if stylesheet:
        lines.append(f'<?xml-stylesheet type="text/xsl" href="{escape(stylesheet, {chr(34): "&quot;"})}"?>')
    lines.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    lines.append('  <channel>')
    lines.append(f'    <title>{escape(title)}</title>')
    lines.append(f'    <link>{escape(link)}</link>')
    lines.append(f'    <description>{escape(description)}</description>')
    lines.append(f'    <language>{escape(language)}</language>')
    lines.append(f'    <lastBuildDate>{build_date}</lastBuildDate>')
    lines.append('    <generator>zotero-arxiv-daily</generator>')
    if self_link:
        lines.append(f'    <atom:link href="{escape(self_link)}" rel="self" type="application/rss+xml"/>')
    if items:
        lines.append(items)
    lines.append('  </channel>')
    lines.append('</rss>')
    return "\n".join(lines) + "\n"
