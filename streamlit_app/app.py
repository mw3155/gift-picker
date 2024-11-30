import streamlit as st
from data_store import (
    generate_chat_link,
    save_chat_and_generate_result_link,
    get_gift_suggestions,
)

# Routing logic
query_params = st.query_params

if "link_a" in query_params:
    # User2's Chat Page
    link_a = query_params["link_a"]
    st.title("Answer a Few Questions")
    
    # Predefined questions
    questions = [
        "What is your favorite hobby?",
        "What is something you've always wanted?",
        "Do you prefer practical or sentimental gifts?",
    ]
    
    responses = []
    for question in questions:
        response = st.text_input(question, key=question)
        if response:
            responses.append(response)
    
    if len(responses) == len(questions):
        if st.button("Submit"):
            link_b = save_chat_and_generate_result_link(link_a, responses)
            if link_b:
                st.success("Chat completed!")
                st.write(f"Share this link with User1: [View Suggestions](?link_b={link_b})")
            else:
                st.error("Invalid link!")
else:
    # Check if User1 is viewing suggestions
    if "link_b" in query_params:
        link_b = query_params["link_b"]
        st.title("Gift Suggestions")
        suggestions = get_gift_suggestions(link_b)
        if suggestions:
            st.write("Here are some gift ideas based on the answers:")
            for suggestion in suggestions:
                st.write(f"- {suggestion}")
        else:
            st.error("Invalid link!")
    else:
        # User1 generates Link A
        st.title("Generate a Chat Link")
        if st.button("Generate Link"):
            link_a = generate_chat_link()
            st.success("Link generated!")
            st.write(f"Share this link with User2: [Start Chat](?link_a={link_a})")
