import streamlit as st
import openai
from datetime import datetime

# Initialize OpenAI client
client = openai.OpenAI()  # Make sure to set OPENAI_API_KEY in your environment variables

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

prompt = """
You are a helpful AI assistant specializing in Christmas gift suggestions. 
A friend wants to buy a gift for the user. But they need help finding the perfect gift.
You will chat with the friend to find out what the user likes and needs.
Ask questions and present numbered options for the friend to choose from to make it easy.
"""


def get_ai_response(messages):
    """Get response from OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                *messages
            ],
            temperature=0.0,
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error getting response from OpenAI: {str(e)}")
        return None

# Page config
st.set_page_config(
    page_title="Christmas Gift AI Assistant",
    page_icon="🎁",
    layout="centered"
)

# Title and description
st.title("🎄 Christmas Gift AI Assistant")
st.markdown("""
Your friend wants to buy a gift for YOU!

Answer the following questions to help them find the perfect gift.
""")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get and display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        response = get_ai_response(st.session_state.messages)
        
        if response:
            message_placeholder.write(response)
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

# Add a clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()
