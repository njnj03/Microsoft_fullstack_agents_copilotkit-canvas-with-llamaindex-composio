# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os, re, hashlib, time, pathlib
from typing import List, Optional, Dict, Any

from llama_index.core import (
    Document, VectorStoreIndex, StorageContext, load_index_from_storage
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.vector_stores import SimpleVectorStore  # <-- correct path
from fastapi import Query

from dotenv import load_dotenv
load_dotenv()

from fastapi import UploadFile, File

# ---------- Config ----------
PERSIST_DIR = os.getenv("MINUTES_PERSIST_DIR", "./storage/vector")  # one global collection
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "text-embedding-3-small")
pathlib.Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)

# One-time objects
embed_model = OpenAIEmbedding(model=EMBED_MODEL_NAME)
parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# ---------- Schemas ----------
class MinutesIn(BaseModel):
    meeting_id: str = Field(..., description="Unique meeting identifier")
    text: str = Field(..., description="Raw transcript text (as from STT)")
    source: Optional[str] = Field("google_meet", description="Origin of transcript")
    participants: Optional[List[str]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

class IngestResult(BaseModel):
    meeting_id: str
    chunks: int
    characters: int
    checksum: str
    persisted_dir: str

# ---------- Helpers ----------
def clean_transcript(text: str) -> str:
    """Minimal, safe normalizer—tune to your needs."""
    # lower-casing for normalization (optional)
    t = text.lower()
    # remove common fillers (keep it conservative)
    t = re.sub(r"\b(uh|um|you know|like)\b", "", t)
    # collapse spaces/newlines
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()

def checksum(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def load_or_create_index():
    """Load existing index if present, otherwise create an empty one."""
    # If storage exists, load; else create with a fresh vector store
    if any(pathlib.Path(PERSIST_DIR).iterdir()):
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        return load_index_from_storage(storage_context)
    else:
        vector_store = SimpleVectorStore()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        # Create an empty index by inserting nothing yet; we’ll upsert nodes later
        return VectorStoreIndex([], storage_context=storage_context, embed_model=embed_model)

# ---------- App ----------
app = FastAPI(title="Minutes Ingestion API", version="1.0")


@app.post("/ingest/minutes-file")
async def ingest_minutes_file(meeting_id: str, file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="replace")
    return ingest_minutes(MinutesIn(meeting_id=meeting_id, text=content, source="file_upload"))


@app.get("/health")
def health():
    return {"ok": True}

from pathlib import Path
import json
from fastapi import Query

@app.get("/debug/nodes")
def debug_nodes(meeting_id: str = Query(...)):
    fp = Path(PERSIST_DIR) / "docstore.json"
    if not fp.exists():
        return {"meeting_id": meeting_id, "count": 0, "nodes": [], "note": f"{fp} not found"}

    data = json.loads(fp.read_text(encoding="utf-8"))
    nodes = []
    data_nodes = (data.get("docstore/data") or {})
    for node_id, payload in data_nodes.items():
        d = payload.get("__data__", {})
        meta = d.get("metadata", {})
        txt = d.get("text", "") or ""
        if meta.get("meeting_id") == meeting_id:
            nodes.append({
                "node_id": node_id,
                "chars": len(txt),
                "preview": txt[:300],
                "metadata": meta,
            })

    return {"meeting_id": meeting_id, "count": len(nodes), "nodes": nodes}

@app.post("/ingest/minutes", response_model=IngestResult)
def ingest_minutes(payload: MinutesIn):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    cleaned = clean_transcript(payload.text)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Empty transcript after cleaning")

    # Build a document with useful metadata
    doc = Document(
        text=cleaned,
        metadata={
            "meeting_id": payload.meeting_id,
            "source": payload.source,
            "participants": payload.participants or [],
            "ingested_at": int(time.time()),
            **(payload.metadata or {}),
        },
    )

    nodes = parser.get_nodes_from_documents([doc])

    # Load or create index, then upsert nodes
    index = load_or_create_index()
    index.insert_nodes(nodes)  # upsert
    index.storage_context.persist(persist_dir=PERSIST_DIR)

    return IngestResult(
        meeting_id=payload.meeting_id,
        chunks=len(nodes),
        characters=len(cleaned),
        checksum=checksum(cleaned),
        persisted_dir=str(PERSIST_DIR),
    )

# (Optional) quick query endpoint to sanity-check ingestion
class QueryIn(BaseModel):
    query: str

@app.post("/query")
def query_minutes(q: QueryIn):
    index = load_or_create_index()
    resp = index.as_query_engine().query(q.query)
    return {"answer": str(resp)}

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from collections import defaultdict

class RetrieveIn(BaseModel):
    prompt: str
    top_k: int = 8
    include_full_text: bool = False
    group_by_meeting: bool = False
    per_meeting_k: int = 3
    meeting_ids: Optional[List[str]] = None  # optional filter
    oversample: int = 4                      # fetch more, then filter
    min_score: float = 0.25                  # drop low-similarity junk

class RetrieveOut(BaseModel):
    prompt: str
    count: int
    total_candidates: int
    matches: List[Dict[str, Any]]
    groups: Optional[List[Dict[str, Any]]] = None  # present when group_by_meeting=True

def _node_text(sn):
    node = getattr(sn, "node", None)
    if node is not None:
        try:
            return node.get_text() or ""
        except Exception:
            return getattr(sn, "get_text", lambda: "")() or ""
    return getattr(sn, "get_text", lambda: "")() or ""

def _node_meta(sn):
    node = getattr(sn, "node", None)
    if node is not None:
        return getattr(node, "metadata", {}) or {}
    return getattr(sn, "metadata", {}) or {}

def _node_id(sn):
    node = getattr(sn, "node", None)
    if node is not None:
        return getattr(node, "node_id", None) or getattr(node, "id_", "")
    return getattr(sn, "node_id", "") or ""

def _meeting_id(meta: Dict[str, Any]) -> str:
    return (meta.get("meeting_id")
            or meta.get("meetingId")
            or "unknown")

@app.post("/retrieve", response_model=RetrieveOut)
def retrieve(q: RetrieveIn):
    index = load_or_create_index()

    # fetch more candidates than needed
    k = max(1, q.top_k)
    k_fetch = max(k, k * max(1, q.oversample))

    # add simple postprocessors (if available)
    try:
        from llama_index.core.postprocessor import LongContextReorder, SimilarityPostprocessor
        qe = index.as_query_engine(
            response_mode="no_text",
            similarity_top_k=k_fetch,
            node_postprocessors=[
                LongContextReorder(),
                # We'll also do a manual cutoff below so we can return max_score
            ],
        )
    except Exception:
        qe = index.as_query_engine(response_mode="no_text", similarity_top_k=k_fetch)

    resp = qe.query(q.prompt)

    raw = []
    for sn in getattr(resp, "source_nodes", []) or []:
        node = getattr(sn, "node", None)
        text = node.get_text() if node else getattr(sn, "get_text", lambda: "")()
        meta = node.metadata if node else getattr(sn, "metadata", {})
        mid = meta.get("meeting_id", "unknown")
        score = float(getattr(sn, "score", 0.0) or 0.0)

        if q.meeting_ids and mid not in q.meeting_ids:
            continue

        raw.append({
            "node_id": getattr(node, "node_id", None) or getattr(sn, "node_id", ""),
            "score": score,
            "text": text,
            "metadata": meta,
            "meeting_id": mid,
        })

    total_candidates = len(raw)
    if not raw:
        return RetrieveOut(
            prompt=q.prompt, count=0, total_candidates=0, max_score=0.0,
            matches=[], groups=None, note="No candidates retrieved."
        )

    # filter by similarity cutoff (as before)
    raw = [r for r in raw if r["score"] >= q.min_score]
    raw.sort(key=lambda x: x["score"], reverse=True)
    max_score = raw[0]["score"] if raw else 0.0

    # NEW: graceful fallback if nothing passes the cutoff
    if not raw:
        # take the best k even if below cutoff, but annotate why
        # (use the original unfiltered list, already in `all_candidates`)
        all_candidates = sorted(
            (r for r in (getattr(resp, "source_nodes", []) or [])),
            key=lambda s: float(getattr(s, "score", 0.0) or 0.0),
            reverse=True,
        )
        # rebuild entries the same way as before
        fallback = []
        for sn in all_candidates:
            node = getattr(sn, "node", None)
            text = node.get_text() if node else getattr(sn, "get_text", lambda: "")()
            meta = node.metadata if node else getattr(sn, "metadata", {})
            fallback.append({
                "node_id": getattr(node, "node_id", None) or getattr(sn, "node_id", ""),
                "score": float(getattr(sn, "score", 0.0) or 0.0),
                "text": text,
                "metadata": meta,
                "meeting_id": meta.get("meeting_id", "unknown"),
            })
        raw = fallback[:k]
        max_score = raw[0]["score"] if raw else 0.0
        fallback_note = f"No results met min_score; returning top {len(raw)} by score (max_score={max_score:.3f})."
    else:
        fallback_note = None

    # build matches (truncate text if needed)
    def preview(txt: str) -> str:
        return txt if q.include_full_text or len(txt) <= 500 else txt[:500] + "…"

    matches = [{
        "node_id": r["node_id"],
        "score": r["score"],
        "text": preview(r["text"]),
        "metadata": r["metadata"],
    } for r in raw[:k]]

    # optional grouping
    groups = None
    if q.group_by_meeting:
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for r in raw:
            buckets.setdefault(r["meeting_id"], [])
            if len(buckets[r["meeting_id"]]) < q.per_meeting_k:
                buckets[r["meeting_id"]].append({
                    "node_id": r["node_id"],
                    "score": r["score"],
                    "text": preview(r["text"]),
                    "metadata": r["metadata"],
                })
        groups = [{"meeting_id": mid, "matches": ms} for mid, ms in buckets.items()]

    return RetrieveOut(
        prompt=q.prompt,
        count=len(matches),
        total_candidates=total_candidates,
        max_score=max_score,
        matches=matches,
        groups=groups,
        note=None if matches else f"No results above min_score={q.min_score}",
    )

from llama_index.llms.openai import OpenAI
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AnswerIn(BaseModel):
    prompt: str = "Extract action items across all meeting minutes with owner and due date if present."
    top_k: int = 12
    oversample: int = 5
    include_full_text: bool = False

class AnswerOut(BaseModel):
    used_nodes: List[Dict[str, Any]]
    answer: Optional[str] = None   # present if OPENAI_API_KEY set
    note: Optional[str] = None

@app.post("/answer", response_model=AnswerOut)
def answer(q: AnswerIn):
    index = load_or_create_index()
    k = max(1, q.top_k)
    k_fetch = max(k, k * max(1, q.oversample))

    # retrieve with filters/postprocessors
    postprocs = [LongContextReorder(), SimilarityPostprocessor(similarity_cutoff=0.25)]
    qe = index.as_query_engine(response_mode="no_text", similarity_top_k=k_fetch, node_postprocessors=postprocs)
    resp = qe.query(q.prompt)

    # collect clean matches
    matches = []
    for sn in getattr(resp, "source_nodes", []) or []:
        node = getattr(sn, "node", None)
        text = (node.get_text() if node else getattr(sn, "get_text", lambda: "")()) or ""
        if _looks_junky(text): 
            continue
        meta = (getattr(node, "metadata", {}) if node else getattr(sn, "metadata", {})) or {}
        nid = (getattr(node, "node_id", None) or getattr(node, "id_", "") if node else getattr(sn, "node_id", ""))
        matches.append({
            "node_id": nid,
            "score": float(getattr(sn, "score", 0.0) or 0.0),
            "text": text if q.include_full_text else (text[:600] + ("…" if len(text) > 600 else "")),
            "metadata": meta,
        })

    # keep the best k
    matches.sort(key=lambda x: x["score"], reverse=True)
    matches = matches[:k]

    # if no key, return matches only
    if not os.getenv("OPENAI_API_KEY"):
        return AnswerOut(used_nodes=matches, note="No OPENAI_API_KEY set; returning retrieved chunks only.")

    # synthesize an answer focused on ACTION ITEMS
    llm = OpenAI(model="gpt-4o-mini")  # or gpt-4o if you prefer
    system = (
        "You are an assistant extracting ACTION ITEMS from meeting minutes across many meetings. "
        "Return ONLY a concise list. For each action: [Owner] — Task (Due date if present) — (Meeting ID). "
        "Use only the provided context. Do not invent owners or due dates."
    )
    context = "\n\n---\n\n".join(
        f"[meeting_id={m['metadata'].get('meeting_id','unknown')}] {m['text']}" for m in matches
    )
    user = f"{q.prompt}\n\nContext:\n{context}\n\nOutput format:\n- Owner — Task (Due: YYYY-MM-DD or 'none') — (meeting_id)"

    completion = llm.complete(f"{system}\n\n{user}")
    return AnswerOut(used_nodes=matches, answer=str(completion))

# ---------- Action Items: Retrieve & Extract (LLM-free) ----------
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from collections import defaultdict
import re

# Light junk filter (reuse if you already defined _looks_junky)
def _looks_junky(txt: str) -> bool:
    if not txt or len(txt.strip()) < 40:
        return True
    lo = txt.lower().strip()
    if lo == "$text":
        return True
    if "this is the content of your meeting minutes" in lo:
        return True
    return False

# Simple normalizers
def _meeting_id(meta: Dict[str, Any]) -> str:
    return (meta.get("meeting_id") or meta.get("meetingId") or "unknown")

def _node_text(sn) -> str:
    node = getattr(sn, "node", None)
    if node is not None:
        try:
            return node.get_text() or ""
        except Exception:
            return getattr(sn, "get_text", lambda: "")() or ""
    return getattr(sn, "get_text", lambda: "")() or ""

def _node_meta(sn) -> Dict[str, Any]:
    node = getattr(sn, "node", None)
    if node is not None:
        return getattr(node, "metadata", {}) or {}
    return getattr(sn, "metadata", {}) or {}

def _node_id(sn) -> str:
    node = getattr(sn, "node", None)
    if node is not None:
        return getattr(node, "node_id", None) or getattr(node, "id_", "")
    return getattr(sn, "node_id", "") or ""

# Heuristics for action items
RE_SPEAKER = re.compile(r"^(?:\[\d{1,2}:\d{2}:\d{2}\]\s*)?([A-Za-z][A-Za-z .'\-]{1,60}):\s*(.+)$", re.I)
RE_COMMIT  = re.compile(
    r"\b(i['’]?ll|i will|i can|i'm going to|i am going to|will|take ownership|own|handle|set up|prepare|finish|circulate|send|update|create|configure|investigate|fix|deploy|summarize|document|schedule|present|sync|align|follow up|reach out)\b",
    re.I
)
RE_DUE     = re.compile(
    r"\bby\s+(?:eod|eow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next week|"
    r"[A-Za-z]{3,9}\s+\d{1,2}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b",
    re.I
)

def _extract_items_from_text(text: str,
                             meta: Dict[str, Any],
                             node_id: str,
                             participants: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    items = []
    if not text:
        return items

    # split into short lines; STT often breaks on newlines already
    for raw_line in (l.strip() for l in text.splitlines() if l.strip()):
        if len(raw_line) < 20:
            continue

        owner = None
        content = raw_line

        # Try "Speaker: content"
        m = RE_SPEAKER.match(raw_line)
        if m:
            owner, content = m.group(1).strip(), m.group(2).strip()

        if not RE_COMMIT.search(content):
            # no commitment verb -> skip
            continue

        # Extract due date phrase if present
        due = None
        mdue = RE_DUE.search(content)
        if mdue:
            due = mdue.group(0).strip()  # keep raw phrase

        # Normalize task (remove leading commitment phrases)
        content_norm = re.sub(
            r"^(i['’]?ll|i will|i can|i am going to|i'm going to|let'?s|we will)\s+",
            "", content, flags=re.I
        ).strip()

        # Fallback: try to infer owner from first token if not found
        if not owner and participants:
            low = content.lower()
            for p in participants:
                name = str(p)
                if name and name.lower() in low[:60]:
                    owner = name
                    break

        # Confidence scoring (very rough)
        conf = 0.60
        if owner: conf += 0.20
        if due:   conf += 0.10
        if re.search(r"\b(i['’]?ll|i will|will)\b", content, re.I): conf += 0.05
        conf = min(conf, 0.95)

        items.append({
            "owner": owner or "unknown",
            "task": content_norm,
            "due": due or "none",
            "meeting_id": _meeting_id(meta),
            "node_id": node_id,
            "confidence": round(conf, 2),
        })
    return items

# Request/Response models
class ActionItemsIn(BaseModel):
    prompt: str = Field(
        "Extract action items with owners and due dates across all meetings.",
        description="Used only to steer retrieval; extraction is heuristic."
    )
    top_k: int = 20
    oversample: int = 5
    meeting_ids: Optional[List[str]] = None    # leave None to search ALL
    min_confidence: float = 0.55
    max_items: int = 50
    include_sources: bool = True               # include node_id + meeting_id in items

class ActionItemsOut(BaseModel):
    count: int
    items: List[Dict[str, Any]]
    scanned_nodes: int
    note: Optional[str] = None

@app.post("/action-items", response_model=ActionItemsOut)
def action_items(q: ActionItemsIn):
    index = load_or_create_index()

    k_fetch = max(q.top_k, q.top_k * max(1, q.oversample))

    # Optional postprocessors to improve retrieval quality
    try:
        from llama_index.core.postprocessor import LongContextReorder, SimilarityPostprocessor
        postprocs = [
            LongContextReorder(),
            SimilarityPostprocessor(similarity_cutoff=0.25),
        ]
        qe = index.as_query_engine(
            response_mode="no_text",
            similarity_top_k=k_fetch,
            node_postprocessors=postprocs,
        )
    except Exception:
        # fallback if postprocessors not available
        qe = index.as_query_engine(response_mode="no_text", similarity_top_k=k_fetch)

    # Pull candidates
    resp = qe.query(q.prompt)

    candidates = []
    for sn in getattr(resp, "source_nodes", []) or []:
        txt = _node_text(sn)
        if _looks_junky(txt):
            continue
        meta = _node_meta(sn)
        if q.meeting_ids and _meeting_id(meta) not in set(q.meeting_ids):
            continue
        candidates.append({"text": txt, "meta": meta, "node_id": _node_id(sn)})

    # Extract items from candidates
    out_items, seen = [], set()
    for c in candidates:
        parts = c["meta"].get("participants") or []
        items = _extract_items_from_text(c["text"], c["meta"], c["node_id"], parts)
        for it in items:
            if it["confidence"] < q.min_confidence:
                continue
            # de-dup on (owner, task, meeting_id)
            key = (it["owner"].lower(), re.sub(r"\s+", " ", it["task"].lower()).strip(), it["meeting_id"])
            if key in seen:
                continue
            seen.add(key)
            if not q.include_sources:
                it = {k: v for k, v in it.items() if k not in ("node_id")}
            out_items.append(it)
            if len(out_items) >= q.max_items:
                break
        if len(out_items) >= q.max_items:
            break

    return ActionItemsOut(
        count=len(out_items),
        items=out_items,
        scanned_nodes=len(candidates),
        note="LLM-free heuristic extraction; set up /answer for synthesized text if desired."
    )


# Run: uvicorn app:app --reload --port 9000
