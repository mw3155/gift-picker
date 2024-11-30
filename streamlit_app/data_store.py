import uuid
import openai
import logging
import os
from typing import Optional
from datetime import datetime
import re

# Configure OpenAI if not already configured
if not openai.api_key:
    openai.api_key = os.getenv("OPENAI_API_KEY")

# In-memory storage
data_store = {}

def is_valid_email(email: str) -> bool:
    """Validate email format using regex pattern"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def save_chat_metadata(chat_id: str, metadata: dict) -> None:
    """Save chat metadata to storage"""
    if chat_id not in data_store:
        data_store[chat_id] = {}
    data_store[chat_id].update(metadata)

def generate_chat_link(budget: Optional[str] = None, email: Optional[str] = None) -> str:
    """Generate a unique chat link and store initial metadata"""
    chat_id = str(uuid.uuid4())
    
    # Store metadata
    metadata = {
        'created_at': datetime.now().isoformat(),
        'budget': budget,
        'notification_email': email,
        'status': 'pending'  # pending, completed
    }
    
    # Save metadata to your storage
    save_chat_metadata(chat_id, metadata)
    
    return chat_id

def save_chat_and_generate_result_link(link_a, responses):
    if link_a not in data_store:
        return None
    
    link_b = str(uuid.uuid4())
    data_store[link_a].update({
        "user2_responses": responses,
        "result_link": link_b,
        "status": "completed"  # Update status when chat is complete
    })
    
    # Get the budget from metadata for gift suggestions
    budget = data_store[link_a].get('budget')
    data_store[link_b] = {
        "gift_suggestions": generate_gift_ideas(responses, budget),
        "parent_chat": link_a  # Store reference to original chat
    }
    
    # Send notification if email is available
    if email := data_store[link_a].get('notification_email'):
        try:
            send_completion_notification(email, link_b)
        except Exception as e:
            logging.error(f"Failed to send notification email: {e}")
    
    return link_b

def get_gift_suggestions(link_b):
    if link_b not in data_store:
        return None
    return data_store[link_b]["gift_suggestions"]

def generate_gift_ideas(messages, budget: Optional[str] = None):
    """Generate gift ideas based on chat messages using GPT"""
    try:
        # Prepare the conversation for GPT
        system_prompt = """You are Santa's gift suggestion expert. Based on the chat conversation between the elf and the gift recipient, suggest 5 specific gift ideas.
        
        Guidelines:
        1. Each suggestion should be specific and actionable (e.g., "A high-quality yoga mat with carrying strap" rather than just "yoga equipment")
        2. Include a brief reason why this gift would be good based on their responses
        3. Keep suggestions within the specified budget range
        4. Keep the festive tone but be practical
        5. Format each suggestion on a new line starting with "🎁"
        """
        
        if budget:
            system_prompt += f"\n\nBudget range: {budget}"
        
        # Format the chat history for better context, excluding the last assistant message
        chat_summary = "Chat summary:\n"
        # Convert messages to list to use indexing
        messages_list = list(messages)
        # Exclude last message if it's from assistant
        if messages_list and messages_list[-1]["role"] == "assistant":
            messages_list = messages_list[:-1]
            
        for msg in messages_list:
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

def send_completion_notification(email: str, result_link: str) -> None:
    """Send email notification when chat is completed"""
    # TODO: Implement email sending functionality
    # For now, just log that we would send an email
    logging.info(f"Would send completion notification to {email} for result {result_link}")
    pass
