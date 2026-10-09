#!/usr/bin/env python3
"""ask v3 — hybrid retrieval: vector (meaning) + SQL (entities/dates), one corpus.
Usage: ask "question"              — vector + email-SQL merged
       ask --from 2026-09-01 --to 2026-10-05 "protocol"   — date-bounded hybrid
"""
import sys, os, sqlite3, requests

q = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))
date_from = date_to = None
args = sys.argv[1:]
if "--from" in args: date_from = args[args.index("--from")+1]
if "--to" in args:   date_to   = args[args.index("--to")+1]
if not q: q = "What is in this corpus?"

print("=== VECTOR RESULTS (meaning) ===")
vec = requests.post("http://localhost:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": q}, timeout=60).json()["embedding"]
import chromadb
c = chromadb.PersistentClient(path=os.path.expanduser("~/Mirror-Food/vector-store"))
res = c.get_collection("deepseek_conversations").query(query_embeddings=[vec], n_results=5)
for d, m in zip(res["documents"][0], res["metadatas"][0]):
    print(" •", (m.get("title") or "?")[:60], "::", d[:150].replace("\n", " "))

print("\n=== EMAIL/SQL RESULTS (entities & dates) ===")
conn = sqlite3.connect(os.path.expanduser("~/.msgvault/msgvault.db"))
conn.row_factory = sqlite3.Row
where, params = [], []
for word in q.split():
    if len(word) >= 4 and not word.startswith("--"):
        where.append("(LOWER(m.subject) LIKE ? OR LOWER(p.email_address) LIKE ? OR LOWER(mb.body_text) LIKE ?)")
        params += [f"%{word.lower()}%"] * 3
if date_from: where.append("m.sent_at >= ?"); params.append(date_from)
if date_to:   where.append("m.sent_at <= ?"); params.append(date_to + " 23:59:59")
sql = """SELECT DISTINCT m.sent_at, p.email_address AS sender, m.subject, m.snippet
FROM messages m
LEFT JOIN participants p ON p.id = m.sender_id
LEFT JOIN message_bodies mb ON mb.message_id = m.id """ + \
("WHERE " + " AND ".join(where) if where else "") + " ORDER BY m.sent_at DESC LIMIT 8"
try:
    for r in conn.execute(sql, params):
        print(" •", (r["sent_at"] or "")[:10], "|", (r["sender"] or "?")[:30], "|", (r["subject"] or "?")[:60])
except Exception as e:
    print(" (SQL layer unavailable:", str(e)[:60], ")")

print("\n=== ANSWER (granite4.1:3b, local) ===")
context = "\n\n".join(res["documents"][0])
r = requests.post("http://localhost:11434/api/generate", timeout=600, json={
    "model": "granite4.1:3b",
    "prompt": f"You are a grounded assistant. Use ONLY the context. If not in context, reply exactly: NOT IN CORPUS. Cite source titles.\n\nCONTEXT:\n{context}\n\nQUESTION: {q}",
    "stream": False})
print(r.json()["response"])
