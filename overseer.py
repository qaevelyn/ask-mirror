#!/usr/bin/env python3
# overseer.py — A Mirror of My Becoming orchestrator
# OVERSEER: EvidenceFlow guard + dispatcher | WORKERS 1-4: fetch-and-carry
# Usage: python3 overseer.py "question"
import sys, os, json, time, requests, chromadb, sqlite3

Q = " ".join(a for a in sys.argv[1:]) or "What is in this corpus?"
LOG = os.path.expanduser("~/Mirror-Food/ask-productivity.jsonl")
OLLAMA = "http://localhost:11434"

def embed(text):
    return requests.post(OLLAMA+"/api/embeddings",
        json={"model":"nomic-embed-text","prompt":text}, timeout=60).json()["embedding"]

log_entry = {"question": Q, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "workers": []}

def worker(name, fn):
    t0 = time.time()
    try:
        hits = fn()
        dt = round(time.time()-t0, 2)
        log_entry["workers"].append({"worker": name, "hits": len(hits), "latency_s": dt, "status": "ok"})
        print(f"  [{name}] {len(hits)} hits in {dt}s")
        return hits
    except Exception as e:
        log_entry["workers"].append({"worker": name, "hits": 0, "status": f"error: {str(e)[:60]}"})
        print(f"  [{name}] ERROR: {str(e)[:60]}")
        return []

def w1_deepseek():
    c = chromadb.PersistentClient(path=os.path.expanduser("~/Mirror-Food/vector-store"))
    r = c.get_collection("deepseek_conversations").query(query_embeddings=[embed(Q)], n_results=4)
    return list(zip(r["documents"][0], r["metadatas"][0]))

def w2_emails():
    c = chromadb.PersistentClient(path=os.path.expanduser("~/Mirror-Food/vector-store"))
    r = c.get_collection("mirror_food_emails").query(query_embeddings=[embed(Q)], n_results=4)
    return list(zip(r["documents"][0], r["metadatas"][0]))

def w3_working():
    c = chromadb.PersistentClient(path=os.path.expanduser("~/Mirror-Food/vector-store"))
    r = c.get_collection("working_documents").query(query_embeddings=[embed(Q)], n_results=4)
    return list(zip(r["documents"][0], r["metadatas"][0]))

def w4_sql():
    conn = sqlite3.connect(os.path.expanduser("~/.msgvault/msgvault.db"))
    conn.row_factory = sqlite3.Row
    hits = []
    for word in Q.split():
        if len(word) >= 4:
            for r in conn.execute(
                """SELECT m.sent_at, p.email_address AS sender, m.subject, mb.body_text
                FROM messages m LEFT JOIN participants p ON p.id = m.sender_id
                LEFT JOIN message_bodies mb ON mb.message_id = m.id
                WHERE LOWER(m.subject) LIKE ? OR LOWER(mb.body_text) LIKE ?
                ORDER BY m.sent_at DESC LIMIT 3""",
                (f"%{word.lower()}%", f"%{word.lower()}%")):
                full = r["body_text"] or ""
                hits.append((f"[EMAIL {r['sent_at'][:10]} | {r['subject']}] {full}",))
    return list(set(hits))[:4]

