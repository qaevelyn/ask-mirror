#!/usr/bin/env python3
"""ask.py — query the Mirror corpus with local LLM. Usage: python3 ask.py "your question" """
import sys, os, requests

q = " ".join(sys.argv[1:]) or "What is in this corpus?"
vec = requests.post("http://localhost:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": q}, timeout=60).json()["embedding"]
import chromadb
c = chromadb.PersistentClient(path=os.path.expanduser("~/Mirror-Food/vector-store"))
res = c.get_collection("deepseek_conversations").query(query_embeddings=[vec], n_results=5)
context = "\n\n".join(res["documents"][0])
print("=== SOURCES ===")
for m in res["metadatas"][0]: print(" •", (m.get("title") or "?")[:60])
print("=== ANSWER (granite4.1:3b, local) ===")
r = requests.post("http://localhost:11434/api/generate", timeout=600, json={
    "model": "granite4.1:3b",
    "prompt": f"You are a grounded assistant. Use ONLY the context below. Rules: (1) If the context does not contain the answer, reply exactly: NOT IN CORPUS. (2) Cite which source title each fact came from. (3) Do not use outside knowledge.\n\nCONTEXT:\n{context}\n\nQUESTION: {q}",
    "stream": False})
print(r.json()["response"])
