# Design Document: Lucio - Personal AI Assistant

**Date:** 2026-04-20
**Project:** Personal AI (Messenger)
**Status:** Validated

## Overview
Lucio is a proactive, personalized AI assistant that lives in the user's Messenger contact list as a friend. It uses a hybrid approach, combining cloud-based reasoning (LLM) with local memory (Vector Database) and proactive task management.

## Architecture
1.  **Interface (The Body):** 
    - Dedicated Facebook account for Lucio.
    - Python-based "Headless Messenger" bridge (e.g., `fbchat-v2` or similar).
    - Bypasses the 24-hour business messaging rule by acting as a personal account.
2.  **Orchestrator (The Nervous System):**
    - Python-based central logic.
    - Handles incoming messages, state management, and routing.
3.  **Brain (The Intelligence):**
    - Hybrid LLM: GPT-4o/Claude for reasoning.
    - Local privacy filtering for sensitive data.
4.  **Memory (The Second Brain):**
    - Short-term: Message history buffer.
    - Long-term: Local Vector Database (ChromaDB/FAISS) for "Memory Snippets" (facts, habits, goals).
5.  **Proactive Pulse (The Heartbeat):**
    - Background scheduler (`APScheduler`) for recurring and dynamic reminders.
    - Integration with Google Calendar API for schedule awareness.

## Key Features
- **Proactive Reminders:** Automated check-ins for meals, work, and scheduled tasks.
- **Deep Personalization:** Learns from conversations and stores facts in long-term memory.
- **Natural Interaction:** Acts as a friend in Messenger, with a custom personality.
- **Autonomous Scheduling:** Can read and modify the user's Google Calendar.

## Technical Stack
- **Language:** Python
- **LLM:** OpenAI/Anthropic API (Hybrid)
- **Database:** ChromaDB (Vector), SQLite (Structured)
- **APIs:** Messenger (Bridge), Google Calendar
- **Hosting:** Local machine or private server (24/7 uptime required for proactivity).

## Implementation Phases
1. **Setup:** Messenger bridge and basic chat echo.
2. **Intelligence:** Integration with LLM and Personality Prompting.
3. **Memory:** Local Vector Database implementation.
4. **Proactivity:** Background scheduler and Google Calendar integration.
5. **Onboarding:** "First Contact" routine for user introduction.
