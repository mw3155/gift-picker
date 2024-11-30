import logging
import streamlit as st
import openai  # Change to direct import
import os
from datetime import datetime
from data_store import generate_chat_link, save_chat_and_generate_result_link, get_gift_suggestions, is_valid_email

# Configure base URL
BASE_URL = os.getenv("BASE_URL", "https://gift-picker.streamlit.app")

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

prompt = """
You are one of Santa's trusted elves. 
Your task is to gather information about the user's preferences to help Santa choose the perfect gift. 
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
Write a single cheerful question (markdown formatting allowed)
</question>

<multiple-choice-options>
Write numbered options, one per line (markdown formatting allowed)
</multiple-choice-options>

IMPORTANT: 
- Use only the five XML tags shown above
- Simple markdown formatting is allowed (bold, italic, lists)
- Do not use HTML or nested XML tags
- Do not create any additional XML tags or sub-tags

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
Ho ho ho! To help Santa pick something just right, could you tell me your gender?
</question>

<multiple-choice-options>
1. Male
2. Female
3. Non-binary
4. Prefer not to say
</multiple-choice-options>

### 1. Objective:
Gather clear and concise information from the user by asking **only structured multiple-choice questions.** The information you collect will be reviewed by Santa, who will make the final decision about the gift.

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
Then wrap it up with a cheerful message.

### 3. Elf's Role and Restrictions:
- **You cannot suggest gifts or examples of gifts.** Only Santa can decide what the gift will be. Your role is purely information gathering.
- **You cannot ask open-ended questions.** Every question must have numbered multiple-choice options.
- **If you fail to follow these rules**, the information you gather will be considered incomplete, and Santa cannot use it.

### 4. Behavior Guidelines:
- Stay in character as a cheerful elf, keeping responses short and playful.
- Always ask **one question at a time** with numbered multiple-choice options for clarity.
- **Switch topics between questions** to keep the conversation engaging and gather a variety of information.
- Keep the tone festive but avoid excessive filler or unnecessary commentary.
- Do not go too deep into one topic (only 2-3 questions per topic), it should be a surprise! Just a simple Q and A.
- You can ask some unrelated questions, to make it more mysterious.

### 5. Topics to Cover:
You **must** ask about these 7 topics:
- Hobbies or activities you enjoy.
- Small luxury or treat that always makes you happy.
- Prefer practical gifts or something more fun and surprising.
- Favorite way to relax or unwind.
- Something you've always wanted but never got around to buying for yourself.
- Age group.
- Gender.

### 6. Formatting Rules:
- Every question must include **only numbered multiple-choice options.** No open-ended or vague follow-ups are allowed.
- Keep responses clear and concise. Avoid adding unnecessary comments or speculations.
- After asking all questions, wrap it up with a cheerful message like "I'll hurry back to the North Pole and share everything with Santa! *jingles bells excitedly* 🔔❄️ Have a magical day! 🎄"

### 7. Examples:
#### Correct:
- **Ho ho ho! What's your age group?**  
1. Under 18  
2. 18–25  
3. 26–40  
4. 41–60  
5. 60+  

#### Incorrect:
- "Great! You're in the 26–40 age group. What would you like to talk about or explore today? It could be anything from career advice, personal development, hobbies, or even current events!" (❌ Open-ended, vague, and not related to the task.)

#### Correct:
- **Ho ho ho! What's your favorite pastime or entertainment?**  
1. Sports or fitness  
2. Reading or writing  
3. Gaming or tech  
4. Cooking or baking  
5. Arts and crafts  

#### Incorrect:
- "Tell me about your hobbies or what you enjoy doing in your free time!" (Open-ended and unstructured.)

---

### **Elf's Code of Conduct:**
1. **Strictly avoid open-ended questions**—each question must have clear numbered options.  
2. **Do not suggest specific gifts.** Only Santa can do that.  
3. **Focus on structured, concise questions** that help gather a variety of information.

Santa is counting on you to stick to your role as a helper. If you stray from these rules, the gathered information won't be usable!
"""

# Modify the generate_response function
def generate_response(messages):
    """Generate a single response from the elf assistant"""
    # If Langfuse is available, wrap this function
    if observe:
        return _generate_response_with_observability(messages)
    return _generate_response_impl(messages)

# Split the implementation
@observe() if observe else lambda: None  # This makes the decorator optional
def _generate_response_with_observability(messages):
    return _generate_response_impl(messages)

def _generate_response_impl(messages):
    """Implementation of response generation"""
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "system", "content": "Remember to structure your response with all XML tags: <covered_questions>, <remaining_questions>, <thinking>, <question>, and <multiple-choice-options>. This is crucial for tracking conversation progress."},
            *messages
        ],
        temperature=0.3,
        max_tokens=1000,
        n=1
    )
    
    content = response.choices[0].message.content
    if "<question>" in content and "<multiple-choice-options>" in content:
        parts = content.split("<question>")
        question = parts[-1].split("</question>")[0].strip()
        
        options_parts = content.split("<multiple-choice-options>")
        options_raw = options_parts[-1].split("</multiple-choice-options>")[0]
        options_lines = options_raw.split('\n')
        cleaned_options = '\n'.join(line.strip() for line in options_lines if line.strip())
        return f"{question}\n{cleaned_options}"
    else:
        logging.error(f"""
        ⚠️ CRITICAL XML STRUCTURE ERROR ⚠️
        Missing required XML tags! Expected both <question> and <multiple-choice-options>
        Found tags: {[tag for tag in ['<question>', '<multiple-choice-options>'] if tag in content]}
        Full content: {content}
        """)
        return content

# Modify get_ai_response similarly
def get_ai_response(messages):
    """Get a single response from the OpenAI API"""
    if observe:
        return _get_ai_response_with_observability(messages)
    return _get_ai_response_impl(messages)

@observe() if observe else lambda: None
def _get_ai_response_with_observability(messages):
    return _get_ai_response_impl(messages)

def _get_ai_response_impl(messages):
    try:
        return generate_response(messages)
    except Exception as e:
        st.error("Oh candy canes! 🎄 Something went wrong in Santa's workshop. Could you try that again, please? *jingles bells hopefully* 🔔")
        logging.error(f"Error generating AI response: {e}")
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
    
    st.title("🎁 Santa's Gift Suggestions")
    suggestions = get_gift_suggestions(result_link)
    
    if suggestions:
        st.markdown("""
        Ho ho ho! 🎅✨
        
        Based on my chat with your special someone, here are some magical gift ideas I've carefully selected:
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
    st.title("🎄 Santa's Helper Elf")
    st.markdown("""
    Ho ho ho! 🎅✨

    I'm one of Santa's special gift-finding elves, spreading holiday cheer from the North Pole! 

    Your friend has asked for my magical help to find you the perfect present. Let's work together to make their gift-giving wishes come true! *sprinkles candy cane dust* ✨🎁

    Just answer my festive questions, and I'll use my elf expertise to help guide them to something wonderful!

    **Note:** You can send your answers to Santa at any time by clicking the "Finished! Send to Santa 🎅" button.
    """)

    # Initialize chat with AI's first message if chat is empty
    if len(st.session_state.messages) == 0:
        logging.info("Generating initial AI message...")
        initial_response = get_ai_response([])
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
            ai_response = get_ai_response(st.session_state.messages)
            
            if ai_response:
                message_placeholder.markdown(ai_response)
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
            else:
                logging.error("Failed to get AI response")

    # Modify the "Finished!" button handler
    if st.button("Finished! Send to Santa 🎅"):
        if len(st.session_state.messages) > 0:
            # Create submission record
            submission = {
                "timestamp": datetime.now().isoformat(),
                "conversation": st.session_state.messages
            }
            
            # Save to data store and get result link
            result_link = save_chat_and_generate_result_link(chat_link, st.session_state.messages)
            
            if result_link:
                full_result_url = f"{BASE_URL}?result={result_link}"
                st.success("Ho ho ho! Your chat has been sent to Santa! 🎄✨")
                st.code(full_result_url, language=None)
                st.info("Share this link with your friend to see Santa's gift suggestions! 🎁")
            else:
                st.error("Oh no! Something went wrong saving your chat. Please try again! 🎅")
        else:
            st.warning("There's nothing to send to Santa yet! Have a chat with the elf first! 🎅")

else:
    # Default page - Link generation
    st.set_page_config(
        page_title="Santa's Secret Gift Helper",
        page_icon="🎁",
        layout="centered"
    )
    st.title("🎄 Santa's Secret Gift Helper")
    st.markdown("""
    Ho ho ho! 🎅✨
    
    Want to find the perfect gift for someone special? Let Santa's elves help!
    
    1. Set your budget and contact details below
    2. Generate and share the magic link with the person you want to buy a gift for
    3. They'll chat with one of Santa's elves about their preferences
    4. You'll get gift suggestions based on their answers!
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
            st.info("""
            Share this link with the person you want to buy a gift for! 🎁
            
            We'll notify you at {email} when they complete the questionnaire.
            """)
