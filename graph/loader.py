"""
Graph Loader — creates nodes and relationships in Neo4j using MERGE.
Idempotent: safe to re-run without creating duplicates.
"""

from loguru import logger
from tqdm import tqdm

from graph.neo4j_connector import Neo4jConnector


class GraphLoader:
    """Loads cleaned article data into a Neo4j graph database."""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector
        self.driver = connector.driver
        self.database = connector.database

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _run(self, cypher: str, **kwargs):
        with self.driver.session(database=self.database) as session:
            session.run(cypher, **kwargs)

    # ── Constraints ───────────────────────────────────────────────────────────
    def create_constraints(self):
        """Create uniqueness constraints (idempotent via IF NOT EXISTS)."""
        constraints = [
            "CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT author_name IF NOT EXISTS FOR (au:Author) REQUIRE au.name IS UNIQUE",
            "CREATE CONSTRAINT subject_name IF NOT EXISTS FOR (s:Subject) REQUIRE s.name IS UNIQUE",
        ]
        for cypher in constraints:
            self._run(cypher)
        logger.info("✅ Uniqueness constraints created / verified.")

    # ── Nodes ─────────────────────────────────────────────────────────────────
    def load_articles(self, data: list[dict]):
        """MERGE Article nodes."""
        cypher = """
        MERGE (a:Article {id: $id})
        SET a.title          = $title,
            a.year           = $year,
            a.abstract       = $abstract,
            a.url            = $url,
            a.citation_count = 0
        """
        count = 0
        for article in tqdm(data, desc="📄 Loading articles", unit="article"):
            self._run(
                cypher,
                parameters={
                    "id": article["arxiv_id"],
                    "title": article["title"],
                    "year": article["year"],
                    "abstract": article.get("abstract", ""),
                    "url": article.get("url", ""),
                },
            )
            count += 1
        logger.info(f"✅ Loaded {count} Article nodes.")

    def load_authors(self, data: list[dict]):
        """MERGE Author nodes and WROTE relationships."""
        cypher = """
        MERGE (au:Author {name: $author_name})
        WITH au
        MATCH (a:Article {id: $article_id})
        MERGE (au)-[r:WROTE]->(a)
        SET r.year = $year
        """
        count = 0
        for article in tqdm(data, desc="👤 Loading authors", unit="article"):
            for author in article.get("authors", []):
                self._run(
                    cypher,
                    parameters={
                        "author_name": author,
                        "article_id": article["arxiv_id"],
                        "year": article["year"],
                    },
                )
                count += 1
        logger.info(f"✅ Loaded {count} Author nodes + WROTE relationships.")

    def load_subjects(self, data: list[dict]):
        """MERGE Subject nodes and HAS_SUBJECT relationships."""
        cypher = """
        MERGE (s:Subject {name: $subject_name})
        WITH s
        MATCH (a:Article {id: $article_id})
        MERGE (a)-[:HAS_SUBJECT]->(s)
        """
        count = 0
        for article in tqdm(data, desc="📚 Loading subjects", unit="article"):
            for subject in article.get("subjects", []):
                self._run(
                    cypher,
                    parameters={
                        "subject_name": subject,
                        "article_id": article["arxiv_id"],
                    },
                )
                count += 1
        logger.info(f"✅ Loaded {count} Subject nodes + HAS_SUBJECT relationships.")

    # ── Orchestrator ──────────────────────────────────────────────────────────
    def load_all(self, data: list[dict]):
        """Run full graph loading pipeline in the correct order."""
        logger.info(f"🚀 Loading {len(data)} articles into Neo4j…")
        self.create_constraints()
        self.load_articles(data)
        self.load_authors(data)
        self.load_subjects(data)
        logger.info("✅ Graph loading complete!")
