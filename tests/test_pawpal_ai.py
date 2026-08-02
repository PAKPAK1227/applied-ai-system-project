"""Reliability tests for the PawPal+ AI (RAG) layer.

These verify the parts that must stay correct for the advisor to be trustworthy:
retrieval actually finds relevant guidelines, the fallback chain degrades safely
when no model is available, and the advisor never crashes the app. The live LLM
backends are monkeypatched, so these run offline with no model or API key.
"""

import pawpal_ai
from pawpal_ai import (
    GenerationResult,
    PetCareAdvisor,
    Retriever,
    generate,
    load_knowledge,
)


# --- Knowledge base + retrieval ----------------------------------------------

def test_load_knowledge_returns_chunks():
    """The knowledge base loads and chunks into multiple sections."""
    chunks = load_knowledge()
    assert len(chunks) > 5
    assert all(c.heading and c.text for c in chunks)


def test_retriever_ranks_relevant_chunk_first():
    """A dog-walking query surfaces a dog guideline above unrelated ones."""
    retriever = Retriever(load_knowledge())

    results = retriever.retrieve("dog walking exercise for my puppy", k=3)

    assert results, "expected at least one relevant chunk"
    top_chunk, top_score = results[0]
    assert top_chunk.source == "dogs.md"
    assert top_score > 0
    # Results are sorted by descending relevance score.
    scores = [score for _chunk, score in results]
    assert scores == sorted(scores, reverse=True)


def test_retriever_returns_empty_for_no_overlap():
    """A query with no keyword overlap retrieves nothing (no false matches)."""
    retriever = Retriever(load_knowledge())

    assert retriever.retrieve("quantum spacecraft telemetry", k=3) == []


# --- Fallback chain -----------------------------------------------------------

def test_generate_returns_none_when_no_backend_available(monkeypatch):
    """With every live backend unavailable, generate() reports no result."""
    monkeypatch.setattr(pawpal_ai, "_generate_anthropic", lambda system, user: None)
    monkeypatch.setattr(pawpal_ai, "_generate_ollama", lambda system, user: None)

    assert generate("system", "user") is None


def test_generate_prefers_anthropic_over_ollama(monkeypatch):
    """The chain tries Anthropic first and stops on the first success."""
    monkeypatch.setattr(pawpal_ai, "_generate_anthropic", lambda system, user: "from-anthropic")
    monkeypatch.setattr(pawpal_ai, "_generate_ollama", lambda system, user: "from-ollama")

    result = generate("system", "user")

    assert result.backend == "anthropic"
    assert result.text == "from-anthropic"


# --- Advisor: grounding + guardrail ------------------------------------------

def test_advise_offline_fallback_is_grounded_in_retrieved_guidelines(monkeypatch):
    """With no live model, advice still surfaces the retrieved guideline headings."""
    monkeypatch.setattr(pawpal_ai, "_generate_anthropic", lambda system, user: None)
    monkeypatch.setattr(pawpal_ai, "_generate_ollama", lambda system, user: None)
    advisor = PetCareAdvisor()

    result = advisor.advise(
        pet_label="Biscuit (Golden Retriever)",
        species="dog",
        breed="Golden Retriever",
        task_descriptions=["Morning walk — 30 min, high priority"],
        available_minutes=60,
    )

    assert result.backend == "offline"
    assert result.retrieved, "offline advice must still be retrieval-grounded"
    # Every retrieved guideline heading appears in the offline advice text.
    for chunk in result.retrieved:
        assert chunk.heading in result.advice


def test_advise_uses_live_backend_and_reports_sources(monkeypatch):
    """When a model answers, its text is returned and the sources are recorded."""
    monkeypatch.setattr(
        pawpal_ai, "generate",
        lambda system, user: GenerationResult(text="Walk Biscuit twice today.", backend="ollama"),
    )
    advisor = PetCareAdvisor()

    result = advisor.advise(
        pet_label="Biscuit (Golden Retriever)",
        species="dog",
        breed="Golden Retriever",
        task_descriptions=["Morning walk — 30 min, high priority"],
        available_minutes=90,
    )

    assert result.backend == "ollama"
    assert result.advice == "Walk Biscuit twice today."
    assert result.sources, "advice should cite the guidelines it retrieved"


def test_advise_never_raises_with_no_tasks(monkeypatch):
    """An advice request for a pet with no tasks returns safely, never crashes."""
    monkeypatch.setattr(pawpal_ai, "_generate_anthropic", lambda system, user: None)
    monkeypatch.setattr(pawpal_ai, "_generate_ollama", lambda system, user: None)
    advisor = PetCareAdvisor()

    result = advisor.advise(
        pet_label="Whiskers (cat)",
        species="cat",
        breed="",
        task_descriptions=[],
        available_minutes=0,
    )

    assert isinstance(result.advice, str) and result.advice
