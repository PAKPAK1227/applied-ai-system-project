"""PawPal+ AI layer — a Retrieval-Augmented Generation (RAG) pet-care advisor.

This module is the "AI feature" of PawPal+. It does NOT replace the deterministic
scheduler in ``pawpal_system.py``; it sits alongside it and answers a different
question: *"Given real pet-care guidelines and this owner's actual pets, tasks,
and available time, what should they do?"*

RAG = Retrieval + Generation:

1. **Retrieve** — ``Retriever`` searches a local knowledge base of pet-care notes
   (the ``knowledge/`` folder) and returns the most relevant snippets for the pet
   in question. No model or API key is needed for this step.
2. **Generate** — ``generate()`` sends those retrieved snippets, plus a summary of
   the pet's current schedule, to a language model, which writes advice that is
   *grounded in the retrieved notes*. The model actively uses the retrieved data
   to form its answer — it does not just print the notes verbatim.

The generator tries three backends in order, so the app runs for anyone:

    Anthropic API (if ANTHROPIC_API_KEY is set)  →  local Ollama  →  offline template

The offline template is a guardrail: if no model is reachable, the advisor still
returns useful, retrieval-grounded output instead of crashing. Every step is
logged so you can see what was retrieved and which backend answered.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# --- Configuration (all overridable via environment variables) ---------------
KNOWLEDGE_DIR = Path(os.environ.get("PAWPAL_KNOWLEDGE_DIR", Path(__file__).parent / "knowledge"))
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("PAWPAL_OLLAMA_MODEL", "llama3.2")
ANTHROPIC_MODEL = os.environ.get("PAWPAL_ANTHROPIC_MODEL", "claude-opus-5")
REQUEST_TIMEOUT = float(os.environ.get("PAWPAL_LLM_TIMEOUT", "60"))

logger = logging.getLogger("pawpal.ai")

SYSTEM_PROMPT = (
    "You are PawPal+, a concise, practical pet-care assistant. "
    "Answer ONLY using the care guidelines provided in the prompt and the owner's "
    "actual pet and schedule. Ground every recommendation in those guidelines; if "
    "the guidelines don't cover something, say so rather than inventing facts. "
    "Keep the answer short: 3-5 specific, actionable bullet points for this owner today."
)

# Words ignored when scoring retrieval relevance.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "at", "is", "are",
    "with", "how", "do", "i", "my", "me", "need", "should", "care", "pet", "pets",
}


def configure_logging(logfile: str | os.PathLike = "pawpal.log") -> None:
    """Send this module's logs to a file and the console.

    Safe to call more than once — it won't stack duplicate handlers. Callers that
    manage their own logging can skip this; the module never configures logging
    on import.
    """
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def _tokenize(text: str) -> list[str]:
    """Lowercase a string into meaningful word tokens (stopwords removed)."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


# --- Retrieval ----------------------------------------------------------------

@dataclass
class KnowledgeChunk:
    """One retrievable snippet of pet-care guidance (a section of a notes file)."""

    source: str          # file the chunk came from, e.g. "dogs.md"
    heading: str         # section heading, e.g. "Walking and exercise"
    tags: list[str]      # keywords declared on the section's `tags:` line
    text: str            # the guidance body

    def searchable_tokens(self) -> list[str]:
        """All tokens the retriever scores against (tags weighted by repetition)."""
        # Repeat tag tokens so an explicit tag match counts for more than a
        # passing mention in the body.
        return _tokenize(self.heading) + _tokenize(" ".join(self.tags)) * 3 + _tokenize(self.text)


def load_knowledge(path: Path | None = None) -> list[KnowledgeChunk]:
    """Load and chunk every ``*.md`` file in the knowledge directory.

    Each ``##`` section becomes one ``KnowledgeChunk``. An optional ``tags:`` line
    directly under the heading is parsed into the chunk's tag list. Missing or
    empty directories return an empty list rather than raising, so the advisor can
    still run (it will simply have nothing to retrieve).
    """
    directory = Path(path) if path is not None else KNOWLEDGE_DIR
    chunks: list[KnowledgeChunk] = []
    if not directory.is_dir():
        logger.warning("Knowledge directory not found: %s", directory)
        return chunks

    for md_file in sorted(directory.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        # Split into sections on level-2 headings.
        for section in re.split(r"^##\s+", raw, flags=re.MULTILINE)[1:]:
            lines = section.splitlines()
            heading = lines[0].strip()
            body_lines = lines[1:]
            tags: list[str] = []
            if body_lines and body_lines[0].strip().lower().startswith("tags:"):
                tags = [t.strip() for t in body_lines[0].split(":", 1)[1].split(",") if t.strip()]
                body_lines = body_lines[1:]
            text = "\n".join(body_lines).strip()
            if heading and text:
                chunks.append(KnowledgeChunk(md_file.name, heading, tags, text))

    logger.info("Loaded %d knowledge chunk(s) from %s", len(chunks), directory)
    return chunks


class Retriever:
    """Scores knowledge chunks against a query by keyword overlap.

    Deliberately dependency-free: a transparent bag-of-words overlap score, not an
    embedding model. It is fast, needs no API key, and is easy to test and explain.
    """

    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self.chunks = chunks

    def retrieve(self, query: str, k: int = 3) -> list[tuple[KnowledgeChunk, int]]:
        """Return the top-``k`` (chunk, score) pairs most relevant to ``query``.

        Score = number of query tokens that appear in the chunk (tag matches count
        extra, via ``searchable_tokens``). Chunks with zero overlap are dropped.
        """
        query_tokens = set(_tokenize(query))
        scored: list[tuple[KnowledgeChunk, int]] = []
        for chunk in self.chunks:
            chunk_tokens = chunk.searchable_tokens()
            score = sum(1 for t in chunk_tokens if t in query_tokens)
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        top = scored[:k]
        logger.info(
            "Retrieved %d/%d chunk(s) for query %r: %s",
            len(top), len(self.chunks), query,
            [f"{c.source}#{c.heading} ({s})" for c, s in top],
        )
        return top


# --- Generation (the fallback chain) -----------------------------------------

@dataclass
class GenerationResult:
    """The generated text plus which backend produced it."""

    text: str
    backend: str  # "anthropic" | "ollama" | "offline"


def _generate_anthropic(system: str, user: str) -> str | None:
    """Try the Anthropic API. Returns None if unavailable (no key/package/error)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # optional dependency; only needed for this backend
    except ImportError:
        logger.info("anthropic package not installed; skipping Anthropic backend")
        return None
    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        logger.info("Anthropic backend answered (%d chars)", len(text))
        return text.strip() or None
    except Exception as exc:  # network, auth, rate limit, etc. — never crash the app
        logger.warning("Anthropic backend failed: %s", exc)
        return None


def _generate_ollama(system: str, user: str) -> str | None:
    """Try a local Ollama server. Returns None if unreachable or on error."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "system": system,
        "prompt": user,
        "stream": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = (data.get("response") or "").strip()
        logger.info("Ollama backend (%s) answered (%d chars)", OLLAMA_MODEL, len(text))
        return text or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Ollama backend unavailable: %s", exc)
        return None


def generate(system: str, user: str) -> GenerationResult | None:
    """Run the live-backend fallback chain: Anthropic, then Ollama.

    Returns the first successful result, or None if no live model answered (the
    caller then falls back to offline template output).
    """
    for name, backend in (("anthropic", _generate_anthropic), ("ollama", _generate_ollama)):
        text = backend(system, user)
        if text:
            return GenerationResult(text=text, backend=name)
    logger.info("No live LLM backend answered; caller should use offline fallback")
    return None


# --- The advisor: retrieval + generation wired together ----------------------

@dataclass
class AdviceResult:
    """Everything the UI needs to show one piece of advice and how it was made."""

    advice: str
    backend: str                        # which generator answered
    sources: list[str]                  # "file.md # Heading" for each retrieved chunk
    retrieved: list[KnowledgeChunk] = field(default_factory=list)


class PetCareAdvisor:
    """Turns retrieved guidelines + a pet's real schedule into grounded advice."""

    def __init__(self, chunks: list[KnowledgeChunk] | None = None) -> None:
        self.chunks = chunks if chunks is not None else load_knowledge()
        self.retriever = Retriever(self.chunks)

    def _build_query(self, species: str, breed: str, task_descriptions: list[str]) -> str:
        """Compose the retrieval query from the pet and its current tasks."""
        parts = [species, breed, "busy owner limited time priority"] + task_descriptions
        return " ".join(p for p in parts if p)

    def _schedule_summary(self, task_lines: list[str], available_minutes: int) -> str:
        """A plain-text summary of the pet's current tasks and the time budget."""
        if task_lines:
            tasks = "\n".join(f"- {line}" for line in task_lines)
        else:
            tasks = "- (no tasks added yet)"
        return f"Time available today: {available_minutes} minutes.\nCurrent tasks:\n{tasks}"

    def _build_prompt(self, pet_label: str, grounding: str, schedule: str) -> str:
        """Assemble the user prompt: retrieved guidelines + the owner's situation."""
        return (
            f"Pet: {pet_label}\n\n"
            f"{schedule}\n\n"
            "Relevant care guidelines (use ONLY these as your source of facts):\n"
            f"{grounding}\n\n"
            "Based on the guidelines above and this pet's tasks and time budget, give "
            "specific advice for today: what to prioritize, anything important that "
            "seems to be missing, and any adjustment to make. Reference the guidelines "
            "you used."
        )

    def _offline_advice(self, retrieved: list[tuple[KnowledgeChunk, int]]) -> str:
        """Guardrail output when no live model is available.

        Still retrieval-driven: it surfaces the guidelines the retriever selected
        for this pet, so the RAG behaviour (retrieval shaping the answer) is visible
        even with no model running. It does not fabricate model-style prose.
        """
        if not retrieved:
            return (
                "No AI model is currently available and no matching guidelines were "
                "found. Start the Ollama service (or set an API key) for full advice."
            )
        lines = [
            "⚠️ No live AI model is available, so here are the most relevant "
            "care guidelines retrieved for this pet (offline fallback):",
            "",
        ]
        for chunk, _score in retrieved:
            first_sentence = chunk.text.split(". ")[0].strip().rstrip(".")
            lines.append(f"- **{chunk.heading}** — {first_sentence}.")
        lines.append("")
        lines.append(
            "Prioritize feeding, medication, and toileting first when time is short."
        )
        return "\n".join(lines)

    def advise(
        self,
        pet_label: str,
        species: str,
        breed: str,
        task_descriptions: list[str],
        available_minutes: int,
    ) -> AdviceResult:
        """Produce grounded advice for one pet. Never raises — always returns a result."""
        query = self._build_query(species, breed, task_descriptions)
        retrieved = self.retriever.retrieve(query, k=3)
        grounding = "\n\n".join(f"[{c.heading}] {c.text}" for c, _ in retrieved) or "(none found)"
        schedule = self._schedule_summary(task_descriptions, available_minutes)
        sources = [f"{c.source} # {c.heading}" for c, _ in retrieved]

        prompt = self._build_prompt(pet_label, grounding, schedule)
        result = generate(SYSTEM_PROMPT, prompt)

        if result is not None:
            return AdviceResult(
                advice=result.text,
                backend=result.backend,
                sources=sources,
                retrieved=[c for c, _ in retrieved],
            )
        return AdviceResult(
            advice=self._offline_advice(retrieved),
            backend="offline",
            sources=sources,
            retrieved=[c for c, _ in retrieved],
        )
