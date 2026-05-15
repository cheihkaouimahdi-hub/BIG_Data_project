"""
arXiv API Extractor — fetches scientific publications from arXiv ONLY.
Uses the public Atom feed at http://export.arxiv.org/api/query
"""

import json
import os
import re
import time
from pathlib import Path

import feedparser
import requests
from loguru import logger
from tqdm import tqdm

import config

# ── Category → Human-readable subject mapping ────────────────────────────────
CATEGORY_MAP = {
    "cs.AI": "Artificial Intelligence",
    "cs.LG": "Machine Learning",
    "cs.CL": "Natural Language Processing",
    "cs.CV": "Computer Vision",
    "cs.NE": "Neural Networks",
    "cs.IR": "Information Retrieval",
    "cs.DB": "Databases",
    "stat.ML": "Statistical Machine Learning",
}


def map_category_to_subject(category: str) -> str:
    """Map an arXiv category code to a readable subject name."""
    return CATEGORY_MAP.get(category, "Other")


def _parse_arxiv_id(entry_id: str) -> str:
    """Extract the arXiv ID from the full Atom entry URL.

    Examples
    --------
    http://arxiv.org/abs/2301.00001v1 → 2301.00001
    """
    raw = entry_id.split("/abs/")[-1]
    # Strip version suffix (e.g. v1, v2)
    return re.sub(r"v\d+$", "", raw)


def _clean_text(text: str) -> str:
    """Remove newlines and extra whitespace from text."""
    return " ".join(text.split())


def _fetch_single_keyword(
    keyword: str,
    max_results: int,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> list[dict]:
    """Fetch articles from arXiv for one keyword with retry logic."""
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{keyword}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"[Attempt {attempt}/{max_retries}] Fetching arXiv for '{keyword}' "
                f"(max {max_results} results)…"
            )
            response = requests.get(base_url, params=params, timeout=60)
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            logger.warning(f"Network error: {exc}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay}s…")
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Failed to fetch arXiv for '{keyword}' after {max_retries} attempts."
                )
                return []

    feed = feedparser.parse(response.text)

    articles: list[dict] = []
    for entry in feed.entries:
        try:
            arxiv_id = _parse_arxiv_id(entry.id)
            title = _clean_text(entry.title)
            abstract = _clean_text(entry.summary)[:1000]
            authors = [a.get("name", "").strip() for a in entry.get("authors", [])]
            published = entry.get("published", "")
            year = int(published[:4]) if len(published) >= 4 else 0
            categories = [
                tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")
            ]
            url = entry.get("link", "")

            articles.append(
                {
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "published": published,
                    "year": year,
                    "categories": categories,
                    "url": url,
                }
            )
        except Exception as exc:
            logger.warning(f"Skipping malformed entry: {exc}")

    return articles


def fetch_arxiv(keywords: list[str], max_results: int) -> list[dict]:
    """Fetch articles from arXiv across multiple keywords, deduplicate, and save.

    Parameters
    ----------
    keywords : list[str]
        Search keywords (e.g. ["machine learning", "deep learning"]).
    max_results : int
        Maximum results to fetch per keyword.

    Returns
    -------
    list[dict]
        Deduplicated list of article dicts.
    """
    all_articles: list[dict] = []
    seen_ids: set[str] = set()

    for keyword in tqdm(keywords, desc="🔍 arXiv keywords", unit="keyword"):
        batch = _fetch_single_keyword(keyword, max_results)
        for article in batch:
            aid = article["arxiv_id"]
            if aid not in seen_ids:
                seen_ids.add(aid)
                all_articles.append(article)
        logger.info(
            f"Keyword '{keyword}': fetched {len(batch)} → "
            f"total unique so far: {len(all_articles)}"
        )
        # Be polite to arXiv servers
        time.sleep(3)

    # Persist raw data
    raw_path = Path(config.DATA_RAW_PATH)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_path, "w", encoding="utf-8") as fp:
        json.dump(all_articles, fp, ensure_ascii=False, indent=2)

    logger.info(
        f"✅ Total fetched & deduplicated: {len(all_articles)} articles → {raw_path}"
    )
    return all_articles
