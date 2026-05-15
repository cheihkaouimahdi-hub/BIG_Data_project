"""
Neo4j Connector — manages driver lifecycle for both local and AuraDB cloud.
"""

from loguru import logger
from neo4j import GraphDatabase

import config


class Neo4jConnector:
    """Thin wrapper around the official Neo4j Python driver.

    Supports both ``bolt://`` (local) and ``neo4j+s://`` (AuraDB cloud) URIs.
    Implements the context-manager protocol for easy ``with`` usage.
    """

    def __init__(self):
        self.uri = config.NEO4J_URI
        self.username = config.NEO4J_USERNAME
        self.password = config.NEO4J_PASSWORD
        self.database = config.NEO4J_DATABASE
        self.driver = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def connect(self):
        """Create the driver and verify connectivity."""
        # neo4j+s:// already implies encryption; no extra flag needed.
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
        )
        self.test_connection()
        logger.info(f"✅ Connected to Neo4j at {self.uri}")
        return self

    def close(self):
        """Shut down the driver gracefully."""
        if self.driver:
            self.driver.close()
            logger.info("🔌 Neo4j connection closed.")

    def test_connection(self):
        """Quick ping — raises on failure."""
        try:
            self.driver.verify_connectivity()
        except Exception as exc:
            raise ConnectionError(
                "❌ Cannot connect to Neo4j. Check your .env credentials.\n"
                f"   URI:  {self.uri}\n"
                f"   User: {self.username}\n"
                f"   Error: {exc}"
            ) from exc

    # ── Query helper ──────────────────────────────────────────────────────────
    def run_query(self, cypher: str, params: dict | None = None):
        """Execute a Cypher statement and return the list of records."""
        with self.driver.session(database=self.database) as session:
            result = session.run(cypher, parameters=params or {})
            return [record.data() for record in result]

    # ── Context manager ───────────────────────────────────────────────────────
    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
