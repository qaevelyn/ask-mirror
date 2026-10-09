# ask — hybrid retrieval over your own corpus

One command against your own archive: vector search (what does it *mean*) + SQL (who/when/what exactly) + a local LLM answer that abstains instead of hallucinating.

- `ask "question"` — vector + SQL merged, granite answers with source citations
- `ask --from 2026-09-01 --to 2026-10-07 "topic"` — date-bounded
- `getdoc.py "topic"` — reconstructs a complete document from its chunks, in order

Runs on Ollama + ChromaDB. No cloud. No accounts. Part of [A Mirror of My Becoming™](https://github.com/qaevelyn/a-mirror-of-my-becoming).
