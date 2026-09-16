"""Recursa server: an authenticated, OpenAI-compatible front door for heavy AI.

Run it next to vLLM on a Vast.ai GPU, on a home server, or in front of the
Claude API so the key never sits on a learner's computer.

    RECURSA_TOKENS=tok1,tok2              bearer tokens accepted (required)
    UPSTREAM_OPENAI_URL=http://127.0.0.1:8000/v1   vLLM or any OpenAI-compatible server
    UPSTREAM_OPENAI_KEY=...               optional key for that upstream
    DEFAULT_MODEL=Qwen/Qwen3-235B-A22B-Instruct   what "auto" means upstream
    ANTHROPIC_API_KEY=...                 lets models named claude-* route to the Claude API
    EMBED_MODEL=BAAI/bge-small-en-v1.5    local embeddings via fastembed when installed
    RATE_PER_MINUTE=120                   per-token request limit
    uvicorn recursa_server.app:app --host 0.0.0.0 --port 8080
"""
import json
import os
import time
from collections import defaultdict, deque

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Recursa server")
UPSTREAM_TRANSPORT = None          # tests inject an httpx transport
_hits = defaultdict(deque)
_embedder = {}


def _cfg(name, default=""):
    return os.environ.get(name, default)


def auth(request: Request):
    tokens = {t.strip() for t in _cfg("RECURSA_TOKENS").split(",") if t.strip()}
    header = request.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if token not in tokens:
        # Invite codes: per-learner tokens with their own monthly limit.
        from recursa_server import invites
        refusal = invites.check(token) if token else (401, "invalid token")
        if refusal:
            raise HTTPException(status_code=refusal[0], detail=refusal[1])
    limit = int(_cfg("RATE_PER_MINUTE", "120"))
    now, q = time.time(), _hits[token]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="rate limit")
    q.append(now)
    return token


def _client(timeout=180):
    return httpx.AsyncClient(timeout=timeout, transport=UPSTREAM_TRANSPORT)


@app.get("/health")
async def health():
    return {"ok": True, "upstream": bool(_cfg("UPSTREAM_OPENAI_URL")), "anthropic": bool(_cfg("ANTHROPIC_API_KEY")),
            "embeddings": bool(_cfg("EMBED_MODEL"))}


@app.get("/v1/models")
async def models(_=Depends(auth)):
    data = []
    if _cfg("UPSTREAM_OPENAI_URL"):
        async with _client(20) as c:
            try:
                r = await c.get(_cfg("UPSTREAM_OPENAI_URL").rstrip("/") + "/models",
                                headers=_upstream_headers())
                data = r.json().get("data", [])
            except Exception:
                data = []
    if _cfg("ANTHROPIC_API_KEY"):
        data += [{"id": m, "object": "model"} for m in ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001")]
    return {"object": "list", "data": data}


def _upstream_headers():
    h = {"content-type": "application/json"}
    if _cfg("UPSTREAM_OPENAI_KEY"):
        h["authorization"] = "Bearer " + _cfg("UPSTREAM_OPENAI_KEY")
    return h


def openai_to_anthropic(body):
    system = "\n\n".join(m["content"] for m in body.get("messages", []) if m.get("role") == "system")
    msgs = []
    for m in body.get("messages", []):
        if m["role"] == "system":
            continue
        if m["role"] == "tool":
            msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": m["tool_call_id"],
                                                      "content": m.get("content", "")}]})
        elif m["role"] == "assistant" and m.get("tool_calls"):
            blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
            for tc in m["tool_calls"]:
                blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"],
                               "input": json.loads(tc["function"].get("arguments") or "{}")})
            msgs.append({"role": "assistant", "content": blocks})
        else:
            msgs.append({"role": m["role"], "content": m.get("content", "")})
    out = {"model": body["model"], "max_tokens": body.get("max_tokens", 700), "messages": msgs,
           "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}] if system else []}
    if body.get("temperature") is not None:
        out["temperature"] = body["temperature"]
    if body.get("tools"):
        out["tools"] = [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
                         "input_schema": t["function"].get("parameters", {"type": "object"})} for t in body["tools"]]
    return out


def anthropic_to_openai(data, model):
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    calls = [{"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
             for b in data.get("content", []) if b.get("type") == "tool_use"]
    msg = {"role": "assistant", "content": text or None}
    if calls:
        msg["tool_calls"] = calls
    return {"id": data.get("id", "msg"), "object": "chat.completion", "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if calls else "stop"}],
            "usage": data.get("usage", {})}


@app.post("/v1/chat/completions")
async def chat(request: Request, _=Depends(auth)):
    body = await request.json()
    model = body.get("model") or "auto"
    if model.startswith("claude"):
        if not _cfg("ANTHROPIC_API_KEY"):
            raise HTTPException(status_code=400, detail="claude models need ANTHROPIC_API_KEY on the server")
        if body.get("stream"):
            body = dict(body, stream=False)
        async with _client() as c:
            r = await c.post(_cfg("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages",
                             headers={"x-api-key": _cfg("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
                                      "content-type": "application/json"}, json=openai_to_anthropic(body))
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text[:300])
        from recursa_server import invites
        invites.record(_, model, r.json().get("usage"), paid=True)
        return JSONResponse(anthropic_to_openai(r.json(), model))
    if not _cfg("UPSTREAM_OPENAI_URL"):
        raise HTTPException(status_code=503, detail="no upstream model server configured")
    if model == "auto":
        body["model"] = _cfg("DEFAULT_MODEL") or model
    url = _cfg("UPSTREAM_OPENAI_URL").rstrip("/") + "/chat/completions"
    if body.get("stream"):
        async def relay():
            async with _client() as c:
                async with c.stream("POST", url, headers=_upstream_headers(), json=body) as r:
                    async for chunk in r.aiter_raw():
                        yield chunk
        return StreamingResponse(relay(), media_type="text/event-stream")
    async with _client() as c:
        r = await c.post(url, headers=_upstream_headers(), json=body)
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text[:300])
    from recursa_server import invites
    invites.record(_, body.get("model"), r.json().get("usage"), paid=False)
    return JSONResponse(r.json())


@app.post("/v1/embeddings")
async def embeddings(request: Request, _=Depends(auth)):
    body = await request.json()
    inputs = body.get("input") or []
    inputs = [inputs] if isinstance(inputs, str) else inputs
    if _cfg("EMBED_MODEL"):
        try:
            from fastembed import TextEmbedding
            model = _embedder.setdefault(_cfg("EMBED_MODEL"), TextEmbedding(_cfg("EMBED_MODEL")))
            vecs = [list(map(float, v)) for v in model.embed(inputs)]
            return {"object": "list", "data": [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vecs)],
                    "model": _cfg("EMBED_MODEL")}
        except ImportError:
            pass
    if _cfg("UPSTREAM_OPENAI_URL"):
        async with _client() as c:
            r = await c.post(_cfg("UPSTREAM_OPENAI_URL").rstrip("/") + "/embeddings", headers=_upstream_headers(), json=body)
        return JSONResponse(r.json(), status_code=r.status_code)
    raise HTTPException(status_code=503, detail="no embedding backend")
