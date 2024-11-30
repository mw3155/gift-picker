from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_url = "localhost:3000"
backend_url = "localhost:8000"

# In-memory storage for simplicity
data_store = {}

@app.post("/generate-chat-link")
def generate_chat_link():
    link_a = str(uuid.uuid4())
    data_store[link_a] = {"user2_responses": [], "result_link": None}
    return {"link_a": f"http://{frontend_url}/chat.html?id={link_a}"}

@app.post("/complete-chat/{link_a}")
def complete_chat(link_a: str, responses: dict):
    if link_a not in data_store:
        return {"error": "Invalid link"}
    
    # Save User2 responses and generate result link
    link_b = str(uuid.uuid4())
    data_store[link_a]["user2_responses"] = responses
    data_store[link_a]["result_link"] = link_b
    data_store[link_b] = {"gift_suggestions": generate_gift_ideas(responses)}
    
    return {"link_b": f"http://{frontend_url}/result.html?id={link_b}"}

@app.get("/get-suggestions/{link_b}")
def get_suggestions(link_b: str):
    if link_b not in data_store:
        return {"error": "Invalid link"}
    return data_store[link_b]["gift_suggestions"]

def generate_gift_ideas(responses):
    # Use OpenAI GPT API or return dummy data for MVP
    return ["Gift Idea 1", "Gift Idea 2", "Gift Idea 3"]

