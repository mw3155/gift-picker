import os
import openai
import logging
from typing import Optional, List, Dict

def generate_santa_response(messages: List[Dict], budget: Optional[str] = None) -> Optional[str]:
    """Generate a single response from Santa Claus"""
    try:
        # Add budget to system prompt if available
        system_messages = [{"role": "system", "content": SANTA_PROMPT}]
        if budget:
            budget_prompt = f"""
            IMPORTANT: The gift budget is {budget}. 
            - Ensure all questions consider this budget range
            - Adjust options to be appropriate for this price range
            - Focus on value-oriented questions for lower budgets
            - Consider luxury preferences for higher budgets
            """
            system_messages.append({"role": "system", "content": budget_prompt})
        
        system_messages.append({
            "role": "system", 
            "content": "Remember to structure your response with all XML tags: <covered_questions>, <remaining_questions>, <thinking>, <question>, and <multiple_choice_options>. This is crucial for tracking conversation progress."
        })

        response = openai.chat.completions.create(
            model="GS-GPT4o-global",  # Using Azure model
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
            
    except Exception as e:
        logging.error(f"Error generating Santa response: {e}")
        return None

def generate_gift_suggestions(messages: List[Dict], budget: Optional[str] = None) -> List[str]:
    """Generate gift ideas based on chat messages using GPT"""
    try:
        # Format the chat history for better context
        chat_summary = format_chat_summary(messages)
        
        response = openai.chat.completions.create(
            model="GS-GPT4o-global",  # Using Azure model
            messages=[
                {"role": "system", "content": GIFT_SUGGESTIONS_PROMPT + (f"\n\nBudget range: {budget}" if budget else "")},
                {"role": "user", "content": chat_summary}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        suggestions = []
        
        # Split content into individual suggestions
        raw_suggestions = content.split("🎁")
        for suggestion in raw_suggestions:
            if not suggestion.strip():
                continue
                
            # Extract suggestion and keywords
            if "<keywords>" in suggestion and "</keywords>" in suggestion:
                parts = suggestion.split("<keywords>")
                suggestion_text = parts[0].strip()
                keywords = parts[1].split("</keywords>")[0].strip()
                suggestions.append({
                    "text": f"🎁 {suggestion_text}",
                    "keywords": keywords
                })
            else:
                suggestions.append({
                    "text": f"🎁 {suggestion.strip()}",
                    "keywords": ""
                })
        return suggestions
        
    except Exception as e:
        logging.error(f"Error generating gift ideas: {e}")
        return []

def format_chat_summary(messages: List[Dict]) -> str:
    """Format chat history for GPT context"""
    chat_summary = "Chat summary:\n"
    # Convert messages to list to use indexing
    messages_list = list(messages)
    # Exclude last message if it's from assistant
    if messages_list and messages_list[-1]["role"] == "assistant":
        messages_list = messages_list[:-1]
        
    for msg in messages_list:
        if msg["role"] == "assistant":
            chat_summary += f"Santa asked: {msg['content']}\n"
        elif msg["role"] == "user":
            chat_summary += f"They answered: {msg['content']}\n"
    
    return chat_summary

# Constants
SANTA_PROMPT = """You are Santa Claus himself, speaking directly with someone to learn about their interests and preferences.
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

GIFT_SUGGESTIONS_PROMPT = """You are Santa's gift suggestion expert. Based on the chat conversation between Santa and the gift recipient, suggest 5 specific gift ideas.

Guidelines:
1. Each suggestion should be specific and actionable (e.g., "A high-quality yoga mat with carrying strap" rather than just "yoga equipment")
2. Include a brief reason why this gift would be good based on their responses
3. Keep suggestions within the specified budget range
4. Keep the festive tone but be practical
5. Format each suggestion on a new line starting with "🎁"
6. For each suggestion, include relevant search keywords in <keywords> tags

Example format:
🎁 A premium yoga mat with carrying strap and alignment lines - Perfect for their daily meditation and yoga practice
<keywords>premium yoga mat alignment lines</keywords>

🎁 A gourmet coffee bean subscription box - They mentioned loving artisanal coffee as their daily luxury
<keywords>gourmet coffee subscription box monthly</keywords>
""" 