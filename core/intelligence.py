import os
import logging
import google.generativeai as genai
from core.personality import SYSTEM_PROMPT, ONBOARDING_PROMPT
from tools.calendar_tool import list_upcoming_events, add_calendar_event
from tools.search_tool import web_search

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Define tools
tools = [list_upcoming_events, add_calendar_event, web_search]

model = genai.GenerativeModel(
    'gemini-1.5-flash',
    tools=tools
)
extract_model = genai.GenerativeModel('gemini-1.5-flash')

def get_ai_response(message, memories, is_onboarding=False, image=None):
    try:
        context = "\n".join([f"- {m}" for m in memories])
        
        prompt = SYSTEM_PROMPT
        if is_onboarding:
            prompt = ONBOARDING_PROMPT
            
        full_system_message = f"{prompt}\n\nFacts I remember about you:\n{context}"

        content_parts = [f"System Instructions: {full_system_message}\n\nUser Message: {message or 'Look at this image.'}"]
        if image:
            content_parts.append(image)

        # Use a chat session for automatic function calling
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(content_parts)
        
        return response.text
    except FileNotFoundError as e:
        return f"Elijah: I'd love to help with your calendar, but I'm missing my credentials. {str(e)}"
    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        return f"Elijah: Sorry, I had trouble thinking. (Error: {e})"

def detect_and_save_facts(user_message, ai_response, memory_manager):
    """Uses LLM to extract potential facts to save from the conversation."""
    if not user_message:
        return
        
    try:
        extraction_prompt = f"""Analyze the following exchange and extract any NEW personal facts, habits, or goals about the user.
Format each fact as a single sentence. If no new facts, return 'NONE'.

User: {user_message}
Elijah: {ai_response}
"""
        response = extract_model.generate_content(f"System: You are a data extraction assistant. Extract personal facts only.\n\n{extraction_prompt}")
        
        facts_text = response.text.strip()
        if "NONE" not in facts_text.upper():
            for fact in facts_text.split("\n"):
                if fact.strip():
                    memory_manager.add_memory(fact.strip())
    except Exception as e:
        logging.error(f"Error extracting facts: {e}")
