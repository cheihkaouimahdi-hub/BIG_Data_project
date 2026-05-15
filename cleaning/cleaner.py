"""
Data Cleaner — normalises, deduplicates, and validates raw arXiv data.
"""

import json
from pathlib import Path

from loguru import logger

from extraction.arxiv_extractor import map_category_to_subject


def load_raw(path: str) -> list[dict]:
    """Load raw JSON articles from disk."""
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    logger.info(f"📂 Loaded {len(data)} raw articles from {path}")
    return data


def normalize_author_name(name: str) -> str:
    """Strip whitespace and convert to title case."""
    return name.strip().title()


def clean_articles(raw: list[dict]) -> list[dict]:
    """Clean, validate, and enrich raw article dicts.

    Steps
    -----
    1. Remove articles with missing title or empty authors
    2. Deduplicate by arxiv_id
    3. Normalise author names
    4. Convert year to int; reject years outside [1990, 2025]
    5. Map category codes → readable subject names
    6. Truncate abstract to 1000 characters
    """
    total_raw = len(raw)

    # Step 1 — Remove invalid entries
    valid = [
        a
        for a in raw
        if a.get("title", "").strip() and a.get("authors")
    ]
    removed_invalid = total_raw - len(valid)

    # Step 2 — Deduplicate by arxiv_id
    seen: set[str] = set()
    deduped: list[dict] = []
    for article in valid:
        aid = article.get("arxiv_id", "")
        if aid and aid not in seen:
            seen.add(aid)
            deduped.append(article)
    removed_dupes = len(valid) - len(deduped)

    # Steps 3–6 — Normalise and enrich
    cleaned: list[dict] = []
    for article in deduped:
        try:
            year = int(article.get("year", 0))
        except (ValueError, TypeError):
            year = 0

        if year < 1990 or year > 2030:
            continue

        # Normalise authors
        authors = [normalize_author_name(a) for a in article["authors"] if a.strip()]
        if not authors:
            continue

        # Map categories → subjects
        categories = article.get("categories", [])
        subjects = list(
            dict.fromkeys(  # preserves order, removes duplicates
                map_category_to_subject(c) for c in categories
            )
        )

        cleaned.append(
            {
                "arxiv_id": article["arxiv_id"],
                "title": article["title"].strip(),
                "abstract": article.get("abstract", "")[:1000],
                "authors": authors,
                "published": article.get("published", ""),
                "year": year,
                "categories": categories,
                "subjects": subjects,
                "url": article.get("url", ""),
            }
        )

    removed_year = len(deduped) - len(cleaned)

    logger.info(
        f"🧹 Cleaning stats:\n"
        f"   Total raw:           {total_raw}\n"
        f"   Invalid removed:     {removed_invalid}\n"
        f"   Duplicates removed:  {removed_dupes}\n"
        f"   Bad year removed:    {removed_year}\n"
        f"   ─────────────────────\n"
        f"   Total clean:         {len(cleaned)}"
    )
    return cleaned


def save_clean(data: list[dict], path: str) -> None:
    """Persist cleaned articles as JSON."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    logger.info(f"💾 Saved {len(data)} clean articles → {out}")
