#!/usr/bin/env python3
# overseer.py v4 — A Mirror of My Becoming orchestrator
# Owner architecture, Oct 11 2026: checkpoint workers, adaptive armor (threat levels),
# RRF fusion, granite judge, state-file resume, heartbeat, W5-portfolio (manifest canon).
# Doctrine: the machine fails definitely; the architecture assumes it.
import sys, os, json, time, requests, chromadb, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror_failsafe as fs

T0 = time.time()
Q = " ".join(a for a in sys.argv[1:]) or "What is in this corpus?"
LOG = os.path.expanduser("~/Mirror-Food/ask-productivity.jsonl")
HOME = os.path.expanduser
PAPERS = HOME("~/repos/qaevelyn.github.io/white-papers/manifest.json")

def ollama_generate(model, prompt, servers, timeout=600, options=None):
    """Try servers in order. Returns (text, server) or raises. options = ollama sampling dict."""
    last = None
    for p in servers:
        try:
            payload = {"model": model, "prompt": prompt, "stream": False}
            if options: payload["options"] = options
            r = requests.post(f"http://localhost:{p}/api/generate", timeout=timeout, json=payload)
            return r.json()["response"], p
        except Exception as e:
            last = e
    raise last or RuntimeError("no model server")

def ollama_embed(q, servers):
    for p in servers:
        try:
            return requests.post(f"http://localhost:{p}/api/embeddings", timeout=60,
                json={"model": "nomic-embed-text", "prompt": q}).json()["embedding"]
        except Exception: continue
    raise RuntimeError("no embedding server")

log_entry = {"question": Q, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), **fs.now(), "workers": []}

def worker(name, fn, hb):
    t0 = time.time()
    try:
        hits = fn()
        dt = round(time.time()-t0, 2)
        log_entry["workers"].append({"worker": name, "hits": len(hits), "latency_s": dt, "status": "ok"})
        hb("done", f"{len(hits)} hits in {dt}s")
        print(f"  [{name}] {len(hits)} hits in {dt}s")
        return hits
    except Exception as e:
        log_entry["workers"].append({"worker": name, "hits": 0, "status": f"error: {str(e)[:60]}"})
        hb("error", str(e)[:60]); print(f"  [{name}] ERROR: {str(e)[:60]}")
        return []

def vec_worker(coll, servers, hb, n=4):
    def fn():
        emb = ollama_embed(Q, servers)
        c = chromadb.PersistentClient(path=HOME("~/Mirror-Food/vector-store"))
        r = c.get_collection(coll).query(query_embeddings=[emb], n_results=n)
        hb("queried", coll)
        return list(zip(r["documents"][0], r["metadatas"][0]))
    return fn

def w4_sql():
    SPAM = ("gift car", "cock ", "cum hard", "verify or update your payment", "suspend your account today", "lottery", "crypto giveaway", "limited time offer", "a document is ready for")
    conn = sqlite3.connect(HOME("~/.msgvault/msgvault.db")); conn.row_factory = sqlite3.Row
    hits = []
    for word in Q.split():
        if len(word) >= 4:
            for r in conn.execute("""SELECT m.sent_at, p.email_address AS sender, m.subject, mb.body_text
                FROM messages m LEFT JOIN participants p ON p.id = m.sender_id
                LEFT JOIN message_bodies mb ON mb.message_id = m.id
                WHERE LOWER(m.subject) LIKE ?
                ORDER BY m.sent_at DESC LIMIT 3""", (f"%{word.lower()}%",)):
                subj = (r["subject"] or "").lower()
                if any(sp in subj for sp in SPAM): continue
                hits.append((f"[EMAIL {r['sent_at'][:10]} | {r['subject']}] {r['body_text'] or ''}",))
    return list(set(hits))[:4]

def w5_portfolio():
    """Portfolio questions answered from CANON (manifest + evidence), never hardcoded."""
    hits = []
    try:
        m = json.load(open(PAPERS))["white_papers"]
        hits.append((f"[PORTFOLIO CANON] White papers published: {len(m)}. Latest: " +
            "; ".join(f"{p['id']} ({p.get('date','?')})" for p in m[:5]),))
    except Exception: pass
    try:
        e = json.load(open(HOME("~/repos/qaevelyn.github.io/site/evidence.json")))["evidence_ledger"]
        for a in e.get("counted_artifacts", []):
            hits.append((f"[EVIDENCE LEDGER] {a['artifact']} — count: {a.get('count','n/a')} — {a.get('source','')}",))
    except Exception: pass
    return hits[:6]

def rrf_fuse(results, names=None, k=60):
    """RRF + quorum visibility: score, supporting workers, rank per worker."""
    names = names or [f"W{i+1}" for i in range(len(results))]
    scores, backers = {}, {}
    for nm, hits in zip(names, results):
        best = {}  # each worker votes ONCE per chunk — its best rank (quorum = distinct workers)
        for rank, h in enumerate(hits):
            if isinstance(h, dict): continue
            text = h[0] if isinstance(h, tuple) else h
            text = str(text).strip()
            if len(text) < 10: continue  # empty-text guard
            key = text[:100]
            r = rank + 1
            if key not in best or r < best[key]: best[key] = r
        for key, r in best.items():
            scores[key] = scores.get(key, 0) + 1/(k + r)
            backers.setdefault(key, []).append(f"{nm}(#{r})")
    order = sorted(scores.items(), key=lambda x: -x[1])
    return [(key, score, backers.get(key, [])) for key, score in order]

def canon_answer(Q):
    """TIER 1: quorum-decidable questions answered directly from canon — raw, no model.
    Owner ruling Oct 11 1:06 PM: 'it was a math question with a math answer.'"""
    ql = Q.lower()
    import re as _re
    try:
        papers = json.load(open(PAPERS))["white_papers"]
    except Exception:
        return None
    n = len(papers)
    latest = papers[0] if papers else None
    if "how many" in ql and ("paper" in ql or "work" in ql or "publication" in ql):
        titles = "; ".join(p["id"] for p in papers[:5])
        return f"CANON ANSWER (white-papers/manifest.json, read at query time):\n  White papers published: {n}\n  Five most recent: {titles}\n  (No model was consulted. The registry is the answer.)"
    if "latest" in ql and ("paper" in ql or "publication" in ql):
        return f"CANON ANSWER (white-papers/manifest.json):\n  Latest: {latest['id']} ({latest.get('date','?')})\n  (No model was consulted.)"
    if ("what is dv14" in ql or "what is protocol companion" in ql):
        e = json.load(open(HOME("~/repos/qaevelyn.github.io/site/evidence.json")))["evidence_ledger"]
        claims = [c["claim"] for c in e.get("published_verifiable", []) if "DV14" in c["claim"] or "Protocol Companion" in c["claim"] or "adversarial" in c["claim"].lower()]
        if claims:
            return "CANON ANSWER (site/evidence.json):\n  " + "\n  ".join(c[:200] for c in claims[:3])
    return None

def main():
    tier1 = canon_answer(Q)
    if tier1:
        print(tier1)
        log_entry.update({"tier": "canon-direct", "model_used": False})
        with open(LOG, "a") as f: f.write(json.dumps(log_entry) + "\n")
        print(f"\n[CANON TIER: answered from registry, no model consulted | logged: {LOG}]")
        return
    level, servers, problems = fs.preflight()
    if problems and not servers:
        print("=== RED: no model server. Start Ollama or the backup on 11435. ==="); sys.exit(1)
    prev = fs.load_state()
    if prev and prev.get("question") == Q and prev.get("stage") == "pre_generation":
        print(f"=== RESUME: state file has verified context for this exact question ({prev['saved']['z']}) — skipping re-query ===")
        verified = [(c["chunk"], c.get("score", 0), c.get("workers", [])) for c in prev["payload"].get("quorum", prev["payload"].get("chunks", []))]
        level = prev["payload"]["level"]; quorum_fresh = False
        print("=== QUORUM: restored from state (original run's deliberation) ===")
    else:
        print(f"=== OVERSEER v4 [{level}]: dispatching '{Q[:60]}' ===")
        hb = lambda stage, note="": fs.heartbeat("overseer", stage, note)
        w_order = [("W1-deepseek", vec_worker("deepseek_conversations", servers, hb)),
                   ("W2-emails", vec_worker("mirror_food_emails", servers, hb)),
                   ("W3-working", vec_worker("working_documents", servers, hb)),
                   ("W4-sql", w4_sql), ("W5-portfolio", w5_portfolio)]
        results = [worker(nm, fn, hb) for nm, fn in w_order]
        wnames = [nm for nm, _ in w_order]
        fused = rrf_fuse(results, wnames)
        seen, verified = set(), []
        for key, score, who in fused:
            if key in seen: continue
            seen.add(key)
            src = next((h for hits in results for h in hits
                        if not isinstance(h, dict) and str(h[0] if isinstance(h, tuple) else h)[:100] == key), None)
            verified.append(((src[0] if isinstance(src, tuple) else str(src)) if src else key, score, who))
        verified = verified[:12]
        print(f"=== FUSED: {len(verified)} chunks (RRF) in {round(time.time()-T0,2)}s total ===")
        print("=== QUORUM: score | backing workers(rank) | chunk head ===")
        quorum_rows = []
        for key, score, who in verified:
            print(f"  {score:.4f} | {','.join(who)} | {key[:60]}")
            quorum_rows.append({"score": score, "workers": who, "chunk": key[:120]})
        log_entry["quorum"] = quorum_rows
        fs.save_state("pre_generation", {"question": Q, "level": level, "chunks": verified[:8]})
    context = "\n\n".join(h[0] for h in verified)
    judge_note = ""
    if level != "GREEN" and verified:
        try:
            jr, _ = ollama_generate("granite4.1:3b",
                f"Rate each numbered context chunk 0-10 for relevance to the question. Reply only 'N:score' lines.\n\nQUESTION: {Q}\n\n" +
                "\n".join(f"{i+1}: {v[0][:300]}" for i, v in enumerate(verified)), servers, timeout=120)
            judge_note = f" [judge@{level}: {jr[:120]}]"
            print(f"=== JUDGE ({level}): scores logged ===")
        except Exception as e:
            judge_note = f" [judge skipped: {str(e)[:40]}]"
    ql = Q.lower()
    portfolio_q = any(p in ql for p in ("how many", "what is the latest", "what ships", "which ships", "publication"))
    if portfolio_q:
        options = {"temperature": 0.1, "top_p": 0.9}
        grounding = "You are a grounded assistant. Use ONLY the context. For counts, titles, and dates use ONLY it and never invent entries. If the answer is not in the context, reply exactly: NOT IN CORPUS. Cite source titles."
    else:
        options = {"temperature": 0.4, "top_p": 0.9}
        grounding = "You are a grounded assistant. Synthesize an answer from the context documents. If the context does not contain enough to answer, reply exactly: NOT IN CORPUS. Cite the source titles you used."
    prompt = grounding + "\n\nCONTEXT:\n" + context + "\n\nQUESTION: " + Q
    answer, used = ollama_generate("granite4.1:3b", prompt, servers, options=options)
    print(f"=== ANSWER (granite4.1:3b via {used}, grounded) ===\n")
    log_entry.update({"tier": "portfolio" if portfolio_q else "corpus", "temperature": options["temperature"], "level": level, "verified_chunks": len(verified), "fusion": [v[1] for v in verified[:6]], "judge": judge_note.strip(), "server_used": used})
    with open(LOG, "a") as f: f.write(json.dumps(log_entry) + "\n")
    print(answer + f"\n\n[logged: {LOG} | level {level} | {len(verified)} chunks]")

if __name__ == "__main__":
    main()
