import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import httpx
from fastapi.testclient import TestClient
import recursa_server.app as srv
fails = []
def check(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{d}]" if d and not c else "")); c or fails.append(n)
seen = {}
def handler(request):
    body = json.loads(request.content or b"{}")
    seen.setdefault(request.url.path, []).append(body)
    if request.url.path.endswith("/v1/messages"):
        return httpx.Response(200, json={"id": "m1", "content": [{"type": "tool_use", "id": "t1", "name": "search_law", "input": {"query": "escrow"}}], "usage": {}})
    if request.url.path.endswith("/chat/completions"):
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "hello from vllm"}}]})
    return httpx.Response(404)
srv.UPSTREAM_TRANSPORT = httpx.MockTransport(handler)
os.environ.update(RECURSA_TOKENS="good", UPSTREAM_OPENAI_URL="http://vllm/v1", DEFAULT_MODEL="big-model", ANTHROPIC_API_KEY="sk-unique-secret-77",
                  ANTHROPIC_BASE_URL="http://anthropic", RATE_PER_MINUTE="3")
c = TestClient(srv.app)
check("server: requests without a token are refused", c.post("/v1/chat/completions", json={}).status_code == 401)
r = c.post("/v1/chat/completions", headers={"authorization": "Bearer good"}, json={"model": "auto", "messages": [{"role": "user", "content": "hi"}]})
check("server: auto routes to the upstream with its default model", r.status_code == 200 and seen["/v1/chat/completions"][-1]["model"] == "big-model", r.text)
r = c.post("/v1/chat/completions", headers={"authorization": "Bearer good"}, json={"model": "claude-opus-5", "messages": [
    {"role": "system", "content": "sys"}, {"role": "user", "content": "q"}], "tools": [{"type": "function", "function": {"name": "search_law", "parameters": {"type": "object"}}}]})
sent = seen["/v1/messages"][-1]
check("server: claude models are translated to the Messages API with prompt caching",
      sent["system"][0]["cache_control"]["type"] == "ephemeral" and sent["tools"][0]["name"] == "search_law")
check("server: tool calls come back in OpenAI form", r.json()["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "search_law")
codes = [c.post("/v1/chat/completions", headers={"authorization": "Bearer good"}, json={"model": "auto", "messages": []}).status_code for _ in range(2)]
check("server: the per-token rate limit applies", codes[-1] == 429, codes)
check("server: the Anthropic key never appears in a response", "sk-unique-secret-77" not in json.dumps(c.get("/health").json()) + r.text)
print(len(fails), "failures"); sys.exit(1 if fails else 0)
