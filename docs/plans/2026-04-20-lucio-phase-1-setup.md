# Lucio Phase 1: Setup & Echo Bot Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish a stable Messenger connection and implement a basic "Echo Bot" that responds to the user's messages as Lucio.

**Architecture:** Use the `fbapy` library to puppet a personal Facebook account. The bot will run an event loop (`listen`) and respond to incoming messages. Credentials will be managed via `app_state.json` (cookies) for security and stability.

**Tech Stack:** Python 3.12, `fbapy`, `python-dotenv`.

---

### Task 1: Environment Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env` (template)
- Create: `.gitignore` (update)

**Step 1: Create requirements.txt**

```text
fbapy
python-dotenv
```

**Step 2: Update .gitignore**

Add:
```text
.env
app_state.json
__pycache__/
*.pyc
.venv/
```

**Step 3: Create .env template**

```text
# For template reference
FACEBOOK_APP_STATE_PATH=app_state.json
USER_FB_ID=your_facebook_user_id_here
```

**Step 4: Run environment setup**

Run: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
Expected: Successful installation of dependencies.

**Step 5: Commit**

```bash
git add requirements.txt .gitignore .env
git commit -m "chore: initial environment setup for Lucio"
```

---

### Task 2: Basic Echo Bot Implementation

**Files:**
- Create: `lucio.py`

**Step 1: Write the failing test (Manual verification)**

Since `fbapy` requires a live login, we will verify with a script that attempts to initialize the client and prints a success message.

**Step 2: Implement the Lucio Client**

```python
import os
import json
from dotenv import load_dotenv
from fbapy import Client

load_dotenv()

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

def main():
    app_state_path = os.getenv("FACEBOOK_APP_STATE_PATH", "app_state.json")
    
    if not os.path.exists(app_state_path):
        print(f"Error: {app_state_path} not found. Please provide session cookies.")
        return

    with open(app_state_path, 'r') as f:
        app_state = json.load(f)

    bot = Lucio(app_state=app_state)
    print("Lucio is online and listening...")
    bot.listen()

if __name__ == "__main__":
    main()
```

**Step 3: Commit**

```bash
git add lucio.py
git commit -m "feat: implement basic echo bot using fbapy"
```

---

### Task 3: Verification & Onboarding Preparation

**Step 1: Verify the bot starts**

Run: `python lucio.py` (Note: This will fail until `app_state.json` is provided by the user).
Expected: Output showing "Error: app_state.json not found" or successful "Lucio is online".

**Step 2: Instructions for User**

Create a README.md with instructions on how to export `app_state.json`.

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add instructions for app_state.json export"
```
