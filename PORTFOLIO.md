# Portfolio Artifact — PawPal+

**Project:** PawPal+ — an AI-assisted pet-care planner with a Retrieval-Augmented
Generation (RAG) advisor.

**GitHub:** https://github.com/PAKPAK1227/applied-ai-system-project

**Live AI feature:** a RAG advisor that retrieves real pet-care guidelines from a local
knowledge base and uses a language model (local Ollama by default, Anthropic API optional)
to generate advice grounded in those guidelines and the owner's actual schedule.

---

## What this project says about me as an AI engineer

This project shows that I treat an AI feature as a system to be engineered, not a model to
be dropped in. I started from a working, well-tested Python app and added intelligence
deliberately: I chose Retrieval-Augmented Generation so the AI's answers stay grounded in a
source I control, kept the deterministic logic separate and fully testable, and designed a
three-tier fallback chain (hosted API → free local model → offline template) so the system
runs reproducibly for anyone and degrades safely when no model is available. I built in
logging, timeouts, and error handling as first-class concerns, and I wrote tests that check
the pipeline's behavior and grounding rather than an LLM's exact words. Just as importantly,
I stayed the decision-maker while collaborating with an AI coding agent — accepting the
ideas that held up, catching the ones that didn't, and verifying assumptions against the
real environment. In short: I can take an AI capability from idea to a reliable,
documented, and honestly-evaluated feature.
