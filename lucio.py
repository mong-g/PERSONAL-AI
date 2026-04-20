import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from memory import MemoryManager

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
memory_manager = MemoryManager()

def get_ai_response(message, memories):
    try:
        context = "\n".join([f"- {m}" for m in memories])
        system_message = f"""You are Lucio, a proactive and friendly personal AI assistant. 
Keep your responses concise and helpful.

Here are some facts I remember about you:
{context}

Use these facts to personalize your response if relevant."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return f"Lucio: Sorry, I had trouble thinking. (Error: {e})"

def main():
    app_state_path = os.getenv("FACEBOOK_APP_STATE_PATH", "app_state.json")
    
    if not os.path.exists(app_state_path):
        print(f"Error: {app_state_path} not found. Please provide session cookies.")
        return

    from fbapy import Client

    class Lucio(Client):
        def on_message(self, mid, author_id, message, thread_id, thread_type, ts, metadata):
            # Ignore messages sent by Lucio himself
            if author_id == self.uid:
                return

            print(f"Received from {author_id}: {message}")
            
            # Check if the sender is the authorized user (you)
            authorized_user = os.getenv("USER_FB_ID")
            if author_id == authorized_user:
                # 1. Retrieve memories
                memories = memory_manager.search_memories(message)
                
                # 2. Get AI response with context
                ai_response = get_ai_response(message, memories)
                
                # 3. Send response
                self.send_message(ai_response, thread_id=thread_id, thread_type=thread_type)
                
                # TODO: Detect and save new memories (Task 3)
            else:
                print(f"Unauthorized message from {author_id}")

    with open(app_state_path, 'r') as f:
        app_state = json.load(f)

    bot = Lucio(app_state=app_state)
    print("Lucio is online and listening...")
    bot.listen()

if __name__ == "__main__":
    main()
