import os
import logging
from google import genai
from google.genai import types
from core.personality import SYSTEM_PROMPT, ONBOARDING_PROMPT
from tools.calendar_tool import list_upcoming_events, add_calendar_event
from tools.search_tool import web_search

# Initialize new 2026 Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Define tools
tools = [list_upcoming_events, add_calendar_event, web_search]

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

        # 2026 SDK Syntax: Automatic function calling with generate_content
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=content_parts,
            config=types.GenerateContentConfig(
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
            )
        )
        
        return response.text
    except FileNotFoundError as e:
        return f"Elijah: I'd love to help with your calendar, but I'm missing my credentials. {str(e)}"
    except Exception as e:
        logging.error(f"Error calling Gemini 2.0: {e}")
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
        # Using stable 1.5 alias for extraction
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest',
            contents=[f"System: You are a data extraction assistant. Extract personal facts only.\n\n{extraction_prompt}"]
        )
        
        facts_text = response.text.strip()
        if "NONE" not in facts_text.upper():
            for fact in facts_text.split("\n"):
                if fact.strip():
                    memory_manager.add_memory(fact.strip())
    except Exception as e:
        logging.error(f"Error extracting facts: {e}")
