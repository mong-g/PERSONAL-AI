from duckduckgo_search import DDGS
import logging

def web_search(query: str, max_results: int = 5) -> str:
    """
    Searches the live web for a query and returns snippets of results.
    Use this for current events, news, weather, or facts you don't know.
    
    Args:
        query: The search query string.
        max_results: Maximum number of snippets to return.
    """
    try:
        logging.info(f"Performing web search for: {query}")
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            
            if not results:
                return f"No web search results found for '{query}'."

            formatted_results = []
            for r in results:
                formatted_results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}")
            
            return "\n\n---\n\n".join(formatted_results)

    except Exception as e:
        logging.error(f"Web search error: {e}")
        return f"I had trouble searching the web: {str(e)}"
