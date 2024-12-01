import uuid
import logging
import os
from typing import Optional
from datetime import datetime
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_app.ai_operations import generate_gift_suggestions  # Add this import

# In-memory storage
data_store = {}

# Add these environment variables
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
BASE_URL = os.getenv("BASE_URL", "https://chatwithsanta.streamlit.app")

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

def send_email(recipient_email, subject, body):
    """Send an email using Gmail SMTP"""
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD]):
        logging.warning("Gmail credentials not configured. Skipping email send.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp_server.sendmail(GMAIL_USER, recipient_email, msg.as_string())
            
        logging.info(f"Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

def save_chat_and_generate_result_link(link_a, responses):
    if link_a not in data_store:
        return None
    
    link_b = str(uuid.uuid4())
    data_store[link_a].update({
        "user2_responses": responses,
        "result_link": link_b,
        "status": "completed"
    })
    
    # Get the budget from metadata for gift suggestions
    budget = data_store[link_a].get('budget')
    suggestions = generate_gift_suggestions(responses, budget)  # Using the imported function
    data_store[link_b] = {
        "gift_suggestions": suggestions,
        "parent_chat": link_a
    }
    
    # Send notification if email is available
    if notification_email := data_store[link_a].get('notification_email'):
        full_result_url = f"{BASE_URL}?result={link_b}"
        email_subject = "🎁 Your Gift Suggestions Are Ready!"
        email_body = f"""
        <html>
        <body>
        <h2>Ho ho ho! 🎅</h2>
        <p>Great news! The person you're buying a gift for has finished chatting with Santa.</p>
        <p>Click the link below to see your personalized gift suggestions:</p>
        <p><a href="{full_result_url}">View Gift Suggestions</a></p>
        <p>Happy gifting! 🎄✨</p>
        </body>
        </html>
        """
        
        if send_email(notification_email, email_subject, email_body):
            logging.info(f"Notification email sent to {notification_email}")
        else:
            logging.error(f"Failed to send notification email to {notification_email}")
    
    return link_b

def get_gift_suggestions(link_b):
    if link_b not in data_store:
        return None
    return data_store[link_b]["gift_suggestions"]

def get_chat_data(chat_id):
    """
    Retrieve chat metadata from storage
    
    Args:
        chat_id (str): The unique identifier for the chat
        
    Returns:
        dict: Chat metadata including budget and email, or None if not found
    """
    try:
        if chat_id in data_store:
            return {
                'budget': data_store[chat_id].get('budget'),
                'notification_email': data_store[chat_id].get('notification_email'),
                'status': data_store[chat_id].get('status', 'pending')
            }
        return None
    except Exception as e:
        logging.error(f"Error retrieving chat data: {e}")
        return None
