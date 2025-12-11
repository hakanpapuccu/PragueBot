from mcp.server.fastmcp import FastMCP
import httpx
from duckduckgo_search import DDGS
import json

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
