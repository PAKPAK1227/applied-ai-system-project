# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## ✨ Features

PawPal+ pairs a plain-Python logic layer (`pawpal_system.py`) with a Streamlit UI (`app.py`):

- **Owner / pet / task modeling** — an `Owner` manages multiple `Pet`s, each owning its own `Task`s (description, time, duration, priority, frequency, completion).
- **Priority-first auto-planning** — `Scheduler.build_plan()` greedily fits tasks into the owner's available minutes, highest priority first, and reports what it scheduled, what it skipped, and why.
- **Sort by time** — `Scheduler.sort_by_time()` orders tasks chronologically by their `HH:MM` time (unscheduled tasks last).
- **Filtering** — `Scheduler.filter_tasks()` narrows tasks by pet name and/or completion status.
- **Daily & weekly recurrence** — completing a recurring task auto-creates its next occurrence with the correct next due date (`Task.next_occurrence()` + `Scheduler.mark_task_complete()`).
- **Conflict warnings** — `Scheduler.detect_conflicts()` flags tasks booked at the same time and returns friendly warnings instead of crashing.

## 🤖 AI Feature — RAG Pet-Care Advisor

PawPal+ includes a **Retrieval-Augmented Generation (RAG)** advisor (`pawpal_ai.py`)
that is fully integrated into the app: it looks up real pet-care guidelines *before*
answering, then an AI model uses those retrieved guidelines — together with the pet's
actual tasks and the owner's time budget — to write specific advice for the day.

**How it works (retrieve → generate):**

1. **Retrieve** — `Retriever` searches a local knowledge base of pet-care notes
   (`knowledge/*.md`, chunked by section) and scores them by keyword overlap with the
   pet in question. No API key or model is needed for this step.
2. **Generate** — the retrieved guideline snippets plus a summary of the pet's current
   schedule are sent to a language model, which produces advice **grounded in the
   retrieved notes** (it uses them to reason, rather than printing them verbatim).

**Runs for anyone — a 3-tier generator fallback chain** (`generate()`):

| Order | Backend | When it's used |
|-------|---------|----------------|
| 1 | **Anthropic API** | if `ANTHROPIC_API_KEY` is set (and the `anthropic` package is installed) |
| 2 | **Local Ollama** (`llama3.2`) | if an Ollama server is running locally — the default demo path, free and offline |
| 3 | **Offline template** | guardrail: if no model is reachable, it still returns the retrieved guidelines instead of crashing |

**Guardrails & logging:** every retrieval and backend attempt is written to `pawpal.log`
(configured via `configure_logging()`). All model calls are wrapped in error handling with
a timeout, so a missing/slow/failed model degrades to the offline fallback rather than
erroring. The UI shows which backend answered and which guidelines were retrieved, so it's
transparent that the advice is retrieval-grounded.

See [`diagrams/architecture.mmd`](diagrams/architecture.mmd) for the full system data flow.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Enabling the AI advisor (choose one)

The scheduler and the RAG **retrieval** step work with no extra setup. To get real AI
**generation**, enable one backend (the app auto-detects whichever is available and falls
back safely if none is):

**Option A — Local model with Ollama (recommended, free, no API key):**

```bash
# macOS (Homebrew); see https://ollama.com for other platforms
brew install ollama
ollama serve &          # start the local model server
ollama pull llama3.2    # one-time ~2 GB model download
```

**Option B — Anthropic API (optional, paid):**

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."   # billed separately from a Claude.ai subscription
```

**Option C — Nothing:** the advisor still runs and returns the retrieved guidelines via the
offline fallback (no real model, weaker output).

Optional environment variables: `PAWPAL_OLLAMA_MODEL` (default `llama3.2`), `OLLAMA_HOST`
(default `http://localhost:11434`), `PAWPAL_ANTHROPIC_MODEL`, `PAWPAL_LLM_TIMEOUT`.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Terminal output from running the logic layer with `python main.py`:

```
==========================================
Today's Schedule for Sam  (budget: 90 min)
==========================================
  08:00-08:05  Feeding           5 min  [high  ] Whiskers
  08:05-08:15  Feeding          10 min  [high  ] Biscuit
  08:15-08:45  Morning walk     30 min  [high  ] Biscuit
  08:45-08:55  Litter box       10 min  [medium] Whiskers
  08:55-09:20  Enrichment play  25 min  [low   ] Biscuit

Skipped (ran out of time):
  - Grooming (40 min) for Biscuit

Total care time: 80 min
Sorted 6 pending task(s) by priority. Scheduled 5 using 80 of 90 min; skipped 1 that did not fit.
```

## 🧪 Testing PawPal+

Run the full suite from the project root:

```bash
python -m pytest
```

**What the tests cover** (21 tests total):

*Scheduler logic* (`tests/test_pawpal.py`, 13 tests):

- **Task & pet basics** — marking a task complete flips its status; adding a task grows the pet's task list.
- **Sorting** — `sort_by_time()` returns tasks in chronological `HH:MM` order and pushes unscheduled tasks last.
- **Filtering** — `filter_tasks()` narrows by pet name and by completion status.
- **Recurrence** — completing a daily task queues a copy due the next day; a weekly task advances one week; a one-off task does not regenerate.
- **Conflict detection** — `detect_conflicts()` flags two tasks sharing a time slot and stays silent when times differ.
- **Priority planning & edge cases** — `build_plan()` skips tasks that exceed the time budget, and an owner with no tasks produces an empty, non-crashing plan.

*RAG advisor reliability* (`tests/test_pawpal_ai.py`, 8 tests) — these run offline with the
model backends monkeypatched, so they need no API key or running model:

- **Retrieval** — the knowledge base loads and chunks; a dog query ranks a dog guideline first and results are score-ordered; a query with no keyword overlap retrieves nothing (no false matches).
- **Fallback chain** — `generate()` returns `None` when no live backend is available and prefers Anthropic over Ollama when both answer.
- **Grounding & guardrail** — with no live model, the advice still surfaces the retrieved guideline headings (proving retrieval shapes the output); when a model answers, its text and the retrieved sources are returned; an advice request for a pet with no tasks never raises.

Successful run:

```
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.1.0, pluggy-1.6.0
collected 21 items

tests/test_pawpal.py .............                                       [ 61%]
tests/test_pawpal_ai.py ........                                         [100%]

============================== 21 passed in 0.05s ==============================
```

**Confidence Level: ★★★★☆ (4/5)**

The core scheduling behaviors — sorting, filtering, recurrence, conflict detection, and budget-aware planning — are all covered by passing tests, including key edge cases. I held back the fifth star because conflict detection only checks exact time matches (not overlapping durations), and the recurring/conflict features aren't yet exercised end-to-end through the Streamlit UI.

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Priority planning | `Scheduler.build_plan()`, `Scheduler.sort_tasks()` | Greedily fits tasks into the time budget, highest priority first (ties broken by shortest duration). |
| Sort by time | `Scheduler.sort_by_time()` | Orders tasks by their `"HH:MM"` time using a `sorted()` lambda key; unscheduled tasks sort last. |
| Filtering | `Scheduler.filter_tasks()` | Filters tasks by pet name and/or completion status (either filter is optional). |
| Recurring tasks | `Task.next_occurrence()`, `Task.is_recurring()`, `Scheduler.mark_task_complete()` | Completing a `daily`/`weekly` task auto-queues a fresh copy with the next `due_date` (via `timedelta`). |
| Conflict detection | `Scheduler.detect_conflicts()` | Lightweight check that returns warning strings when two tasks (same or different pets) share an exact `"HH:MM"` slot — never crashes. |

## 📸 Demo Walkthrough

Launch the Streamlit app with:

```bash
streamlit run app.py
```

### Main UI features and actions

- **Owner panel** — set the owner's name and how many minutes of care time are available today.
- **Add a pet** — enter a name, species, and breed to register a pet.
- **Add a task** — pick a pet, then set the task's description, time, duration, priority, and frequency (daily / weekly / once).
- **Task list** — filter tasks by pet or hide completed ones, and tick a checkbox to mark a task done.
- **Today's Schedule** — see conflict warnings, a time-sorted agenda, and an on-demand auto-fit plan.

### Example workflow

1. Set the owner name to **Sam** and available time to **120 minutes**.
2. **Add a pet:** "Biscuit" (dog, Golden Retriever).
3. **Add a task:** "Morning walk" at 08:00, 30 min, high priority, daily.
4. **Add another task:** "Feeding" at 08:00, 10 min, high priority, daily.
5. Scroll to **Today's Schedule** — a ⚠️ conflict warning appears because both tasks are booked at 08:00.
6. Change one task's time, then click **Auto-fit plan for my available time** to see the priority-ordered plan.
7. Tick **Morning walk** complete — because it's daily, tomorrow's copy is queued automatically (a "🔁 re-added" message confirms it).

### Key Scheduler behaviors shown

- **Sorting** — the agenda lists tasks in chronological order via `Scheduler.sort_by_time()`.
- **Filtering** — the "Show pet" / "Hide completed" controls use `Scheduler.filter_tasks()`.
- **Conflict warnings** — same-time tasks trigger `st.warning` banners from `Scheduler.detect_conflicts()`.
- **Recurrence** — completing a daily/weekly task regenerates it via `Scheduler.mark_task_complete()`.
- **Priority planning** — the auto-fit plan comes from `Scheduler.build_plan()`.

### Sample CLI output (`python main.py`)

```
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
  After:  Biscuit has 5 tasks; next 'Grooming' due 2026-07-12
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
