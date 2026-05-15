"""
Semantic Scholar API Extractor — fetches citation data for arXiv papers.
"""

import json
import time
from pathlib import Path

import requests
from loguru import logger
from tqdm import tqdm

import config


def fetch_citations_for_articles(arxiv_ids: list[str], batch_size: int = 100) -> list[dict]:
    """
    Fetch citation data from Semantic Scholar using batch queries.
    
    Parameters
    ----------
    arxiv_ids : list[str]
        List of arXiv IDs (e.g., ["2301.00001", "2104.12345"])
    batch_size : int
        Number of papers to query per batch (max 500 for S2 API)
        
    Returns
    -------
    list[dict]
        List of dicts containing the source arXiv ID and a list of cited arXiv IDs.
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/batch"
    params = {"fields": "citations,citations.externalIds"}
    
    citation_data = []
    
    for i in tqdm(range(0, len(arxiv_ids), batch_size), desc="🔗 Semantic Scholar citations"):
        batch_ids = [f"ARXIV:{aid}" for aid in arxiv_ids[i:i + batch_size]]
        payload = {"ids": batch_ids}
        
        try:
            response = requests.post(base_url, params=params, json=payload, timeout=30)
            if response.status_code == 429:
                logger.warning("Rate limited by Semantic Scholar. Waiting 5s...")
                time.sleep(5)
                response = requests.post(base_url, params=params, json=payload, timeout=30)
                
            response.raise_for_status()
            data = response.json()
            
            for paper, source_arxiv_id in zip(data, arxiv_ids[i:i + batch_size]):
                if paper is None or "citations" not in paper:
                    continue
                    
                cited_arxiv_ids = []
                for citation in paper["citations"]:
                    ext_ids = citation.get("externalIds", {})
                    if ext_ids and "ArXiv" in ext_ids:
                        cited_arxiv_ids.append(ext_ids["ArXiv"])
                        
                if cited_arxiv_ids:
                    citation_data.append({
                        "source_arxiv_id": source_arxiv_id,
                        "cites": cited_arxiv_ids
                    })
                    
        except Exception as e:
            logger.error(f"Error fetching batch {i}: {e}")
            
        # polite sleep
        time.sleep(1)

    out_path = Path(config.DATA_CITATIONS_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(citation_data, fp, indent=2)
        
    logger.info(f"✅ Fetched citations for {len(citation_data)} articles → {out_path}")
    return citation_data
