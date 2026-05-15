"""
Configuration module — loads all settings from .env file.
Supports both local (bolt://) and AuraDB cloud (neo4j+s://) URIs.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Neo4j AuraDB Connection ──────────────────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ── arXiv Search Config ──────────────────────────────────────────────────────
SEARCH_KEYWORDS = [
    kw.strip()
    for kw in os.getenv("SEARCH_KEYWORDS", "machine learning").split(",")
]
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "300"))

# ── File Paths ────────────────────────────────────────────────────────────────
DATA_RAW_PATH = "data/raw/arxiv_raw.json"
DATA_CLEAN_PATH = "data/cleaned/articles_clean.json"
VISUALIZATION_PATH = "visualizations/"
