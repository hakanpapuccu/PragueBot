from mcp.server.fastmcp import FastMCP
import httpx
from duckduckgo_search import DDGS
import json
import wikipedia

# Create an MCP server
mcp = FastMCP("Prague Guide Tools")

@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a specific city using wttr.in."""
    try:
        # format=3 gives a one-line output like: "Prague: ⛅️  +12°C"
        response = httpx.get(f"https://wttr.in/{city}?format=3", timeout=5.0)
        return response.text.strip()
    except Exception as e:
        return f"Could not fetch weather: {e}"

@mcp.tool()
def search_hotels(city: str, query: str = "") -> str:
    """Search for hotels in a specific city using DuckDuckGo."""
    try:
        search_term = f"hotels in {city} {query}"
        results = DDGS().text(search_term, max_results=5)
        
        # Format results nicely
        formatted = "Here are some real hotel results:\n"
        for res in results:
            formatted += f"- **{res['title']}**: {res['body']} ({res['href']})\n"
            
        if not results:
            return f"No hotels found for {city}."
            
        return formatted
    except Exception as e:
        return f"Could not search hotels: {e}"

if __name__ == "__main__":
    mcp.run()

@mcp.tool()
def search_wikipedia(query: str, lang: str = "tr") -> str:
    """Search Wikipedia for a given query and return the summary."""
    try:
        wikipedia.set_lang(lang)
        # Search for the page
        search_results = wikipedia.search(query)
        if not search_results:
            return "No Wikipedia results found."
        
        # Get the first result's summary
        page_title = search_results[0]
        summary = wikipedia.summary(page_title, sentences=5)
        return f"**Wikipedia ({page_title}):**\n{summary}\n\n[Read more]({wikipedia.page(page_title).url})"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Ambiguous query. Options: {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError:
        return "Page not found on Wikipedia."
    except Exception as e:
        return f"Wikipedia Error: {e}"
