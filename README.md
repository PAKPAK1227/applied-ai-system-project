# 🐾 PawPal+ — An AI-Assisted Pet-Care Planner

PawPal+ helps a busy pet owner plan their day of pet care. You enter your pets and
their care tasks, say how much time you have, and the app builds a priority-first
daily schedule — then an **AI advisor** looks up real pet-care guidelines and uses
them to give specific, grounded advice for your pets and your time budget.

**Why it matters:** consistent pet care is mostly a scheduling-and-priorities problem
under a time constraint. PawPal+ pairs a transparent, deterministic scheduler with a
retrieval-grounded AI advisor, so the owner gets both a concrete plan *and* trustworthy,
source-backed guidance — without either piece being a black box.

---

## Original project (CodePath Modules 1–3)

**PawPal+** is my original CodePath project. In Modules 1–3 it was a plain
Python-plus-Streamlit app whose goal was to help a pet owner stay consistent with
care: model an owner, their pets, and each pet's tasks (duration, priority, time,
frequency), then generate a **priority-first daily schedule** that fits the owner's
available minutes, sort and filter tasks, detect same-time conflicts, and regenerate
recurring chores. This final submission keeps that scheduler intact and adds a new
**Retrieval-Augmented Generation (RAG) AI advisor** on top of it.

---

## ✨ What it does

**Deterministic scheduler** (`pawpal_system.py`)
- Models an `Owner` → many `Pet`s → many `Task`s.
- **Priority-first planning** (`build_plan`) fits tasks into the owner's available minutes, highest priority first.
- **Sort by time**, **filter** by pet/completion, **daily/weekly recurrence**, and **conflict warnings** for same-time bookings.

**RAG AI advisor** (`pawpal_ai.py`) — the AI feature
- **Retrieves** the most relevant pet-care guidelines from a local knowledge base (`knowledge/*.md`).
- **Generates** advice with a language model that uses those retrieved guidelines *plus* the pet's real tasks and the owner's time budget.
- Runs for anyone via a **3-tier fallback chain**: Anthropic API → local Ollama model → offline template.

---

## 🧭 Architecture Overview

The full system diagram is a Mermaid source file: [`diagrams/architecture.mmd`](diagrams/architecture.mmd)
(the class-level design is in [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd)).

The system has **two subsystems** behind one Streamlit UI, and data flows
input → process → output:

1. **Input** — the owner enters pets, tasks, and available minutes in the UI (`app.py`).
2. **Deterministic scheduler** — turns tasks + time budget into a schedule, agenda, and conflict warnings. Pure Python, no AI, fully testable.
3. **RAG advisor** — when the owner asks for advice on a pet:
   - the **Retriever** builds a query from the pet and its tasks and scores the knowledge-base chunks by keyword overlap, returning the top matches;
   - the **prompt builder** combines those retrieved guidelines with a summary of the pet's schedule;
   - the **generator** sends that to a model through the fallback chain (Anthropic → Ollama → offline template) and returns advice grounded in the retrieved notes.
4. **Output** — the UI shows the plan and the advice, including *which* backend answered and *which* guidelines were retrieved.
5. **Human + testing checkpoints** — the owner reviews the plan and advice and decides what to do (human-in-the-loop), and the pytest suite verifies both subsystems. Every retrieval and backend choice is written to `pawpal.log`.

---

## 🚀 Setup Instructions

### 1. Install the app

```bash
git clone https://github.com/PAKPAK1227/applied-ai-system-project.git
cd applied-ai-system-project

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Enable the AI advisor (choose one)

The scheduler and the RAG **retrieval** step need no extra setup. To get real AI
**generation**, enable one backend — the app auto-detects whichever is available and
falls back safely if none is:

**Option A — Local model with Ollama (recommended: free, no API key):**

```bash
brew install ollama            # macOS; see https://ollama.com for other platforms
ollama serve &                 # start the local model server
ollama pull llama3.2           # one-time ~2 GB model download
```

**Option B — Anthropic API (optional, paid, separate from a Claude.ai subscription):**

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Option C — Nothing:** the advisor still runs and returns the retrieved guidelines via
the offline fallback (no live model — weaker output, but never crashes).

### 3. Run it

```bash
streamlit run app.py           # the web app
python main.py                 # a terminal demo of the scheduler
python demo_ai.py              # a terminal demo of the RAG advisor + guardrail
python -m pytest               # the test suite (see Testing below)
```

Optional environment variables: `PAWPAL_OLLAMA_MODEL` (default `llama3.2`), `OLLAMA_HOST`
(default `http://localhost:11434`), `PAWPAL_ANTHROPIC_MODEL`, `PAWPAL_LLM_TIMEOUT`,
`PAWPAL_KNOWLEDGE_DIR`.

---

## 💬 Sample Interactions

Real outputs from the RAG advisor. Because language-model output varies between runs,
yours may differ in wording — but it will stay grounded in the same retrieved guidelines.

### Example 1 — Dog on a tight morning (local Ollama model)

**Input:** Biscuit (dog, Golden Retriever); 45 minutes available. Tasks: Morning walk
(30 min, high, 08:00), Feeding (10 min, high, 08:00), Grooming (40 min, medium, weekly).

**Retrieved guidelines:** `general.md # Prioritizing when time is short`, `dogs.md # Walking and exercise`, `dogs.md # Feeding`

**AI output:**
> • **Prioritize feeding and morning walk**: As high-priority tasks on a busy day, ensure Biscuit is fed at 08:00 (10 min) and the 30-min morning walk is completed before any other activities.
> • **Shorten grooming session**: Given the time constraint, consider shortening the 40-min grooming to 20–30 minutes so it still fits.
> • **Ensure adequate exercise**: For a high-energy breed like a Golden Retriever, an extra short play session (5–10 minutes) would be beneficial after the walk.
> • **Provide fresh water throughout the day**, including during and after meals.

### Example 2 — Cat with moderate time (local Ollama model)

**Input:** Whiskers (cat, Tabby); 60 minutes available. Tasks: Litter box (10 min, high,
07:30), Play session (15 min, low, 18:00).

**Retrieved guidelines:** `cats.md # Litter box care`, `general.md # Prioritizing when time is short`, `cats.md # Play and enrichment`

**AI output:**
> • **Prioritize litter box maintenance**: At 07:30, dedicate 10 minutes to scooping Whiskers' litter box — a high-priority task that affects her health and comfort.
> • **Fit in a short play session**: Even when time is limited, a ~10-minute session of active, hunting-style play meets Whiskers' enrichment needs.
> • **Keep any medication and feeding on schedule**: health-critical tasks come first on a busy day.
> • **Consider an extra litter box** in a quiet location (one per cat plus one extra).

### Example 3 — Graceful degradation (no model available → offline fallback)

**Input:** Biscuit (dog); 45 minutes; Morning walk (30 min, high). Ollama not running and no API key.

**AI output:**
> ⚠️ No live AI model is available, so here are the most relevant care guidelines retrieved for this pet (offline fallback):
> - **Prioritizing when time is short** — On a busy day, health-critical tasks come first: feeding, any medication, and toileting needs.
> - **Walking and exercise** — Most adult dogs need 30–60 minutes of walking per day, ideally split into two shorter walks.
> - **Consistency and routine** — Pets do best with predictable daily routines.
>
> Prioritize feeding, medication, and toileting first when time is short.

This shows the reliability guardrail: with no model reachable, the advisor still returns
the retrieved guidelines instead of erroring.

---

## 🧩 Design Decisions & Trade-offs

- **Two layers, one deterministic and one AI.** The scheduler stays pure Python so its
  behavior is predictable and fully testable; the AI advisor is additive. The retrieved
  guidelines and the live schedule actively shape the model's answer, so the AI is
  integrated into the app's logic rather than bolted on as a separate script.
- **RAG instead of a bare chatbot.** Grounding answers in a curated knowledge base keeps
  advice factual and lets the app show its sources. *Trade-off:* the advice is only as
  good as the notes in `knowledge/`; it deliberately won't answer beyond them.
- **Keyword retrieval, not embeddings.** A transparent bag-of-words overlap score is
  dependency-free, fast, and easy to test and explain. *Trade-off:* it can occasionally
  surface a loosely-related chunk (e.g., a cat feeding note for a dog query) and doesn't
  understand synonyms. For this small, well-tagged corpus that's an acceptable exchange
  for simplicity.
- **Local model first, with a fallback chain.** Defaulting to a free local Ollama model
  means the project runs reproducibly for anyone with no API key or cost, and upgrades to
  a hosted model by just setting a key — no code change. *Trade-off:* a small local model
  gives shorter, occasionally less-polished answers than a large hosted one.
- **Fail safe over fail loud.** Every model call has a timeout and error handling; if no
  model is reachable the advisor degrades to the offline fallback rather than crashing.
- **Exact-time conflict detection.** Conflicts are flagged on identical `HH:MM` start
  times, not overlapping durations — O(n), easy to reason about, and it covers the common
  "you double-booked 08:00" case. *Trade-off:* it won't catch a 30-minute task that
  overlaps a later one.

---

## 🧪 Testing & Reliability Summary

**One-line summary:** 21 of 21 automated tests pass; the scheduler logic is fully
covered, and the AI layer is verified for retrieval accuracy and safe fallback. The main
weakness is language-model non-determinism — wording varies between runs, and the small
local model sometimes adds a caveat slightly beyond the retrieved notes.

Reliability is enforced three ways:

1. **Automated tests** (`python -m pytest`, 21 tests):
   - *Scheduler* (`tests/test_pawpal.py`, 13): completion, adding tasks, time-sorting, filtering, daily/weekly recurrence, conflict detection, budget-aware planning, and empty-plan edge cases.
   - *RAG advisor* (`tests/test_pawpal_ai.py`, 8): retrieval ranks a relevant guideline first and rejects no-overlap queries; the fallback chain picks the right backend; offline advice stays grounded in the retrieved headings; the advisor never raises. These run offline with the model backends monkeypatched — no key or model required.
2. **Logging** — every retrieval and backend attempt is written to `pawpal.log`, so you can audit what was retrieved and which model answered.
3. **Error handling / guardrails** — all model calls are wrapped with timeouts and exception handling; failures degrade to the offline fallback (see Sample Interaction 3) instead of crashing.

**What worked:** retrieval reliably pulls the right guidelines, and the model grounds its
advice in them (the sample outputs even cite the guideline names). The fallback chain made
the app runnable end-to-end with no API key.
**What didn't (and what I learned):** LLM output isn't reproducible byte-for-byte, so the
tests assert on *structure and grounding* (backend chosen, sources present, headings
surfaced) rather than exact text — testing an AI feature means testing the pipeline's
behavior, not the prose.

---

## 🧾 Execution Evidence (reproducible, no video needed)

Real output captured by running the commands below. This demonstrates an end-to-end
system run, the AI (RAG) feature, and the reliability/guardrail behavior — each with clear
outputs. (Language-model wording varies between runs; the structure and grounding do not.)

### ✅ Reliability — automated tests

```text
$ python -m pytest
collected 21 items

tests/test_pawpal.py .............                                       [ 61%]
tests/test_pawpal_ai.py ........                                         [100%]

============================== 21 passed in 0.03s ==============================
```

### ✅ End-to-end run — deterministic scheduler (`python main.py`)

**Input:** owner "Sam", 120 min; two pets (Biscuit the dog, Whiskers the cat) with six
tasks added out of time order, two of them booked at the same 07:30 slot.

```text
$ python main.py
===========================================
Today's Schedule for Sam  (budget: 120 min)
===========================================
  08:00-08:05  Feeding           5 min  [high  ] Whiskers
  08:05-08:15  Feeding          10 min  [high  ] Biscuit
  08:15-08:45  Morning walk     30 min  [high  ] Biscuit
  08:45-08:55  Litter box       10 min  [medium] Whiskers
  08:55-09:35  Grooming         40 min  [medium] Biscuit
  09:35-10:00  Enrichment play  25 min  [low   ] Biscuit

Total care time: 120 min
Sorted 6 pending task(s) by priority. Scheduled 6 using 120 of 120 min; skipped 0 that did not fit.

Agenda sorted by time
---------------------
  07:30  Feeding
  07:30  Feeding
  08:00  Morning walk
  12:00  Grooming
  17:00  Enrichment play
  18:00  Litter box

Conflict check
--------------
  ⚠️  Conflict at 07:30: Feeding (Biscuit), Feeding (Whiskers)

Recurring tasks
---------------
  Before: Biscuit has 4 tasks; completing weekly 'Grooming'
  After:  Biscuit has 5 tasks; next 'Grooming' due 2026-08-09
```

### ✅ AI feature (RAG) + guardrail (`python demo_ai.py`)

Two live-model scenarios (retrieval → grounded generation), then the offline fallback
guardrail with every live backend forced off.

```text
$ python demo_ai.py

===== Scenario 1: dog, 45 minutes =====
INPUT: Biscuit — dog Golden Retriever; 45 min available
  task: Morning walk — 30 min, high priority, at 08:00, repeats daily
  task: Feeding — 10 min, high priority, at 08:00, repeats daily
  task: Grooming — 40 min, medium priority, at 12:00, repeats weekly
BACKEND: ollama
RETRIEVED GUIDELINES:
  - general.md # Prioritizing when time is short
  - dogs.md # Walking and exercise
  - dogs.md # Feeding
ADVICE:
Given Biscuit's schedule and guidelines:
* Prioritize feeding: Since it's a busy day, ensure Biscuit is fed first, at 08:00
  (high priority task). This aligns with prioritizing health-critical tasks.
* Adjust morning walk time: While Biscuit needs 30-60 minutes of walking per day, the
  current 30-minute walk may not be sufficient. Consider adding a shorter play session
  or short walk later in the day (enrichment and grooming can be shortened or shifted).
* Toileting needs: prioritize a quick toileting break at 08:00 to meet daily needs.

===== Scenario 2: cat, 60 minutes =====
INPUT: Whiskers — cat Tabby; 60 min available
  task: Litter box — 10 min, high priority, at 07:30, repeats daily
  task: Play session — 15 min, low priority, at 18:00, repeats daily
BACKEND: ollama
RETRIEVED GUIDELINES:
  - cats.md # Litter box care
  - general.md # Prioritizing when time is short
  - cats.md # Play and enrichment
ADVICE:
• High priority: Complete the litter box task at 07:30 (10 minutes). This is a critical
  health-critical task that needs attention first.
• Adapt play session: Shorten or adjust the 18:00 play session to fit your time.
  Skipping it entirely would be detrimental (see "Prioritizing when time is short").
• Enrichment and grooming can be shortened or shifted to another day without harm.

===== Scenario 3: guardrail — no live model available =====
BACKEND: offline
RETRIEVED GUIDELINES:
  - general.md # Prioritizing when time is short
  - dogs.md # Walking and exercise
  - dogs.md # Feeding
ADVICE:
⚠️ No live AI model is available, so here are the most relevant care guidelines
retrieved for this pet (offline fallback):
- Prioritizing when time is short — On a busy day, health-critical tasks come first:
  feeding, any medication, and toileting needs (walks for dogs, litter for cats).
- Walking and exercise — Most adult dogs need 30-60 minutes of walking per day...
- Feeding — Adult dogs are usually fed twice a day on a consistent schedule.
Prioritize feeding, medication, and toileting first when time is short.
```

### ✅ Reliability — logging / audit trail (`pawpal.log`)

Every retrieval and backend choice is logged, including the fallback decision in Scenario 3:

```text
pawpal.ai INFO Loaded 15 knowledge chunk(s) from .../knowledge
pawpal.ai INFO Retrieved 3/15 chunk(s) for query 'dog Golden Retriever ...':
  ['general.md#Prioritizing when time is short (14)', 'dogs.md#Walking and exercise (8)', 'dogs.md#Feeding (8)']
pawpal.ai INFO Ollama backend (llama3.2) answered (900 chars)
pawpal.ai INFO Retrieved 3/15 chunk(s) for query 'cat Tabby ...':
  ['cats.md#Litter box care (21)', 'general.md#Prioritizing when time is short (14)', 'cats.md#Play and enrichment (11)']
pawpal.ai INFO Ollama backend (llama3.2) answered (778 chars)
pawpal.ai INFO No live LLM backend answered; caller should use offline fallback
```

---

## 🪞 Reflection

Building PawPal+ taught me that the hard part of an "AI system" is mostly *not* the model:
it's deciding what the AI should be responsible for, grounding it so its output is
trustworthy, and designing the surrounding code so a missing or slow model degrades
gracefully instead of breaking the app. Keeping a clean split between deterministic logic
and the AI layer made both easier to build, test, and reason about.

> The graded responsible-AI reflection — how I collaborated with AI, one helpful and one
> flawed AI suggestion, and the system's limitations — lives in `model_card.md` (added in
> Step 5 of this submission), not here.

---

## 📂 Project structure

```
applied-ai-system-final/
├── app.py               # Streamlit UI (scheduler + AI advisor)
├── pawpal_system.py     # deterministic scheduler (Owner / Pet / Task / Scheduler)
├── pawpal_ai.py         # RAG layer (Retriever, generate() fallback chain, PetCareAdvisor)
├── main.py              # terminal demo of the scheduler
├── demo_ai.py           # terminal demo of the RAG advisor + offline guardrail
├── knowledge/           # the retrieval corpus: dogs.md, cats.md, general.md
├── tests/               # test_pawpal.py (13) + test_pawpal_ai.py (8)
├── diagrams/            # architecture.mmd (system flow) + uml_final.mmd (classes)
├── assets/              # architecture images
├── model_card.md        # responsible-AI reflection
├── PORTFOLIO.md         # portfolio artifact (GitHub link + reflection)
└── requirements.txt
```
