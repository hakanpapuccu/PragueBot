from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

try:
    chat = client.chats.create(model="gemini-1.5-flash") # Use 1.5-flash for test to avoid quota if possible, or 2.5-flash
    print("Chat object attributes:", dir(chat))
    
    # Try to see if there is history
    # response = chat.send_message("Hello")
    # print("Chat history type:", type(chat.history)) # This line caused error
except Exception as e:
    print(f"Error during inspection: {e}")
