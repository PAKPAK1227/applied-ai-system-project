# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

Based on the PawPal+ scenario, a user should be able to perform these three core actions:

1. **Add a pet (and owner) profile** — The user enters basic owner information and creates a pet with details like name, species/breed, and any care preferences. This gives the app the context it needs to plan care around a specific animal.
2. **Add or edit a care task** — The user records tasks such as walks, feeding, medications, enrichment, or grooming. Each task carries at least a duration and a priority (and can be edited later) so the scheduler knows how long it takes and how important it is.
3. **Generate and view today's daily plan** — The user asks PawPal+ to build a daily schedule from the current tasks, respecting constraints like available time and priority. The app then displays the resulting plan clearly and, ideally, explains why it ordered things the way it did.

**a. Initial design**

My design settled on four classes:

- **Task** — one care activity: description, duration (time), priority, frequency, and completion status.
- **Pet** — a single animal (name, species, breed) that owns its list of tasks.
- **Owner** — the user; holds available care time and preferences, manages multiple pets, and exposes all their tasks in one place.
- **Scheduler** — the "brain" that gathers tasks across all of the owner's pets, sorts them by priority, and fits them into the available time to build a daily plan.

Relationships: an Owner has many Pets, each Pet has many Tasks, and the Scheduler reads the Owner to organize Tasks into a plan.

**b. Design changes**

- **Added an `id` to Task.** The review flagged that `Pet.edit_task(task_id)` and `remove_task(task_id)` referenced an identifier that didn't exist. I added an auto-generated `id` so tasks can be found and edited/removed reliably.
- **Renamed CareTask → Task and dropped DailyPlan.** I simplified to four classes. Instead of a separate `DailyPlan` object, `Scheduler.build_plan` returns a lightweight dict (scheduled, skipped, total_time, reasoning), which was enough for the UI and easier to test.
- **Made the Scheduler work across pets.** Rather than duplicating `available_minutes`, the `Scheduler` reads `Owner.pending_tasks()` (which returns `(pet, task)` pairs) so tasks stay linked to their pet across the whole household, and the time budget comes from the owner at plan time.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints: the owner's available minutes (a time budget), each task's priority, and each task's set time (used for the agenda and conflict checks). Preferences are stored on the `Owner` but not yet used by the planner.

Priority mattered most. A busy owner's real question is "if I can't do everything, what must get done?" — so `build_plan` schedules high priority first, breaking ties by shortest duration to fit more in.

**b. Tradeoffs**

My conflict detection only flags tasks with the **exact same start time** ("HH:MM") — it does not account for task duration or overlapping windows. So a 30-minute 08:00 walk and an 08:15 feeding are treated as non-conflicting even though they actually overlap.

This is a reasonable tradeoff for this scenario because exact-time matching is O(n), trivial to reason about, and returns a plain warning instead of crashing or silently rearranging the day. For a single owner juggling a handful of pet chores, "you double-booked 07:30" is the common, useful case; true interval-overlap detection would add real complexity (sorting intervals, comparing end times) for an edge case a busy owner can eyeball. If the app grew, I'd upgrade to duration-aware overlap checking.

---

## 3. AI Collaboration

**a. How you used AI**

I used AI across every phase: brainstorming the UML classes, generating skeleton stubs, writing the scheduling algorithms, drafting tests, and wiring the Streamlit UI. Small, concrete prompts worked best — e.g. "sort Task objects by an HH:MM string using a lambda key" or "give a lightweight conflict-detection strategy that warns instead of crashing." Asking it to review a file for missing relationships also caught a real bug (a `task_id` with no matching `id` field).

**b. Judgment and verification**

I didn't accept the AI's terser `detect_conflicts` (a one-line `defaultdict` + comprehension) because it packed grouping, filtering, and string-building into one expression that was hard to scan; I kept my readable two-phase version instead. I verified every change by running `python main.py` and `python -m pytest`, and used Streamlit's `AppTest` to exercise the UI headlessly.

**c. AI strategy**

- **Most effective features:** agent/multi-file editing for the recurrence change (it touched `Task` and `Scheduler` together), inline chat on a single method for refactors, and attaching a file so it could review the UML/skeleton for gaps.
- **A suggestion I modified:** I kept the `Scheduler` as a class rather than collapsing it into a loose function, and dropped the separate `DailyPlan` class in favor of a simple dict — trimming complexity the AI would otherwise have carried along.
- **Separate chat sessions per phase** kept each context focused: testing prompts didn't muddy implementation context, so suggestions stayed on-task instead of drifting.
- **Lead architect takeaway:** AI is fast at options and boilerplate, but the decisions — keep it four classes, warn instead of crash, exact-time conflicts for now — were mine. I treated its output as a draft to verify, not an answer to trust.

---

## 4. Testing and Verification

**a. What you tested**

The 13 tests cover the behaviors an owner relies on: marking tasks complete, adding tasks, sorting by time (including unscheduled-last), filtering by pet and status, daily and weekly recurrence, non-recurring tasks not regenerating, conflict detection (flagged and clear cases), budget-based skipping, and an empty plan. These matter because they're exactly the behaviors most likely to break during a refactor.

**b. Confidence**

Confident — 4/5. The core logic is well covered, including edge cases. The gaps: the Streamlit UI has no automated tests in the suite (I verified it manually with `AppTest`), and conflict detection only checks exact times. Next I'd test overlapping-duration conflicts, midnight/late-day edge times, and editing a whole recurring series.

---

## 5. Reflection

**a. What went well**

The clean split between the logic layer (`pawpal_system.py`) and the UI (`app.py`). The `Scheduler` methods are small and independently testable, which made adding sorting, filtering, recurrence, and conflicts low-risk.

**b. What you would improve**

I'd make `build_plan` respect each task's set time instead of auto-sequencing from 08:00, so the agenda and the auto-fit plan agree. I'd also upgrade conflict detection to be duration-aware.

**c. Key takeaway**

Being the lead architect matters more than the code the AI writes. Small, verifiable increments and clear design calls kept the system coherent — the AI accelerated the work, but I owned the direction.

---

## 6. AI Feature — RAG Pet-Care Advisor

**a. What it does**

The AI feature is a Retrieval-Augmented Generation (RAG) advisor (`pawpal_ai.py`). When
the owner asks for advice on a pet, it (1) **retrieves** the most relevant snippets from a
local knowledge base of pet-care guidelines (`knowledge/*.md`), then (2) sends those
snippets — plus a summary of the pet's real tasks and the owner's time budget — to a
language model that **generates** advice grounded in the retrieved notes. It's integrated
into the main app, not a standalone script: the retrieved guidelines and the live schedule
actively shape the model's answer.

**b. Design decisions and tradeoffs**

- **Real model, no cloud lock-in.** The generator tries three backends in order —
  Anthropic API → local Ollama (`llama3.2`) → offline template. The default demo path is a
  free local model, so the project runs reproducibly for anyone with no API key or cost,
  and upgrades to a hosted model by just setting a key (no code change).
- **Keyword retrieval over embeddings.** I used a transparent bag-of-words overlap score
  rather than a vector database. It's dependency-free, fast, easy to test, and easy to
  explain — the right call for a small, well-tagged knowledge base.
- **Fail safe, never crash.** Every model call is wrapped with a timeout and error handling.
  If no model is reachable, the advisor still returns the retrieved guidelines (the offline
  fallback), so the feature degrades gracefully instead of erroring.

**c. Reliability and verification**

Eight tests (`tests/test_pawpal_ai.py`) cover the parts that must stay correct: retrieval
finds relevant guidelines and rejects no-overlap queries, the fallback chain picks the right
backend, and the advisor stays grounded (offline advice still surfaces the retrieved
headings) and never raises. The model backends are monkeypatched, so the tests run offline
with no API key or running model. Every retrieval and backend choice is logged to
`pawpal.log` for an audit trail. I verified the full path end-to-end against a live local
Ollama model.
