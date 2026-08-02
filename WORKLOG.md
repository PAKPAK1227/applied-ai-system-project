# PawPal+ — Worklog

A plain-language running log of what we changed and why, so anyone can read this
file and explain what PawPal+ does and how it works at a high level.

## What PawPal+ is (in one paragraph)

PawPal+ is a small app for a busy pet owner. You tell it about your pets and the
care tasks each one needs (walks, feeding, meds, grooming…), how long each task
takes, and how important it is. You also tell it how many minutes of care time you
have today. The app then builds a sensible daily plan — fitting the most important
tasks into the time you have first — warns you about double-booked time slots, and
automatically re-creates daily/weekly chores after you check them off.

## How it's built (the two layers)

- **The "brain" — `pawpal_system.py`.** Plain Python, no UI. Four classes:
  - `Task` — one care activity (description, duration, priority, time, how often it repeats, done/not-done).
  - `Pet` — one animal that owns a list of its `Task`s.
  - `Owner` — you: your available minutes, preferences, and your list of `Pet`s.
  - `Scheduler` — the logic that reads the `Owner` and does the smart work: sorting,
    filtering, building the plan, detecting conflicts, and handling recurring tasks.
- **The "face" — `app.py`.** A Streamlit web UI that calls into the brain. It remembers
  your `Owner` between clicks using `st.session_state`.
- **Supporting files:** `main.py` (a terminal demo of the brain), `tests/test_pawpal.py`
  (13 automated tests), `diagrams/*.mmd` (class diagrams), and the docs (`README.md`,
  `reflection.md`, `ai_interactions.md`).

---

## Change log

### 2026-08-02 — Onboarding / baseline
- Read every file in the project to understand it fully.
- Confirmed the baseline is healthy: **all 13 tests pass** (`python3 -m pytest`).
- Noted `python` isn't on PATH here — use `python3`.
- Set up this worklog and started tracking changes. No code changed yet.

### 2026-08-02 — Professional folder structure
- Created an **`assets/`** folder — the dedicated home for system architecture images
  (e.g. a PNG exported from the diagram). Added a `.gitkeep` so Git tracks the empty
  folder until real images land there.
- Added **`diagrams/architecture.mmd`** — the required Mermaid *source* file for the
  system architecture diagram. It's the canonical class diagram (Owner → Pet → Task,
  with the Scheduler reading the Owner) and matches `pawpal_system.py` exactly. This is
  what graders look for; a PNG alone is not sufficient.
- Left the existing `diagrams/uml.mmd` (early draft) and `diagrams/uml_final.mmd`
  (final class diagram) in place for history.

### 2026-08-02 — Added the AI feature: a RAG pet-care advisor
This is the big one — it gives PawPal+ a real AI capability.

**What we added, in plain terms:** a "PawPal Advisor" that gives smart, personalized
pet-care advice. When you ask it about a pet, it first **looks things up** in a small
library of real pet-care notes, then a **real AI model uses those notes** (plus your pet's
actual tasks and how much time you have) to write advice for the day. That "look it up, then
answer using what you found" pattern is called **RAG (Retrieval-Augmented Generation)** —
the required advanced AI feature.

**The pieces we built:**
- **`knowledge/`** — the library the AI reads from: three markdown files of pet-care
  guidelines (`dogs.md`, `cats.md`, `general.md`), split into labelled sections.
- **`pawpal_ai.py`** — the AI layer, in three parts:
  1. **Retriever** — searches the knowledge files and returns the few most relevant notes
     for the pet in question (simple, transparent keyword matching — no API key needed).
  2. **Generator** — sends the retrieved notes + the pet's schedule to a language model.
     It tries three options in order so it works for anyone: **Anthropic API** (if a key is
     set) → **free local Ollama model** (our demo path) → **offline template** (a safety net
     that still shows the retrieved notes if no model is running).
  3. **Advisor** — ties retrieval + generation together and returns the advice, which notes
     it used, and which backend answered.
- **`app.py`** — added a "🤖 PawPal Advisor" panel: pick a pet, click a button, read the
  advice. It shows which model answered and (in an expander) which guidelines were used, so
  it's clear the advice is grounded in real notes, not made up.
- **Logging & guardrails** — every lookup and model call is written to `pawpal.log`, and all
  model calls have timeouts + error handling so a missing/slow model never crashes the app.
- **`tests/test_pawpal_ai.py`** — 8 new tests for the AI layer (retrieval accuracy, the
  fallback chain, and safe/grounded behavior). They run offline, so no key or model needed.
- **`diagrams/architecture.mmd`** — rewrote it as a **system data-flow diagram** (input →
  process → output) showing the scheduler, the RAG retriever/generator/fallback, the log,
  and where the human and the automated tests check the AI. The class diagram now lives in
  `diagrams/uml_final.mmd`.
- Docs updated: README (new "AI Feature" section + setup steps for Ollama/API + testing),
  `reflection.md` (new section 6 on the RAG feature), `.gitignore` (ignore `pawpal.log`).

**Setup we ran on this machine:** installed Ollama via Homebrew, started the local server,
and pulled the `llama3.2` model (~2 GB). No API key or payment involved.

**Verified:** all **21 tests pass** (`python3.13 -m pytest`), and a live end-to-end advisor
call generated real, guideline-grounded advice through the local llama3.2 model.

**Note for this machine:** run tests with **`python3.13`** — the bare `python3` here is a
3.14 build without pytest installed.

