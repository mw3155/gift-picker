import uuid

# In-memory storage
data_store = {}

def generate_chat_link():
    link_a = str(uuid.uuid4())
    data_store[link_a] = {"user2_responses": [], "result_link": None}
    return link_a

def save_chat_and_generate_result_link(link_a, responses):
    if link_a not in data_store:
        return None
    link_b = str(uuid.uuid4())
    data_store[link_a]["user2_responses"] = responses
    data_store[link_a]["result_link"] = link_b
    data_store[link_b] = {"gift_suggestions": generate_gift_ideas(responses)}
    return link_b

def get_gift_suggestions(link_b):
    if link_b not in data_store:
        return None
    return data_store[link_b]["gift_suggestions"]

def generate_gift_ideas(messages):
    """Generate gift ideas based on chat messages"""
    # Extract user responses
    user_responses = [msg["content"] for msg in messages if msg["role"] == "user"]
    
    # For now, return simple suggestions based on the responses
    # In a real implementation, you might want to use GPT to analyze the responses
    # and generate more meaningful suggestions
    return [
        "Based on their interests: A hobby-related gift",
        "Something practical they mentioned wanting",
        "A surprise gift that matches their preferences"
    ]
