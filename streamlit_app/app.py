import logging
import streamlit as st
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Initialize OpenAI client
client = openai.OpenAI()  # Make sure to set OPENAI_API_KEY in your environment variables

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
- Do not go too deep into one topic, it should be a surprise! Just a simple Q and A.
- You can ask some unrelated questions, to make it more mysterious.

### 4. Topics to Cover:
Ask about 5-7 of the following areas:
- Hobbies or activities you enjoy.
- Small luxury or treat that always makes you happy.
- Prefer practical gifts or something more fun and surprising.
- Favorite way to relax or unwind.
- Something you’ve always wanted but never got around to buying for yourself.
- Age group.

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

### **Elf’s Code of Conduct:**
1. **Strictly avoid open-ended questions**—each question must have clear numbered options.  
2. **Do not suggest specific gifts.** Only Santa can do that.  
3. **Focus on structured, concise questions** that help gather a variety of information.

Santa is counting on you to stick to your role as a helper. If you stray from these rules, the gathered information won’t be usable!
"""

validation_prompt = """
You are a validator that checks if a response contains proper multiple choice questions and maintains appropriate question depth.
Your task is to check if the latest response is appropriate given the ENTIRE conversation history.

Requirements:
- Must contain a clear question with numbered options (at least 2)
- Must maintain a festive, elf-like tone
- Questions should stay high-level and not dig too deep into specifics
- Questions should vary in topic and not fixate on one area
- Questions should be general enough to maintain gift surprise
- If a topic was already discussed, new questions should not dig deeper into it

When analyzing the conversation:
1. Look at previous questions asked by the elf
2. Check if the current question is exploring a topic that was already covered
3. Ensure questions are moving across different topics
4. Verify that follow-up questions aren't making previous topics more specific

Examples of BAD patterns:
- First question: "What hobbies do you enjoy?"
- Later question: "Which specific craft supplies do you prefer?" (TOO DEEP into hobbies)
- Multiple questions about the same topic area

Examples of GOOD patterns:
- First question: "What activities make you smile?"
- Later question: "How do you prefer to relax?" (DIFFERENT topic)
- Questions that explore various aspects of preferences

Return ONLY one of these:
- "VALID" if the response meets all requirements
- "INVALID because [specific reason]" if it doesn't meet requirements (e.g., "INVALID because this is the third question about hobbies")

Do not suggest fixes or provide new text. Only validate and explain if invalid.
"""

refinement_prompt = """
You are still the same cheerful elf, but you need to fix your previous response based on the feedback.
Keep your magical and festive tone.
Make sure to maintain consistency with previous interactions while fixing the issue.
Do not say sorry or anything else, just fix the response. The user will not see the previous failure.
"""

def get_ai_response(messages):
    """Get response from OpenAI API with LLM-based multiple choice validation"""
    logging.info(f"START of get_ai_response, len(messages): {len(messages)}")
    try:
        # Get initial response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                *messages
            ],
            temperature=0.1,
            max_tokens=1000,    
        )
        initial_response = response.choices[0].message.content

        # Validate response using LLM - now including message history
        validation_messages = [
            {"role": "system", "content": validation_prompt},
            {"role": "user", "content": "Here is the conversation history and latest response to validate:"}
        ]
        
        # Add conversation history
        for msg in messages:
            if msg["role"] == "assistant":
                validation_messages.append({"role": "user", "content": f"Previous elf question: {msg['content']}"})
            elif msg["role"] == "user":
                validation_messages.append({"role": "user", "content": f"User answer: {msg['content']}"})
        
        # Add the latest response to validate
        validation_messages.append({"role": "user", "content": f"Latest elf response to validate: {initial_response}"})
        
        validation = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=validation_messages,
            temperature=0.1,
            max_tokens=1000,
        )
        validation_result = validation.choices[0].message.content
        logging.info(f"Validation result: {validation_result}")
        if validation_result == "VALID":
            return initial_response
        else:
            # Get refined response from the elf
            refined = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt + "\n" + refinement_prompt},
                    *messages,
                    {"role": "assistant", "content": initial_response},
                    {"role": "system", "content": f"Please fix your response. {validation_result}"}
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            logging.info(f"Refined response: {refined.choices[0].message.content}") 
            return refined.choices[0].message.content

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
