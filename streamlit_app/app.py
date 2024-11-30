import logging
import streamlit as st
from langfuse.decorators import observe
from langfuse.openai import openai  # OpenAI integration
from langfuse import Langfuse
import os

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

prompt = """
You are one of Santa's trusted elves. 
Your task is to gather information about the user's preferences to help Santa choose the perfect gift. 
**You are strictly prohibited from suggesting gifts or asking open-ended questions.**

### 1. Objective:
Gather clear and concise information from the user by asking **only structured multiple-choice questions.** The information you collect will be reviewed by Santa, who will make the final decision about the gift.

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
Ask about 5-7 of the following areas:
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
- After asking all questions, ask one last question, wrap it up by saying "And that's all I need to know! Ho ho ho! 🎅✨"

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
- "Tell me about your hobbies or what you enjoy doing in your free time!" (❌ Open-ended and unstructured.)

---

### **Elf's Code of Conduct:**
1. **Strictly avoid open-ended questions**—each question must have clear numbered options.  
2. **Do not suggest specific gifts.** Only Santa can do that.  
3. **Focus on structured, concise questions** that help gather a variety of information.

Santa is counting on you to stick to your role as a helper. If you stray from these rules, the gathered information won't be usable!
"""

validation_prompt = """
You are a validator that checks if a response contains proper multiple choice questions and maintains appropriate question depth.
Your task is to check if the latest response is appropriate given the ENTIRE conversation history.

Requirements:
- Must contain a clear question with numbered options (at least 2)
- Questions should stay high-level and not dig too deep into specifics (no more than 3 questions per topic)
- Questions should be general enough to maintain gift surprise
- If a topic was already discussed, new questions should not dig deeper into it

Examples of BAD patterns:
- First question: "What hobbies do you enjoy?"
- Second question: "For this hobby, ..." (still ok)
- Third question: "For this hobby, which specific craft supplies do you prefer?" (TOO SPECIFIC)

Examples of GOOD patterns:
- First question: "What activities make you smile?"
- Later question: "How do you prefer to relax?" (DIFFERENT topic)
- Questions that explore various aspects of preferences

Return ONLY one of these:
- "VALID" if the response meets all requirements
- "INVALID because [specific reason]" if it doesn't meet requirements (e.g., "INVALID because this is the fourth question about hobbies")

Do not suggest fixes or provide new text. Only validate and explain if invalid.
Do not be too strict, give some leeway.
"""

refinement_prompt = """
You are still the same cheerful elf, but you need to fix your previous response based on the feedback.
Keep your magical and festive tone.
Make sure to maintain consistency with previous interactions while fixing the issue.
Do not say sorry or anything else, just fix the response. The user will not see the previous failure.
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
   - Maintains good topic variety compared to previous questions
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
        model="gpt-4o-mini",
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
        model="gpt-4o-mini",
        messages=picker_messages,
        temperature=0.0,
        max_tokens=1000
    )
    picker_result = response.choices[0].message.content
    chosen_index = int(picker_result.split()[0]) - 1
    return candidates[chosen_index], picker_result

@observe()
def validate_response(messages, response_to_validate):
    """Validate the chosen response"""
    validation_messages = [
        {"role": "system", "content": validation_prompt},
        {"role": "user", "content": "Here is the conversation history and latest response to validate:"}
    ]
    
    for msg in messages:
        if msg["role"] == "assistant":
            validation_messages.append({"role": "user", "content": f"Previous elf question: {msg['content']}"})
        elif msg["role"] == "user":
            validation_messages.append({"role": "user", "content": f"User answer: {msg['content']}"})
    
    validation_messages.append({"role": "user", "content": f"Latest elf response to validate: {response_to_validate}"})
    
    validation = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=validation_messages,
        temperature=0.0,
        max_tokens=1000
    )
    return validation.choices[0].message.content

@observe()
def refine_response(messages, chosen_response, validation_result):
    """Refine the response if validation failed"""
    refined = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt + "\n" + refinement_prompt},
            *messages,
            {"role": "assistant", "content": chosen_response},
            {"role": "system", "content": f"Please fix your response. {validation_result}"}
        ],
        temperature=0.0,
        max_tokens=1000
    )
    return refined.choices[0].message.content

@observe()
def get_ai_response(messages):
    """Get response from OpenAI API with multiple candidates and selection"""
    try:
        # Generate candidates
        candidates = generate_candidates(messages)
        for i, candidate in enumerate(candidates, 1):
            logging.info(f"Candidate {i}:\n{candidate}")
        
        # Pick best response
        chosen_response, picker_result = pick_best_response(messages, candidates)
        logging.info(f"Picker result:\n{picker_result}")
        
        # Validate response
        validation_result = validate_response(messages, chosen_response)
        logging.info(f"Validation result:\n{validation_result}")
        
        if validation_result == "VALID":
            return chosen_response
        else:
            # Refine response
            refined_response = refine_response(messages, chosen_response, validation_result)
            logging.info(f"Refined response:\n{refined_response}")
            return refined_response

    except Exception as e:
        st.error(f"Error getting response from OpenAI: {str(e)}")
        return None

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
        response = get_ai_response(st.session_state.messages)
        
        if response:
            message_placeholder.markdown(response)
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            logging.error("Failed to get AI response")

# Add a clear chat button
if st.button("Clear Chat"):
    logging.info("Clearing chat history")
    st.session_state.messages = []
    st.rerun()
