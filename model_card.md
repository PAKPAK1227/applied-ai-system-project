# Model Card — PawPal+ RAG Pet-Care Advisor

This is the responsible-AI reflection for the AI feature in PawPal+: a
Retrieval-Augmented Generation (RAG) advisor that retrieves pet-care guidelines from a
local knowledge base and uses a language model to turn them into advice for a specific
pet and time budget. The advisor's default model is a local `llama3.2` via Ollama, with
an optional Anthropic API backend and an offline template fallback.

---

## Limitations and Biases

- **Only as good as the knowledge base.** The advisor answers from `knowledge/*.md`, which
  currently covers **dogs, cats, and general** care. An owner of a rabbit, bird, or reptile
  gets weak or empty retrieval and therefore weak advice. The notes are English-only and
  reflect general, broadly US-oriented pet-care norms — they are not localized or
  breed-exhaustive.
- **Keyword retrieval has no understanding of meaning.** Retrieval is a transparent
  bag-of-words overlap score, so it can't handle synonyms and can occasionally surface a
  loosely-related section (e.g., a cat feeding note for a dog query when the word "feeding"
  overlaps). It favors sections whose *tags* match, which works well for this small corpus
  but wouldn't scale to a large one without embeddings.
- **Small local model, non-deterministic output.** `llama3.2` is a small model; its wording
  varies between runs and it is occasionally *over-helpful* — during testing it sometimes
  added a sensible tip that went slightly beyond the retrieved notes (e.g., suggesting a
  "quick toileting break" or an "extra litter box"). These were reasonable but not strictly
  in the source text, which is a mild grounding drift.
- **Not veterinary advice.** The system gives general scheduling and care guidance. It is
  not a medical tool and should not be used for diagnosis or treatment decisions.
- **Scheduler limitations carry over.** Conflict detection only flags identical start times
  (not overlapping durations), and the auto-fit plan sequences tasks from a fixed day start
  rather than honoring each task's set time.

---

## Could It Be Misused, and How Is That Prevented?

- **Mistaking it for a vet.** The main risk is a user treating the advice as authoritative
  medical guidance. *Mitigations already in place:* the system prompt constrains the model
  to the retrieved guidelines and tells it to say when something isn't covered rather than
  invent facts; the UI shows which guidelines were used so advice is verifiable; output is
  general and scheduling-focused. *Further mitigation:* an explicit "not a substitute for a
  vet" disclaimer could be shown in the UI.
- **Hallucination / fabricated facts.** A language model can invent plausible-sounding
  claims. *Mitigation:* RAG grounding plus the instruction to use only the provided
  guidelines, and the visible source list, so a user can check the advice against the
  retrieved notes.
- **Prompt injection via task text.** Task descriptions are user-authored and inserted into
  the prompt, so a user could try to steer the model off-task. *Mitigation:* this is a
  single-user, local app with a constraining system prompt, so the blast radius is small;
  the model is instructed to answer only about pet care using the guidelines.
- **Privacy.** Because the default path is a local model with no account, pet and schedule
  data stay on the user's machine — nothing is sent to a third party unless the user opts
  into the Anthropic backend.

---

## What Surprised Me While Testing Reliability

- **You can't unit-test an LLM's exact words.** I expected to assert on output text; instead
  I had to test the *pipeline's behavior* — which backend was chosen, that sources were
  returned, that the offline fallback still surfaces the retrieved headings. Testing an AI
  feature meant testing structure and grounding, not prose.
- **The small local model was more grounded than I expected.** `llama3.2` reliably cited the
  guideline names and mostly stuck to the retrieved notes; its main flaw was
  *over-helpfulness* (adding an extra reasonable tip), not fabrication.
- **The offline fallback became a real feature, not just an error path.** Forcing every
  model off still produced useful, source-backed output, which reframed the fallback as a
  legitimate product state rather than a failure mode.
- **Tag weighting mattered more than expected.** In the logs, the cat query scored the
  "Litter box care" section at 21 versus 11–14 for others — the ×3 tag weighting cleanly
  separated the right section from near-misses.

---

## Collaboration with AI

I built the AI feature of PawPal+ in partnership with **Claude Code**, an AI coding agent.
It helped brainstorm the RAG design, wrote the retriever/generator/advisor code, installed
and wired up the local Ollama model, drafted tests and documentation, and captured the
execution evidence. I made the decisions — choosing RAG, keeping a free local model as the
default, and defining what "done" looked like — and reviewed and corrected its work.

**One helpful suggestion.** When I said I might not have a paid API key, the AI proposed
using a **free local model (Ollama) with a three-tier fallback chain** (Anthropic API →
local Ollama → offline template). This removed the cost/access blocker entirely: the project
runs for anyone with no key and no billing, still uses a genuine model, and upgrades to a
hosted model later by just setting an environment variable. That one suggestion shaped the
whole reliability design.

**One flawed suggestion.** When writing the README setup steps, the AI generated a clone
command with a nested path (`cd applied-ai-system-project/applied-ai-system-final`),
assuming the project lived in a subfolder. It was wrong — the Git repository's root *is* the
project folder, so anyone following those steps would have `cd`'d into a directory that
doesn't exist. (It also first referenced a `model_card.md` link before that file existed.)
I caught both by checking the actual repository layout, and the AI corrected them. The
lesson: an AI will confidently assume things about your environment and filesystem — verify
those assumptions against reality instead of trusting them.
