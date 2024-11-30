import logging
import streamlit as st
from langfuse.decorators import observe
from langfuse.openai import openai  # OpenAI integration
from langfuse import Langfuse
import os
from datetime import datetime
import json
from data_store import generate_chat_link, save_chat_and_generate_result_link, get_gift_suggestions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_type = "openai"
openai.api_version = None  # Only needed for Azure
openai.api_base = "https://api.openai.com/v1"

# Initialize Langfuse
langfuse = Langfuse()  # Make sure to set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY

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

### 1. Objective:
Gather clear and concise information from the user by asking **only structured multiple-choice questions.** The information you collect will be reviewed by Santa, who will make the final decision about the gift.
Strategy: 
First ask one question for each of the 7 topics. 
Then go deeper into one topic, asking 2-3 questions about it.
Then wrap it up with a cheerful message like "I'll hurry back to the North Pole and share everything with Santa! *jingles bells excitedly* 🔔❄️ Have a magical day! 🎄"

### 2. Elf's Role and Restrictions:
- **You cannot suggest gifts or examples of gifts.** Only Santa can decide what the gift will be. Your role is purely information gathering.
- **You cannot ask open-ended questions.** Every question must have numbered multiple-choice options.
- **If you fail to follow these rules**, the information you gather will be considered incomplete, and Santa cannot use it.

### 3. Behavior Guidelines:
- Stay in character as a cheerful elf, keeping responses short and playful.
- Always ask **one question at a time** with numbered multiple-choice options for clarity.
- **Switch topics between questions** to keep the conversation engaging and gather a variety of information.
- Keep the tone festive but avoid excessive filler or unnecessary commentary.
- Do not go too deep into one topic (only 2-3 questions per topic), it should be a surprise! Just a simple Q and A.
- You can ask some unrelated questions, to make it more mysterious.

### 4. Topics to Cover:
You **must** ask about these 7 topics:
- Hobbies or activities you enjoy.
- Small luxury or treat that always makes you happy.
- Prefer practical gifts or something more fun and surprising.
- Favorite way to relax or unwind.
- Something you've always wanted but never got around to buying for yourself.
- Age group.
- Gender.

### 5. Formatting Rules:
- Every question must include **only numbered multiple-choice options.** No open-ended or vague follow-ups are allowed.
- Keep responses clear and concise. Avoid adding unnecessary comments or speculations.
- After asking all questions, wrap it up with a cheerful message like "I'll hurry back to the North Pole and share everything with Santa! *jingles bells excitedly* 🔔❄️ Have a magical day! 🎄"

### 6. Examples:
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

picker_prompt = """
You are a response picker that selects the best elf response from multiple candidates.
Analyze each response based on these criteria:

1. Question Quality (Most Important):
   - Clear multiple choice format
   - Appropriate number of options (2-5)
   - Options are distinct and meaningful
   - Options cover a good range of possibilities

2. Topic Selection (Also Important):
   - Stays high-level without going too specific
   - Appropriate for gift selection
   - Doesn't overlap with previous topics
   - Avoids follow-up questions on same topic

Review the conversation history and the candidate responses.
Return ONLY the number (1, 2, or 3) of the best response, followed by a brief reason.
Example: "2 - Best balance of distinct options and new topic area"
"""

@observe()
def generate_candidates(messages):
    """Generate multiple candidate responses"""
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            *messages
        ],
        temperature=0.3,
        max_tokens=1000,
        n=3
    )
    return [choice.message.content for choice in response.choices]

@observe()
def pick_best_response(messages, candidates):
    """Pick the best response from candidates"""
    picker_messages = [
        {"role": "system", "content": picker_prompt},
    ]
    if len(messages) > 0:
        picker_messages.append({"role": "user", "content": "Here is the conversation history:"}) 
    else:
        picker_messages.append({"role": "user", "content": "This is the first question."})  
    for msg in messages:
        if msg["role"] == "assistant":
            picker_messages.append({"role": "user", "content": f"Previous elf question: {msg['content']}"})
        elif msg["role"] == "user":
            picker_messages.append({"role": "user", "content": f"User answer: {msg['content']}"})
    
    picker_messages.append({"role": "user", "content": "Here are the candidate responses to choose from:"})
    for i, candidate in enumerate(candidates, 1):
        picker_messages.append({"role": "user", "content": f"Response {i}: {candidate}"})
    
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=picker_messages,
        temperature=0.0,
        max_tokens=1000
    )
    picker_result = response.choices[0].message.content
    chosen_index = int(picker_result.split()[0]) - 1
    return candidates[chosen_index], picker_result

@observe()
def get_ai_response(messages):
    """Get response from OpenAI API with multiple candidates and selection"""
    candidates = []
    chosen_response = ""
    try:
        # Generate candidates
        candidates = generate_candidates(messages)
        for i, candidate in enumerate(candidates, 1):
            logging.info(f"Candidate {i}:\n{candidate}")
        
        # Pick best response
        chosen_response, picker_result = pick_best_response(messages, candidates)
        logging.info(f"Picker result:\n{picker_result}")
        
        return chosen_response

    except Exception as e:
        if chosen_response:
            return chosen_response
        elif candidates:
            return candidates[0]
        else:
            st.error("Oh candy canes! 🎄 Something went wrong in Santa's workshop. Could you try that again, please? *jingles bells hopefully* 🔔")
        return None

# Get base URL from environment variable or use default
BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")

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
            <div style='background-color: #f0f8ff; padding: 15px; border-radius: 10px; margin: 10px 0;'>
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
    st.title("🎄 Santa's Secret Gift Helper")
    st.markdown("""
    Ho ho ho! 🎅✨
    
    Want to find the perfect gift for someone special? Let Santa's elves help!
    
    1. Generate a special link below
    2. Share it with the person you want to buy a gift for
    3. They'll chat with one of Santa's elves about their preferences
    4. You'll get gift suggestions based on their answers!
    """)
    
    if st.button("Generate Magic Link ✨"):
        new_link = generate_chat_link()
        full_url = f"{BASE_URL}?chat={new_link}"
        st.code(full_url, language=None)
        st.info("Share this link with the person you want to buy a gift for! 🎁")
