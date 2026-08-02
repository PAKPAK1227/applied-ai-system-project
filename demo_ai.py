"""Terminal demo of the PawPal+ RAG advisor — reproducible text evidence.

Runs the AI advisor on two pets (retrieval + generation), then demonstrates the
offline fallback guardrail by forcing every live model backend to be unavailable.
Every retrieval and backend choice is also written to pawpal.log.

Run with:  python demo_ai.py
"""

import logging

import pawpal_ai
from pawpal_ai import PetCareAdvisor
from pawpal_system import Pet, Task

# Log the retrieval/backend audit trail to pawpal.log (file only, so this demo's
# stdout stays clean). The Streamlit app configures console logging too.
_log = logging.getLogger("pawpal.ai")
if not _log.handlers:
    handler = logging.FileHandler("pawpal.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    _log.addHandler(handler)
    _log.setLevel(logging.INFO)


def task_lines(pet: Pet) -> list[str]:
    """Describe a pet's pending tasks the way the app does for the advisor."""
    return [
        f"{t.description} — {t.duration} min, {t.priority} priority, "
        f"at {t.time or 'unscheduled'}, repeats {t.frequency}"
        for t in pet.pending_tasks()
    ]


def show(title: str, advisor: PetCareAdvisor, pet: Pet, minutes: int) -> None:
    """Run the advisor for one pet and print a labelled input/output block."""
    lines = task_lines(pet)
    result = advisor.advise(
        pet_label=f"{pet.name} ({pet.breed or pet.species})",
        species=pet.species,
        breed=pet.breed,
        task_descriptions=lines,
        available_minutes=minutes,
    )
    print(f"\n===== {title} =====")
    print(f"INPUT: {pet.name} — {pet.species} {pet.breed}; {minutes} min available")
    for line in lines:
        print(f"  task: {line}")
    print(f"BACKEND: {result.backend}")
    print("RETRIEVED GUIDELINES:")
    for src in result.sources:
        print(f"  - {src}")
    print("ADVICE:")
    print(result.advice)


def main() -> None:
    advisor = PetCareAdvisor()

    # Scenario 1: a dog on a tight morning.
    biscuit = Pet("Biscuit", species="dog", breed="Golden Retriever")
    biscuit.add_task(Task("Morning walk", duration=30, priority="high", time="08:00", frequency="daily"))
    biscuit.add_task(Task("Feeding", duration=10, priority="high", time="08:00", frequency="daily"))
    biscuit.add_task(Task("Grooming", duration=40, priority="medium", time="12:00", frequency="weekly"))
    show("Scenario 1: dog, 45 minutes", advisor, biscuit, 45)

    # Scenario 2: a cat with moderate time.
    whiskers = Pet("Whiskers", species="cat", breed="Tabby")
    whiskers.add_task(Task("Litter box", duration=10, priority="high", time="07:30", frequency="daily"))
    whiskers.add_task(Task("Play session", duration=15, priority="low", time="18:00", frequency="daily"))
    show("Scenario 2: cat, 60 minutes", advisor, whiskers, 60)

    # Scenario 3: guardrail — force every live backend off; the advisor must
    # degrade to the offline fallback instead of crashing.
    print("\n===== Scenario 3: guardrail — no live model available =====")
    pawpal_ai._generate_anthropic = lambda system, user: None
    pawpal_ai._generate_ollama = lambda system, user: None
    show("Offline fallback", advisor, biscuit, 45)


if __name__ == "__main__":
    main()
