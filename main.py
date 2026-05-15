"""
main.py — Full ETL pipeline orchestrator.

Usage
-----
    python main.py --step all        # run everything
    python main.py --step extract    # arXiv extraction only
    python main.py --step clean      # data cleaning only
    python main.py --step load       # load into Neo4j AuraDB
    python main.py --step visualize  # generate charts
"""

import argparse
import sys

from loguru import logger

import config
from extraction.arxiv_extractor import fetch_arxiv
from cleaning.cleaner import load_raw, clean_articles, save_clean
from graph.neo4j_connector import Neo4jConnector
from graph.loader import GraphLoader
from visualization.visualizer import (
    plot_collaboration_network,
    plot_citation_network,
    plot_trending_subjects,
    plot_top_authors,
)

# ── Configure logger ──────────────────────────────────────────────────────────
logger.remove()
logger.add(sys.stderr, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyse de Publications Scientifiques — ETL Pipeline",
    )
    parser.add_argument(
        "--step",
        choices=["extract", "clean", "load", "visualize", "all"],
        default="all",
        help="Pipeline step to execute (default: all)",
    )
    args = parser.parse_args()
    step = args.step

    logger.info(f"🚀 Pipeline started — step: {step}")
    logger.info(f"   Keywords: {config.SEARCH_KEYWORDS}")
    logger.info(f"   Max results per keyword: {config.MAX_RESULTS}")

    # ── STEP 1: Extract from arXiv ────────────────────────────────────────────
    if step in ("extract", "all"):
        logger.info("═══════════ STEP 1: EXTRACTION ═══════════")
        raw_data = fetch_arxiv(config.SEARCH_KEYWORDS, config.MAX_RESULTS)
        logger.info(f"Extraction complete — {len(raw_data)} articles.")

    # ── STEP 2: Clean ─────────────────────────────────────────────────────────
    if step in ("clean", "all"):
        logger.info("═══════════ STEP 2: CLEANING ═══════════")
        raw_data = load_raw(config.DATA_RAW_PATH)
        clean_data = clean_articles(raw_data)
        save_clean(clean_data, config.DATA_CLEAN_PATH)

    # ── STEP 3: Load into Neo4j AuraDB ────────────────────────────────────────
    if step in ("load", "all"):
        logger.info("═══════════ STEP 3: LOADING INTO NEO4J ═══════════")
        with Neo4jConnector() as conn:
            loader = GraphLoader(conn)
            clean_data = load_raw(config.DATA_CLEAN_PATH)
            loader.load_all(clean_data)

    # ── STEP 4: Visualize ─────────────────────────────────────────────────────
    if step in ("visualize", "all"):
        logger.info("═══════════ STEP 4: VISUALIZATION ═══════════")
        with Neo4jConnector() as conn:
            with conn.driver.session(database=config.NEO4J_DATABASE) as session:
                plot_collaboration_network(session)
                plot_citation_network(session)
                plot_trending_subjects(session)
                plot_top_authors(session)

    logger.info("✅ Pipeline complete! Check visualizations/ folder.")


if __name__ == "__main__":
    main()
