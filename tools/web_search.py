"""
E.V. Web Search — DuckDuckGo search integration.
"""

import logging
from typing import List, Dict

logger = logging.getLogger("ev.tools.web_search")


def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo.
    Returns formatted results with titles, snippets, and URLs.
    """
    num_results = min(num_results, 10)

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))

        if not results:
            return f"No results found for: {query}"

        output_lines = [f"🔍 Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "No description")
            href = r.get("href", "")
            output_lines.append(f"{i}. **{title}**")
            output_lines.append(f"   {body}")
            if href:
                output_lines.append(f"   URL: {href}")
            output_lines.append("")

        return "\n".join(output_lines)

    except ImportError:
        return "Error: duckduckgo-search package not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"Error searching the web: {e}"
