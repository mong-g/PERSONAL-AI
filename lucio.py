import os
import json
from dotenv import load_dotenv

load_dotenv()

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
            
            # Echo the message back (Phase 1)
            # We will check if the sender is the authorized user (you)
            authorized_user = os.getenv("USER_FB_ID")
            if author_id == authorized_user:
                self.send_message(f"Lucio: You said '{message}'", thread_id=thread_id, thread_type=thread_type)
            else:
                print(f"Unauthorized message from {author_id}")

    with open(app_state_path, 'r') as f:
        app_state = json.load(f)

    bot = Lucio(app_state=app_state)
    print("Lucio is online and listening...")
    bot.listen()

if __name__ == "__main__":
    main()
