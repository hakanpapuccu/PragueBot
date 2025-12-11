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

sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.tools.mcp_server import get_weather, search_hotels, search_wikipedia

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

def safe_search_wikipedia(query: str):
    """Search Wikipedia for general information."""
    return search_wikipedia(query)

# Register tools with Gemini
tools = [safe_get_weather, safe_search_hotels, safe_search_wikipedia]

from fastapi.responses import StreamingResponse
import json
import asyncio

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id
    user_msg = request.message
    model_to_use = request.model_name

    if session_id not in chat_history:
        chat_history[session_id] = []

    history = chat_history[session_id]
    
    # Enable tools but DISABLE automatic execution so we can intercept and notify
    generate_content_config = types.GenerateContentConfig(
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) 
    )

    async def event_generator():
        try:
            # 1. Send User Message
            chat = client.chats.create(
                model=model_to_use, 
                config=generate_content_config,
                history=history
            )
            
            response = chat.send_message(user_msg)
            
            # 2. Loop to handle function calls
            while True:
                # Check if the model wants to call a function
                function_call_part = None
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_call_part = part.function_call
                        break
                
                if function_call_part:
                    fn_name = function_call_part.name
                    fn_args = function_call_part.args
                    
                    # Notify Frontend: Thinking...
                    yield json.dumps({"type": "status", "content": f"🛠️ Using tool: {fn_name}..."}) + "\n"
                    
                    # Execute Tool
                    tool_result = "Error executing tool"
                    try:
                        if fn_name == "safe_get_weather":
                            tool_result = safe_get_weather(**fn_args)
                        elif fn_name == "safe_search_hotels":
                            tool_result = safe_search_hotels(**fn_args)
                        elif fn_name == "safe_search_wikipedia":
                            tool_result = safe_search_wikipedia(**fn_args)
                        else:
                            tool_result = f"Unknown tool: {fn_name}"
                    except Exception as e:
                        tool_result = f"Tool Execution Error: {e}"
                        
                    # Send result back to model
                    # We need to construct the function response part properly
                    # response = chat.send_message(
                    #    types.Content(
                    #        role="tool", 
                    #        parts=[types.Part(
                    #             function_response=types.FunctionResponse(
                    #                 name=fn_name,
                    #                 response={"result": tool_result}
                    #             )
                    #        )]
                    #    )
                    # )
                    # The SDK simplifies this usually, but manually:
                    response = chat.send_message(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_name,
                                response={"result": tool_result}
                            )
                        )
                    )
                else:
                    # No function call, just text response
                    break

            # 3. Final Response
            final_text = response.text
            yield json.dumps({"type": "response", "content": final_text}) + "\n"
            
            # Save History
            chat_history[session_id] = chat.get_history()

        except errors.ClientError as e:
            print(f"Gemini API Error: {e}")
            yield json.dumps({"type": "error", "content": f"⚠️ Rate Limit/API Error: {e}"}) + "\n"
        except Exception as e:
            print(f"Unexpected Error: {e}")
            yield json.dumps({"type": "error", "content": f"⚠️ System Error: {e}"}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

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
