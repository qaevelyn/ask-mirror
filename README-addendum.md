# overseer.py — the orchestrator

Overseer + Workers pattern: dispatches each query to 4 workers
(W1 deepseek_conversations, W2 mirror_food_emails, W3 working_documents,
W4 msgvault SQL), dedupes, enforces EvidenceFlow grounding (NOT IN CORPUS
abstention), generates via granite, and logs per-worker productivity
(hits, latency) to ask-productivity.jsonl.

Usage: python3 overseer.py "question"
Requires: Ollama running (nomic-embed-text + granite4.1:3b), ChromaDB stores, msgvault.db
