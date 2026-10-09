#!/usr/bin/env python3
"""getdoc — reconstruct a full document from the vector store.
Usage: python3 getdoc.py "part of the title or content""""
import sys, os, requests, chromadb
probe = " ".join(sys.argv[1:]) or "handover"
vec = requests.post("http://localhost:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": probe}, timeout=60).json()["embedding"]
c = chromadb.PersistentClient(path=os.path.expanduser("~/Mirror-Food/vector-store"))
col = c.get_collection("deepseek_conversations")
hit = col.query(query_embeddings=[vec], n_results=3)
cid = hit["metadatas"][0][0]["conversation_id"]
title = hit["metadatas"][0][0].get("title", "?")
print(f"=== RECONSTRUCTING: {title} (conversation_id: {cid[:12]}...) ===")
full = col.get(where={"conversation_id": cid}, include=["documents", "metadatas"])
pairs = sorted(zip(full["metadatas"], full["documents"]), key=lambda x: x[0].get("chunk_index", 0))
doc = "\n".join(d for _, d in pairs)
out = os.path.expanduser(f"~/Mirror-Food/reconstructed/{title[:40].replace(' ','_')}.md")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w").write(doc)
print(f"chunks: {len(pairs)} | chars: {len(doc):,} | saved: {out}")
print("\n--- first 500 chars ---\n" + doc[:500])
