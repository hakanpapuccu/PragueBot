from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from google.genai import errors
import subprocess
import json
import sys

# Load environment variables
load_dotenv()

app = FastAPI()



# Chat model
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

# In-memory history: {session_id: [messages]}
chat_history = {}

# Initialize Gemini Client
# We will use the system env variable GOOGLE_API_KEY
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found. Please create a .env file with your key.")
    # For robust local dev without crashing immediately (though agent won't work):
    # api_key = "dummy" 
    # But genai.Client might validate it. Let's just exit gracefully or let it fail later?
    # Better to exit with useful message.
    import sys
    sys.exit(1)

client = genai.Client(api_key=api_key)

# Define Tools directly for simplicity if MCP networking is complex,
# BUT we want to adhere to MCP structure.
# For this 'simple agent', we will define the functions that CALL the MCP tools
# or we can define the tools directly on the client if we want to skip the network hop.
# The user asked for "mcp server support".
# So let's simluate an MCP client connecting to our local tools.
# To keep it robust without complex async stdio handling in this snippet, 
# I will import the functions from the module for this simple implementation 
# and expose them to Gemini. 
# REAL MCP CLIENT implementation would require connecting to stdio/SSE.
# I will use a hybrid approach: Define tools for Gemini that wrap the logic.

# Import real tools from our MCP server module
# Since both are in the same project, we can import directly for "in-process" usage
# preserving the logic in the mcp_server.py file as requested.
import sys
import os

# Ensure backend directory is in path if needed (it usually is if running from root)
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.tools.mcp_server import get_weather, search_hotels

# Refine wrapper functions if needed, or use directly.
# The decorators in mcp_server might wrap them. 
# FastMCP decorators usually return the original function as well or a callable.
# Let's verify by just using them. If they fail, we will wrap them.
# Update: FastMCP @mcp.tool creates a Tool object, but often makes it callable.
# If not, we will need to extract the underlying function.
# Let's try to wrap them simply to be safe and ensure correct Gemini signature.

def safe_get_weather(city: str):
    """Get real weather."""
    return get_weather(city)

def safe_search_hotels(city: str, query: str = ""):
    """Search real hotels."""
    return search_hotels(city, query)

# Register tools with Gemini
tools = [safe_get_weather, safe_search_hotels]

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id
    user_msg = request.message

    if session_id not in chat_history:
        chat_history[session_id] = []
        # System prompt or initial setup
        # chat_history[session_id].append(types.Content(role="model", parts=[types.Part(text="Hello! I am your Prague Guide.")]))

    history = chat_history[session_id]
    
    # Add user message
    # history.append(types.Content(role="user", parts=[types.Part(text=user_msg)]))
    
    # Configure config with tools
    generate_content_config = types.GenerateContentConfig(
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
    )

    # Call Gemini
    # We use chat interface
    try:
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=generate_content_config,
            history=history
        )
        
        response = chat.send_message(user_msg)
        
        # In this SDK version, use get_history() or similar if available, 
        # or rely on the fact that if we pass 'history' list, does it update it in place?
        # The 'get_history' method exists per inspection.
        # But 'history' passed to Create might be used for initialization.
        # Let's try retrieves history via method.
        # Actually, let's look at the inspection output again: 'get_history'
        chat_history[session_id] = chat.get_history()
        
        return {"response": response.text}
    except errors.ClientError as e:
        print(f"Gemini API Error: {e}")
        error_msg = str(e)
        if "429" in error_msg:
            return {"response": "⚠️ **Rate Limit Exceeded**: I'm feeling a bit overwhelmed! Please try again in 30 seconds."}
        return {"response": f"⚠️ **Error**: Something went wrong with the AI provider. ({e})"}
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return {"response": f"⚠️ **System Error**: An unexpected error occurred. ({e})"}

@app.get("/history")
async def get_history(session_id: str = "default"):
    return chat_history.get(session_id, [])

from fastapi.staticfiles import StaticFiles
# Mount static files (Frontend) - MUST be after API routes
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
