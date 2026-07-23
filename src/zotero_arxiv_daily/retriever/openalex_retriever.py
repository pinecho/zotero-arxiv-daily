import requests
from .base import BaseRetriever, register_retriever
from ..protocol import Paper
from loguru import logger
from typing import Any
from datetime import date, timedelta
from time import sleep

OPENALEX_WORKS_URL = "https://api.openalex.org/works"

# Fields requested from the API. Keeping this small keeps the payload light and
# lets OpenAlex serve pages faster.
SELECT_FIELDS = ",".join(
    [
        "id",
        "doi",
        "title",
        "abstract_inverted_index",
        "authorships",
        "primary_location",
        "best_oa_location",
        "publication_date",
    ]
)


def invert_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct plain-text abstract from OpenAlex ``abstract_inverted_index``.

    OpenAlex stores abstracts as ``{word: [positions]}`` (an inverted index).
    We place every word at each of its positions and join by position order.
    Returns ``None`` when the abstract is missing so the paper can be skipped.
    """
    if not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    if not positions:
        return None
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


@register_retriever("openalex")
class OpenAlexRetriever(BaseRetriever):
    """Retrieve recently published journal/conference papers from OpenAlex.

    Unlike the arXiv/bioRxiv retrievers, this covers formally *published* works
    (not only preprints). Filtering is configurable via ``source.openalex``:

    - ``filter_type: search`` (default, "get it working" mode) matches each
      phrase in ``search`` against ``default.search`` and unions the results.
    - ``filter_type: topic`` (precise mode) filters by ``topics.id`` (OR-joined).
      OpenAlex has deprecated Concepts in favour of Topics.
    """

    def __init__(self, config):
        super().__init__(config)
        cfg = self.retriever_config
        filter_type = cfg.get("filter_type", "search")
        if filter_type not in ("search", "topic"):
            raise ValueError(
                f"source.openalex.filter_type must be 'search' or 'topic', got {filter_type!r}"
            )
        if filter_type == "search" and not cfg.get("search"):
            raise ValueError("source.openalex.search must be a non-empty list when filter_type='search'")
        if filter_type == "topic" and not cfg.get("topic_ids"):
            raise ValueError("source.openalex.topic_ids must be a non-empty list when filter_type='topic'")

    def _paginate(self, params: dict[str, Any], remaining: int) -> list[dict[str, Any]]:
        """Cursor-paginate a single OpenAlex query, honouring 429/backoff.

        Collects at most ``remaining`` works. Follows ``meta.next_cursor`` until
        it is exhausted.
        """
        per_page = min(200, max(1, remaining))
        params = {**params, "per-page": per_page, "cursor": "*", "select": SELECT_FIELDS}
        collected: list[dict[str, Any]] = []
        retry_num = 5
        delay_time = 10
        while remaining > 0:
            params["per-page"] = min(200, remaining)
            for attempt in range(retry_num):
                try:
                    response = requests.get(OPENALEX_WORKS_URL, params=params, timeout=(10, 60))
                    if response.status_code == 429:
                        raise requests.HTTPError("429 Too Many Requests", response=response)
                    response.raise_for_status()
                    break
                except Exception as e:
                    if attempt == retry_num - 1:
                        raise
                    wait = delay_time * (attempt + 1)
                    logger.warning(f"OpenAlex request failed: {e}. Retry {attempt + 1}/{retry_num} in {wait}s.")
                    sleep(wait)
            result = response.json()
            batch = result.get("results", [])
            if not batch:
                break
            collected.extend(batch)
            remaining -= len(batch)
            next_cursor = result.get("meta", {}).get("next_cursor")
            if not next_cursor:
                break
            params["cursor"] = next_cursor
            sleep(1)  # be polite to the API between pages
        return collected

    def _retrieve_raw_papers(self) -> list[dict[str, Any]]:
        cfg = self.retriever_config
        days = cfg.get("days", 2)
        from_date = (date.today() - timedelta(days=days)).isoformat()
        max_results = 10 if self.config.executor.debug else cfg.get("max_results", 200)
        mailto = cfg.get("mailto", None)

        # ``has_abstract:true`` avoids wasting the candidate budget on works
        # whose abstract we cannot rank on.
        base_filter = f"from_publication_date:{from_date},has_abstract:true"
        common: dict[str, Any] = {}
        if mailto:
            common["mailto"] = mailto

        filter_type = cfg.get("filter_type", "search")
        seen: set[str] = set()
        raw_papers: list[dict[str, Any]] = []

        if filter_type == "search":
            queries = list(cfg.get("search"))
            logger.info(f"OpenAlex search mode ({len(queries)} queries) since {from_date}")
            for query in queries:
                if len(raw_papers) >= max_results:
                    break
                params = {**common, "filter": base_filter, "search": query}
                works = self._paginate(params, max_results - len(raw_papers))
                for w in works:
                    wid = w.get("id")
                    if wid and wid not in seen:
                        seen.add(wid)
                        raw_papers.append(w)
        else:  # topic mode
            topic_ids = list(cfg.get("topic_ids"))
            topics_filter = "topics.id:" + "|".join(topic_ids)
            logger.info(f"OpenAlex topic mode ({topics_filter}) since {from_date}")
            params = {**common, "filter": f"{base_filter},{topics_filter}"}
            works = self._paginate(params, max_results)
            for w in works:
                wid = w.get("id")
                if wid and wid not in seen:
                    seen.add(wid)
                    raw_papers.append(w)

        raw_papers = raw_papers[:max_results]
        logger.info(f"OpenAlex returned {len(raw_papers)} candidate works")
        return raw_papers

    def convert_to_paper(self, raw_paper: dict[str, Any]) -> Paper | None:
        title = raw_paper.get("title")
        if not title:
            logger.debug("Skipping OpenAlex work without title")
            return None
        abstract = invert_abstract(raw_paper.get("abstract_inverted_index"))
        if not abstract:
            logger.debug(f"Skipping OpenAlex work without abstract: {title}")
            return None
        authorships = raw_paper.get("authorships", [])
        authors = [
            a["author"]["display_name"]
            for a in authorships
            if a.get("author") and a["author"].get("display_name")
        ]
        # OpenAlex ships author institutions directly, so we can fill affiliations
        # here (no LLM / full text needed). Keep unique names in author order.
        affiliations: list[str] = []
        for a in authorships:
            for inst in a.get("institutions") or []:
                name = inst.get("display_name")
                if name and name not in affiliations:
                    affiliations.append(name)
        primary = raw_paper.get("primary_location") or {}
        # Prefer the DOI (already a full https://doi.org/... URL), then the
        # landing page, then the OpenAlex work URL.
        url = raw_paper.get("doi") or primary.get("landing_page_url") or raw_paper.get("id")
        best_oa = raw_paper.get("best_oa_location") or {}
        pdf_url = best_oa.get("pdf_url")  # may be None when not open access
        venue = (primary.get("source") or {}).get("display_name")  # journal / conference name
        return Paper(
            source=self.name,
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            pdf_url=pdf_url,
            full_text=None,
            affiliations=affiliations or None,
            venue=venue,
        )
