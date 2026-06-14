"""
Web search module using DuckDuckGo (no API key required).

⚠️ PRIVACY WARNING:
Search queries are sent to DuckDuckGo servers. Do NOT use web search if your
questions contain sensitive, internal, or confidential information.
"""

import logging
from typing import List, Dict
from ddgs import DDGS

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 3) -> List[Dict]:
    """
    Search the web using DuckDuckGo and return relevant snippets.

    ⚠️ WARNING: This sends your query to DuckDuckGo servers.
    Only use for generic, non-sensitive questions.

    Parameters:
        query (str): Search query.
        max_results (int): Maximum number of results to return.

    Returns:
        List[Dict]: Each dict contains {"text": str, "source": str}
    """
    try:
        results = DDGS().text(query, max_results=max_results)
        
        output = []
        for result in results:
            output.append({
                "text": f"{result.get('title', '')}\n{result.get('body', '')}",
                "source": result.get("href", "Unknown"),
            })
        
        logger.info(f"Retrieved {len(output)} web search results for query: {query}")
        return output
    
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return []
