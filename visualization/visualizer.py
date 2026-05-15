"""
Visualizer — generates publication-analysis charts from Neo4j data.
All plots are saved as PNG files in the visualizations/ folder.
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless rendering inside Docker
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import networkx as nx
import numpy as np
import pandas as pd
from loguru import logger

import config

# Ensure output directory exists
Path(config.VISUALIZATION_PATH).mkdir(parents=True, exist_ok=True)

# Use a built-in style compatible with recent matplotlib
try:
    plt.style.use("seaborn-v0_8-darkgrid")
except OSError:
    plt.style.use("ggplot")


# ── 1. Collaboration Network ─────────────────────────────────────────────────

def plot_collaboration_network(session) -> None:
    """Build and plot an undirected author-collaboration graph."""
    query = """
    MATCH (a1:Author)-[:WROTE]->(ar:Article)<-[:WROTE]-(a2:Author)
    WHERE id(a1) < id(a2)
    RETURN a1.name AS author1, a2.name AS author2, COUNT(ar) AS weight
    ORDER BY weight DESC
    LIMIT 150
    """
    records = session.run(query).data()

    if not records:
        logger.warning("⚠️  No collaboration data found — skipping network plot.")
        return

    G = nx.Graph()
    for rec in records:
        G.add_edge(rec["author1"], rec["author2"], weight=rec["weight"])

    fig, ax = plt.subplots(figsize=(16, 12))
    pos = nx.spring_layout(G, k=1.8, iterations=50, seed=42)

    # Node size ∝ degree
    degrees = dict(G.degree())
    node_sizes = [max(degrees[n] * 120, 200) for n in G.nodes()]

    # Edge width ∝ collaboration count
    weights = [G[u][v]["weight"] for u, v in G.edges()]
    max_w = max(weights) if weights else 1
    edge_widths = [1 + 4 * (w / max_w) for w in weights]

    nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths, alpha=0.3, edge_color="#888888")
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_size=node_sizes,
        node_color="#4C72B0",
        alpha=0.85,
        edgecolors="#2c3e50",
        linewidths=0.8,
    )

    # Label only top-degree nodes to avoid clutter
    top_n = 25
    top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:top_n]
    labels = {n: n for n in top_nodes}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, font_weight="bold", ax=ax)

    ax.set_title("Author Collaboration Network", fontsize=18, fontweight="bold", pad=20)
    ax.axis("off")
    fig.tight_layout()
    out = os.path.join(config.VISUALIZATION_PATH, "collaboration_network.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"📊 Saved → {out}")


# ── 2. Citation Network ──────────────────────────────────────────────────────

def plot_citation_network(session) -> None:
    """Build and plot a directed citation graph, coloured by year."""
    query = """
    MATCH (a1:Article)-[:CITES]->(a2:Article)
    RETURN a1.id AS source, a1.year AS source_year,
           a2.id AS target, a2.year AS target_year
    LIMIT 500
    """
    records = session.run(query).data()

    if not records:
        logger.warning("⚠️  No citation data found — skipping citation network plot.")
        # Create a placeholder chart instead
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(
            0.5, 0.5,
            "No CITES relationships found.\n"
            "arXiv API does not provide citation data.\n"
            "This graph would populate if citation links were loaded.",
            ha="center", va="center", fontsize=14, transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f0f0f0", edgecolor="#cccccc"),
        )
        ax.set_title("Citation Network", fontsize=18, fontweight="bold")
        ax.axis("off")
        out = os.path.join(config.VISUALIZATION_PATH, "citation_network.png")
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"📊 Saved placeholder → {out}")
        return

    G = nx.DiGraph()
    years = {}
    for rec in records:
        G.add_edge(rec["source"], rec["target"])
        years[rec["source"]] = rec.get("source_year", 2020)
        years[rec["target"]] = rec.get("target_year", 2020)

    fig, ax = plt.subplots(figsize=(14, 10))
    pos = nx.spring_layout(G, seed=42)

    year_values = [years.get(n, 2020) for n in G.nodes()]
    cmap = cm.coolwarm

    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.2, arrows=True, arrowsize=8)
    nodes = nx.draw_networkx_nodes(
        G, pos, ax=ax, node_size=60, node_color=year_values, cmap=cmap, alpha=0.8
    )

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(min(year_values), max(year_values)))
    sm.set_array([])
    fig.colorbar(sm, ax=ax, label="Year")

    ax.set_title("Citation Network", fontsize=18, fontweight="bold", pad=20)
    ax.axis("off")
    fig.tight_layout()
    out = os.path.join(config.VISUALIZATION_PATH, "citation_network.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"📊 Saved → {out}")


# ── 3. Trending Subjects ─────────────────────────────────────────────────────

def plot_trending_subjects(session) -> None:
    """Stacked bar chart: article count per subject per year."""
    query = """
    MATCH (a:Article)-[:HAS_SUBJECT]->(s:Subject)
    RETURN a.year AS year, s.name AS subject, COUNT(a) AS count
    ORDER BY year
    """
    records = session.run(query).data()

    if not records:
        logger.warning("⚠️  No subject data found — skipping trending subjects plot.")
        return

    df = pd.DataFrame(records)
    pivot = df.pivot_table(index="year", columns="subject", values="count", fill_value=0)
    pivot = pivot.sort_index()

    fig, ax = plt.subplots(figsize=(14, 8))
    pivot.plot(kind="bar", stacked=True, ax=ax, colormap="tab10", edgecolor="white", linewidth=0.5)
    ax.set_title("Trending Research Subjects by Year", fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel("Year", fontsize=13)
    ax.set_ylabel("Number of Articles", fontsize=13)
    ax.legend(title="Subject", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    fig.tight_layout()
    out = os.path.join(config.VISUALIZATION_PATH, "trending_subjects.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"📊 Saved → {out}")


# ── 4. Top Authors ───────────────────────────────────────────────────────────

def plot_top_authors(session) -> None:
    """Horizontal bar chart of the top 15 most prolific authors."""
    query = """
    MATCH (au:Author)-[:WROTE]->(ar:Article)
    RETURN au.name AS author, COUNT(ar) AS articles
    ORDER BY articles DESC
    LIMIT 15
    """
    records = session.run(query).data()

    if not records:
        logger.warning("⚠️  No author data found — skipping top authors plot.")
        return

    df = pd.DataFrame(records).sort_values("articles", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(
        df["author"], df["articles"],
        color=plt.cm.viridis(np.linspace(0.3, 0.9, len(df))),
        edgecolor="white", linewidth=0.6,
    )
    ax.set_title("Top 15 Most Prolific Authors", fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel("Number of Articles", fontsize=13)

    # Add value labels
    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 0.3, bar.get_y() + bar.get_height() / 2,
            f"{int(width)}", va="center", fontsize=10,
        )

    fig.tight_layout()
    out = os.path.join(config.VISUALIZATION_PATH, "top_authors.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"📊 Saved → {out}")
