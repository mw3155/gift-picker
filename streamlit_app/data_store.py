import uuid
import openai
import logging
import os

# Configure OpenAI if not already configured
if not openai.api_key:
    openai.api_key = os.getenv("OPENAI_API_KEY")

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
    """Generate gift ideas based on chat messages using GPT"""
    try:
        # Prepare the conversation for GPT
        system_prompt = """You are Santa's gift suggestion expert. Based on the chat conversation between the elf and the gift recipient, suggest 5 specific gift ideas.
        
        Guidelines:
        1. Each suggestion should be specific and actionable (e.g., "A high-quality yoga mat with carrying strap" rather than just "yoga equipment")
        2. Include a brief reason why this gift would be good based on their responses
        3. Suggestions should vary in price range
        4. Keep the festive tone but be practical
        5. Format each suggestion on a new line starting with "🎁"
        """
        
        # Format the chat history for better context
        chat_summary = "Chat summary:\n"
        for msg in messages:
            if msg["role"] == "assistant":
                chat_summary += f"Elf asked: {msg['content']}\n"
            elif msg["role"] == "user":
                chat_summary += f"They answered: {msg['content']}\n"
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_summary}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        suggestions = response.choices[0].message.content.split("\n")
        # Filter out empty lines and ensure each suggestion starts with 🎁
        suggestions = [s.strip() for s in suggestions if s.strip()]
        return suggestions
        
    except Exception as e:
        logging.error(f"Error generating gift ideas: {e}")
        # Fallback suggestions if API call fails
        return [
            "🎁 A hobby-related gift based on their interests",
            "🎁 Something practical they mentioned wanting",
            "🎁 A surprise gift that matches their preferences"
        ]
