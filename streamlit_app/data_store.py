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

def generate_gift_ideas(responses):
    # Simple hardcoded response for now
    return [
        f"A gift related to their hobby: {responses[0]}",
        f"Something they always wanted: {responses[1]}",
        f"A {responses[2]} gift."
    ]
