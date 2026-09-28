# Social Media Engagement Agent - Repository Overview

## Short Description / Tagline
An AI-powered Social Media Engagement Assistant built with Hindsight Memory and Google Gemini. Maintains persistent memory across conversations, campaigns, past complaint resolutions, and brand guidelines to draft empathetic, context-aware responses with human-in-the-loop approval.

## Project Structure
- `backend/`: FastAPI backend and services.
  - `main.py`: FastAPI routes (`/api/posts`, `/api/draft`, `/api/scenario/before-after`, `/api/memories`, `/api/recall`).
  - `hindsight_client.py`: Hindsight Memory client (`retain`, `recall`, `reflect`) with offline mock fallback.
  - `gemini_agent.py`: Google Gemini integration for response drafting and reasoning.
- `frontend/`:
  - `streamlit_app.py`: Streamlit Dashboard featuring Triage Queue, Before/After Walkthrough, Brand Memory Manager, and Analytics.
  - `gradio_app.py`: Gradio App for fast interactive testing and judge evaluation.
- `data/`:
  - `seed_memories.json`: Initial Hindsight memory bank facts, directives, and observations.
  - `sample_posts.json`: Incoming social media post scenarios.
- `README.md`: Structured documentation with problem statement, architecture, quickstart, and metrics.
- `requirements.txt`: Python package dependencies.
