import logging
import streamlit as st
import openai  # Change to direct import
import os
from datetime import datetime
from data_store import generate_chat_link, save_chat_and_generate_result_link, get_gift_suggestions, is_valid_email, get_chat_data
from ai_operations import generate_santa_response, SANTA_PROMPT  # Add SANTA_PROMPT to import

# Configure base URL
BASE_URL = os.getenv("BASE_URL", "https://chatwithsanta.streamlit.app")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Add new function to handle optional Langfuse initialization
def init_langfuse():
    try:
        from langfuse.decorators import observe
        from langfuse import Langfuse
        langfuse = Langfuse()
        return observe, langfuse
    except (ImportError, Exception) as e:
        logging.warning(f"Langfuse initialization failed: {e}. Continuing without observability.")
        return None, None

# Initialize Langfuse (optional)
observe, langfuse = init_langfuse()

# Configure OpenAI (modify the OpenAI configuration)
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_type = "azure"
openai.api_version = "2024-08-01-preview"

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Add this after initializing session_state.messages
if "santa_submissions" not in st.session_state:
    st.session_state.santa_submissions = []

# Add at the start of the app
if "session_start" not in st.session_state:
    st.session_state.session_start = datetime.now()
    st.session_state.messages = []
    st.session_state.santa_submissions = []

# Add session timeout check
def check_session_timeout():
    if "session_start" in st.session_state:
        session_duration = datetime.now() - st.session_state.session_start
        if session_duration.total_seconds() > 3600:  # 1 hour timeout
            st.session_state.clear()
            st.rerun()

# Modify the generate_response function to include budget
def generate_response(messages, budget=None):
    """Generate a single response from Santa Claus"""
    # If Langfuse is available, wrap this function
    if observe:
        return _generate_response_with_observability(messages, budget)
    return generate_santa_response(messages, budget)  # Just call the imported function directly

@observe() if observe else lambda: None  # This makes the decorator optional
def _generate_response_with_observability(messages, budget):
    return generate_santa_response(messages, budget)

# Modify get_ai_response similarly
def get_ai_response(messages, budget=None):
    """Get a single response from the OpenAI API"""
    if observe:
        return _get_ai_response_with_observability(messages, budget)
    return _get_ai_response_impl(messages, budget)

@observe() if observe else lambda: None
def _get_ai_response_with_observability(messages, budget):
    return _get_ai_response_impl(messages, budget)

def _get_ai_response_impl(messages, budget):
    """Implementation of response generation"""
    try:
        return generate_santa_response(messages, budget)
    except openai.RateLimitError:
        logging.error("Rate limit exceeded")
        st.error("Too many requests. Please wait a moment and try again.")
    except openai.APIError as e:
        logging.error(f"OpenAI API error: {e}")
        st.error("Service temporarily unavailable. Please try again later.")
    except Exception as e:
        logging.error(f"Error generating AI response: {e}")
        st.error("Oh candy canes! Something went wrong. Please try again!")
    return None

# Get URL parameters
chat_link = st.query_params.get("chat", None)
result_link = st.query_params.get("result", None)

# Check result page first
if result_link:
    # Results page
    st.set_page_config(
        page_title="Santa's Gift Ideas",
        page_icon="🎁",
        layout="centered"
    )
    
    st.title("🎁 Santa's Christmas Surprise")
    suggestions = get_gift_suggestions(result_link)
    
    if suggestions:
        st.markdown("""
        Ho ho ho! 🎅✨
        
        Based on my wonderful chat with your special someone, I've carefully selected some gift ideas that I think they'll love:
        """)
        
        # Create a nice card-like display for each suggestion
        for suggestion in suggestions:
            # Create Amazon search URL using the suggestion text
            suggestion_text = suggestion['text']  # Extract text from suggestion dictionary
            keywords = suggestion['keywords']  # Get keywords for better search results
            search_terms = keywords if keywords else suggestion_text
            amazon_search_url = f"https://www.amazon.com/s?k={'+'.join(search_terms.split())}"
            
            st.markdown(f"""
            <div style='
                background-color: #f0f8ff; 
                padding: 20px; 
                border-radius: 10px; 
                margin: 10px 0;
                border: 2px solid #e1e4e8;
                color: #1e1e1e;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                font-size: 16px;
                line-height: 1.5;
            '>
                {suggestion_text}
                <br><br>
                <a href="{amazon_search_url}" target="_blank" style="
                    display: inline-block;
                    padding: 8px 16px;
                    background-color: #FF9900;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 14px;
                ">
                    🔍 Search on Amazon
                </a>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("""
        ---
        💝 Remember, these are just suggestions! The best gifts come from the heart.
        
        🎄 Want to find a gift for someone else? [Start a new gift search](/)
        """)
        
        # Add some festive decorations
        st.snow()  # Add some snowfall effect
    else:
        st.error("Oh no! This gift suggestion link seems to be invalid. Please check with your friend for the correct link! 🎅")
        st.markdown("Want to start your own gift search? [Click here](/) to begin!")

# Then check chat page
elif chat_link:
    # Chat page - existing chat functionality
    # Page config
    st.set_page_config(
        page_title="Chat with Santa",
        page_icon="🎁",
        layout="centered"
    )

    # Title and description
    st.title("🎄 Chat with Santa")
    st.markdown("""
    Ho ho ho! Merry Christmas! 🎅✨

    I'm Santa Claus, and I'm so happy you're here! Your friend has asked for my help in choosing a special Christmas gift for you.

    Let's have a jolly chat so I can learn more about you and prepare something wonderful for Christmas! 

    **Note:** You can finish our chat at any time by clicking the "Enough chatting. Send to Gift Production! 🎁" button.
    """)

    # Get budget from the chat link data
    chat_data = get_chat_data(chat_link)
    budget = chat_data.get('budget') if chat_data else None

    # Initialize chat with AI's first message if chat is empty
    if len(st.session_state.messages) == 0:
        logging.info("Generating initial AI message...")
        initial_response = get_ai_response([], budget)
        if initial_response:
            initial_message = {
                "role": "assistant", 
                "content": initial_response
            }
            st.session_state.messages.append(initial_message)
            logging.info(f"Initial AI message generated: {initial_response}")
        else:
            logging.error("Failed to generate initial AI message")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        logging.info(f"User input: {prompt}")
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get and display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            logging.info("Requesting AI response...")
            ai_response = get_ai_response(st.session_state.messages, budget)
            
            if ai_response:
                message_placeholder.markdown(ai_response)
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
            else:
                logging.error("Failed to get AI response")

    if st.button("Restart Chat 🔄"):
        st.session_state.messages = []
        st.rerun()

    if st.button("Enough chatting. Send to Gift Production! 🎁"):
        if len(st.session_state.messages) > 0:
            try:
                logging.info("Attempting to save chat and generate result link...")
                # Create submission record
                submission = {
                    "timestamp": datetime.now().isoformat(),
                    "conversation": st.session_state.messages
                }
                
                # Save to data store and get result link
                logging.info(f"Saving chat for chat_link: {chat_link}")
                result_link = save_chat_and_generate_result_link(chat_link, st.session_state.messages)
                
                if result_link:
                    full_result_url = f"{BASE_URL}?result={result_link}"
                    logging.info(f"Successfully generated result link: {result_link}")
                    st.success("Ho ho ho! Your chat has been sent to Gift Production! 🎁")
                    st.code(full_result_url, language=None)
                    st.info("Share this link with your friend to see Santa's gift suggestions! 🎁")
                else:
                    logging.error("Failed to generate result link - returned None")
                    st.error("Oh no! Something went wrong saving your chat. Please try again! 🎅")
            except Exception as e:
                logging.error(f"Error saving chat: {str(e)}", exc_info=True)
                st.error(f"Oh no! Something went wrong saving your chat: {str(e)}")
        else:
            st.warning("There's nothing to send to Gift Production yet! Have a chat with Santa first! 🎅")


else:
    # Default page - Link generation
    st.set_page_config(
        page_title="Santa's Gift Helper",
        page_icon="🎁",
        layout="centered"
    )
    st.title("🎄Santa's Gift Helper")
    st.markdown("""
    Ho ho ho! Merry Christmas! 🎅✨
    
    Want help choosing the perfect Christmas gift for someone special? Let me, Santa Claus, help you!
    
    1. Set your budget and contact details below
    2. Share the magic Christmas link with the person you want to surprise
    3. They'll have a jolly chat with me about their interests
    4. You'll get special gift suggestions based on our conversation!
    """)
    
    # Add budget selection
    budget_ranges = [
        "Under $25",
        "$25 - $50",
        "$50 - $100",
        "$100 - $200",
        "$200 - $500",
        "Over $500"
    ]
    budget = st.select_slider(
        "Select your budget range 💰",
        options=budget_ranges,
        value="$50 - $100"
    )
    
    # Add email input
    email = st.text_input(
        "Your email address 📧",
        help="We'll notify you when they complete the questionnaire!"
    )
    
    # Generate link button with validation
    if st.button("Generate Magic Link ✨"):
        if not email:
            st.warning("Please enter your email address! 📧")
        elif not is_valid_email(email):
            st.error("Please enter a valid email address! 📧")
        else:
            new_link = generate_chat_link(budget=budget, email=email)
            full_url = f"{BASE_URL}?chat={new_link}"
            
            st.success("Magic link generated successfully! ✨")
            # Display both clickable link and copyable code
            st.markdown(f"**Click here to open:** [Magic Link 🎄]({full_url})")
            st.code(full_url, language=None)
            st.info(f"""
            Share this link with the person you want to buy a gift for! 🎁
            
            We'll notify you at {email} when they complete the questionnaire.
            """)
