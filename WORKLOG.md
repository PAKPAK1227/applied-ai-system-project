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

