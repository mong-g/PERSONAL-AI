import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from memory import MemoryManager
from personality import SYSTEM_PROMPT, ONBOARDING_PROMPT

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
memory_manager = MemoryManager()

def get_ai_response(message, memories, is_onboarding=False):
    try:
        context = "\n".join([f"- {m}" for m in memories])
        
        prompt = SYSTEM_PROMPT
        if is_onboarding:
            prompt = ONBOARDING_PROMPT
            
        full_system_message = f"{prompt}\n\nFacts I remember about you:\n{context}"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": full_system_message},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return f"Lucio: Sorry, I had trouble thinking. (Error: {e})"

def detect_and_save_facts(user_message, ai_response):
    """Uses LLM to extract potential facts to save from the conversation."""
    try:
        extraction_prompt = f"""Analyze the following exchange and extract any NEW personal facts, habits, or goals about the user.
Format each fact as a single sentence. If no new facts, return 'NONE'.

User: {user_message}
Lucio: {ai_response}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Use a cheaper model for extraction
            messages=[
                {"role": "system", "content": "You are a data extraction assistant. Extract personal facts only."},
                {"role": "user", "content": extraction_prompt}
            ]
        )
        facts_text = response.choices[0].message.content.strip()
        if facts_text != "NONE":
            for fact in facts_text.split("\n"):
                if fact.strip():
                    memory_manager.add_memory(fact.strip())
    except Exception as e:
        print(f"Error extracting facts: {e}")

def main():
    app_state_path = os.getenv("FACEBOOK_APP_STATE_PATH", "app_state.json")
    
    if not os.path.exists(app_state_path):
        print(f"Error: {app_state_path} not found. Please provide session cookies.")
        return

    from fbapy import Client

    class Lucio(Client):
        def on_message(self, mid, author_id, message, thread_id, thread_type, ts, metadata):
            if author_id == self.uid:
                return

            print(f"Received from {author_id}: {message}")
            
            authorized_user = os.getenv("USER_FB_ID")
            if author_id == authorized_user:
                # 1. Check for onboarding
                is_onboarding = memory_manager.collection.count() == 0
                
                # 2. Retrieve memories
                memories = memory_manager.search_memories(message)
                
                # 3. Get AI response
                ai_response = get_ai_response(message, memories, is_onboarding)
                
                # 4. Send response
                self.send_message(ai_response, thread_id=thread_id, thread_type=thread_type)
                
                # 5. Background: Detect and save facts
                detect_and_save_facts(message, ai_response)
            else:
                print(f"Unauthorized message from {author_id}")

    with open(app_state_path, 'r') as f:
        app_state = json.load(f)

    bot = Lucio(app_state=app_state)
    print("Lucio is online and listening...")
    bot.listen()

if __name__ == "__main__":
    main()
