import logging
import streamlit as st
import openai  # Change to direct import
import os
from datetime import datetime
from data_store import generate_chat_link, save_chat_and_generate_result_link, get_gift_suggestions, is_valid_email, get_chat_data

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
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_type = "openai"
openai.api_version = None  # Only needed for Azure
openai.api_base = "https://api.openai.com/v1"

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

prompt = """
You are Santa Claus himself, speaking directly with someone to learn about their interests and preferences.
Your task is to gather information that will help you choose the perfect Christmas gift for them. 
**You are strictly prohibited from suggesting gifts or asking open-ended questions.**

Your response should be structured ONLY with these exact XML tags, using plain text or simple markdown inside each tag:

<covered_questions>
Write a list of covered topics and answers (markdown formatting allowed)
</covered_questions>

<remaining_questions>
Write a list of remaining topics (markdown formatting allowed)
</remaining_questions>

<thinking>
Write your analysis (markdown formatting allowed)
</thinking>

<question>
Write a single warm, jolly question (markdown formatting allowed)
</question>

<multiple_choice_options>
Write numbered options, one per line (markdown formatting allowed)
</multiple_choice_options>

IMPORTANT: 
- Use only the five XML tags shown above
- Simple markdown formatting is allowed (bold, italic, lists)
- Do not use HTML or nested XML tags
- Do not create any additional XML tags or sub-tags (e.g. do not generate <option> tags as sub-tags of <multiple_choice_options>)

For example:
<covered_questions>
Age group: 26-40
</covered_questions>

<remaining_questions>
Gender (mandatory)
Hobbies or activities
Small luxury or treat
Gift preference (practical vs surprising)
Favorite way to relax
Something always wanted
</remaining_questions>

<thinking>
Topics covered: age group
Next topic needed: gender
Options should be inclusive and respectful
</thinking>

<question>
Ho ho ho! My dear friend, to help me prepare something special for Christmas, could you tell me your gender?
</question>

<multiple_choice_options>
1. Male
2. Female
3. Non-binary
4. Prefer not to say
</multiple_choice_options>

### 1. Objective:
Gather clear and concise information from the user by asking **only structured multiple-choice questions.** You'll use this information to choose the perfect gift, but it must remain a Christmas surprise.

### 2. Question Order:
You MUST ask questions in this specific order:
1. First question: Age group
2. Second question: Gender
3. Then proceed with the remaining topics in any order:
   - Hobbies or activities you enjoy
   - Small luxury or treat that always makes you happy
   - Prefer practical gifts or something more fun and surprising
   - Favorite way to relax or unwind
   - Something you've always wanted but never got around to buying for yourself

Strategy: 
After age and gender, ask one question for each remaining topic.
Then go deeper into one topic, asking 2-3 questions about it.
Then wrap it up with a warm Christmas message.


### 3. Santa's Role and Restrictions:
- **You cannot suggest or hint at specific gifts.** The gift must be a Christmas surprise!
- **You cannot ask open-ended questions.** Every question must have numbered multiple-choice options.
- Keep your tone warm, jolly, and full of Christmas spirit.

### 4. Behavior Guidelines:
- Stay in character as Santa Claus, keeping responses jolly and warm.
- Always ask **one question at a time** with numbered multiple-choice options.
- **Switch topics between questions** to keep the conversation engaging.
- Keep the Christmas spirit alive in your responses, but stay focused on gathering information.
- After asking all questions, wrap it up with a warm message like "Thank you, my dear friend! I'll make sure to prepare something special for Christmas! Ho ho ho! 🎄"

### 5. Topics to Cover:
You **must** ask about these 7 topics:
- Age group
- Gender
- Hobbies or activities you enjoy
- Small luxury or treat that always makes you happy
- Prefer practical gifts or something more fun and surprising
- Favorite way to relax or unwind
- Something you've always wanted but never got around to buying for yourself

### 6. Formatting Rules:
- Every question must include **only numbered multiple-choice options.** No open-ended or vague follow-ups are allowed.
- Keep responses clear and concise, but maintain the warm, jolly Santa personality.
- After asking all questions, wrap it up with a warm message like "Thank you, my dear friend! I'll make sure to prepare something special for Christmas! Ho ho ho! 🎄"
- Use festive emojis sparingly (🎅🎄❄️)
"""

# Modify the generate_response function to include budget
def generate_response(messages, budget=None):
    """Generate a single response from the elf assistant"""
    # If Langfuse is available, wrap this function
    if observe:
        return _generate_response_with_observability(messages, budget)
    return _generate_response_impl(messages, budget)

# Split the implementation
@observe() if observe else lambda: None  # This makes the decorator optional
def _generate_response_with_observability(messages, budget):
    return _generate_response_impl(messages, budget)

def _generate_response_impl(messages, budget):
    """Implementation of response generation"""
    # Add budget to system prompt if available
    system_messages = [{"role": "system", "content": prompt}]
    if budget:
        budget_prompt = f"""
        IMPORTANT: The gift budget is {budget}. 
        - Ensure all questions consider this budget range
        - Adjust options to be appropriate for this price range
        - Focus on value-oriented questions for lower budgets
        - Consider luxury preferences for higher budgets
        """
        system_messages.append({"role": "system", "content": budget_prompt})
    
    system_messages.append({"role": "system", "content": "Remember to structure your response with all XML tags: <covered_questions>, <remaining_questions>, <thinking>, <question>, and <multiple_choice_options>. This is crucial for tracking conversation progress."})

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            *system_messages,
            *messages
        ],
        temperature=0.3,
        max_tokens=1000,
        n=1
    )
    
    content = response.choices[0].message.content
    if "<question>" in content and "<multiple_choice_options>" in content:
        parts = content.split("<question>")
        question = parts[-1].split("</question>")[0].strip()
        
        options_parts = content.split("<multiple_choice_options>")
        options_raw = options_parts[-1].split("</multiple_choice_options>")[0]
        options_lines = options_raw.split('\n')
        cleaned_options = '\n'.join(line.strip() for line in options_lines if line.strip())
        return f"{question}\n{cleaned_options}"
    else:
        logging.error(f"""
        ⚠️ CRITICAL XML STRUCTURE ERROR ⚠️
        Missing required XML tags! Expected both <question> and <multiple_choice_options>
        Found tags: {[tag for tag in ['<question>', '<multiple_choice_options>'] if tag in content]}
        Full content: {content}
        """)
        return content

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
    try:
        return generate_response(messages, budget)
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
                {suggestion}
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
        page_title="Santa's Helper Elf",
        page_icon="🎁",
        layout="centered"
    )

    # Title and description
    st.title("🎄 Chat with Santa")
    st.markdown("""
    Ho ho ho! Merry Christmas! 🎅✨

    I'm Santa Claus, and I'm so happy you're here! Your friend has asked for my help in choosing a special Christmas gift for you.

    Let's have a jolly chat so I can learn more about you and prepare something wonderful for Christmas! 

    **Note:** You can finish our chat at any time by clicking the "Enough chatting. Send to Gift Production! 🎅🎁" button.
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

    # Modify the "Finished!" button handler
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Enough chatting. Send to Gift Production! 🎅🎁"):
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
                        st.success("Ho ho ho! Your chat has been sent to Santa! 🎄✨")
                        st.code(full_result_url, language=None)
                        st.info("Share this link with your friend to see Santa's gift suggestions! 🎁")
                    else:
                        logging.error("Failed to generate result link - returned None")
                        st.error("Oh no! Something went wrong saving your chat. Please try again! 🎅")
                except Exception as e:
                    logging.error(f"Error saving chat: {str(e)}", exc_info=True)
                    st.error(f"Oh no! Something went wrong saving your chat: {str(e)}")
            else:
                st.warning("There's nothing to send to Santa yet! Have a chat with the elf first! 🎅")

    with col2:
        if st.button("Restart Chat 🔄"):
            st.session_state.messages = []
            st.rerun()

else:
    # Default page - Link generation
    st.set_page_config(
        page_title="Santa's Secret Gift Helper",
        page_icon="🎁",
        layout="centered"
    )
    st.title("🎄 Santa's Christmas Gift Helper")
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
