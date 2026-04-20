# Lucio Phase 2: Intelligence and Memory Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give Lucio the ability to "think" using an LLM and "remember" facts about the user using a local vector database (ChromaDB).

**Architecture:**
- **LLM:** OpenAI GPT-4o for reasoning and natural conversation.
- **Memory:** ChromaDB (persistent local storage) to store "Memory Snippets" (facts, habits, goals).
- **RAG Loop:** For each message, Lucio will:
    1. Retrieve relevant memories from ChromaDB.
    2. Combine memories with the current chat history.
    3. Generate a response using the LLM.
    4. Detect if any new facts should be saved to memory.

**Tech Stack:** Python 3.12, `openai`, `chromadb`, `python-dotenv`.

---

### Task 1: Intelligence Setup (LLM Integration)

**Files:**
- Modify: `requirements.txt`
- Modify: `.env` (template)
- Modify: `lucio.py`

**Step 1: Add openai to requirements.txt**
Add `openai` to the file.

**Step 2: Update .env template**
Add `OPENAI_API_KEY=your_openai_api_key_here`.

**Step 3: Update lucio.py with LLM logic**
Implement a method `get_ai_response(message, context)` that calls the OpenAI API.

**Step 4: Commit**
```bash
git add requirements.txt .env lucio.py
git commit -m "feat: integrate OpenAI for Lucio's brain"
```

---

### Task 2: Persistent Local Memory (ChromaDB)

**Files:**
- Modify: `requirements.txt`
- Create: `memory.py`
- Modify: `lucio.py`

**Step 1: Add chromadb to requirements.txt**
Add `chromadb` and `pysqlite3-binary` (for Linux/server compatibility if needed).

**Step 2: Implement MemoryManager in memory.py**
Create a class that handles:
- `add_memory(text, metadata)`: Saves a fact.
- `search_memories(query_text, n_results=3)`: Retrieves relevant facts.

**Step 3: Integrate Memory into lucio.py**
Initialize `MemoryManager` in `Lucio` class.
In `on_message`, query memory before calling the LLM.

**Step 4: Commit**
```bash
git add requirements.txt memory.py lucio.py
git commit -m "feat: add ChromaDB local memory system"
```

---

### Task 3: Personality & Onboarding

**Files:**
- Modify: `lucio.py`
- Create: `personality.py`

**Step 1: Define Personality Prompt**
In `personality.py`, create a `SYSTEM_PROMPT` that defines Lucio as a proactive, friendly, and smart personal assistant.

**Step 2: Implement Onboarding Logic**
In `lucio.py`, check if the user is known (e.g., if any memories exist). If not, trigger a "First Contact" introduction.

**Step 3: Final Verification**
Run `lucio.py` (simulated or with keys) to ensure it uses memories and maintains personality.

**Step 4: Commit**
```bash
git add lucio.py personality.py
git commit -m "feat: add personality and onboarding routine"
```
