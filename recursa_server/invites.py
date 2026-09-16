"""Invite codes for a Recursa server: one code per learner, each with its own
monthly spending limit, revocable at any time.

    python -m recursa_server.invites create --label "Maria" --limit 5 --url https://my-server.example/v1
    python -m recursa_server.invites list
    python -m recursa_server.invites revoke --label "Maria"

Codes are stored in INVITES_FILE (default invites.json next to the server).
The code a learner pastes carries the server address and a random token; the
server checks the token, meters Claude calls against its limit, and refuses
with HTTP 402 once the month's limit is reached. Calls to your own GPU cost
nothing and are counted, not charged.
"""
import argparse, base64, hashlib, json, os, secrets, threading, time

_LOCK = threading.Lock()
PRICES = {"claude-haiku-4-5": (1.0, 5.0), "claude-sonnet-5": (3.0, 15.0)}
UNKNOWN_PRICE = (15.0, 75.0)          # conservative until the owner sets PRICES_JSON


def _path():
    return os.environ.get("INVITES_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "invites.json"))


def _load():
    try:
        with open(_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"tokens": {}}


def _save(data):
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, _path())


def _month():
    return time.strftime("%Y-%m")


def make_code(url, token, label=""):
    payload = base64.urlsafe_b64encode(json.dumps({"u": url, "t": token, "n": label}, separators=(",", ":"))
                                       .encode()).decode().rstrip("=")
    return f"RCS1-{payload}-{hashlib.sha256(payload.encode()).hexdigest()[:6]}"


def create(label, monthly_limit_usd, url):
    token = secrets.token_urlsafe(24)
    with _LOCK:
        data = _load()
        data["tokens"][token] = {"label": label, "limit": float(monthly_limit_usd), "month": _month(),
                                 "spent": 0.0, "requests": 0, "revoked": False}
        _save(data)
    return make_code(url, token, label)


def revoke(label):
    with _LOCK:
        data = _load()
        n = 0
        for t in data["tokens"].values():
            if t["label"] == label and not t["revoked"]:
                t["revoked"] = True
                n += 1
        _save(data)
    return n


def check(token):
    """None if the token may be used, else (status, reason)."""
    data = _load()
    t = data["tokens"].get(token)
    if t is None:
        return 401, "invalid token"
    if t["revoked"]:
        return 401, "this invite was revoked"
    if t["month"] == _month() and t["spent"] >= t["limit"]:
        return 402, "this invite's monthly limit is reached"
    return None


def price(model):
    table = dict(PRICES)
    try:
        table.update({k: tuple(v) for k, v in json.loads(os.environ.get("PRICES_JSON", "{}")).items()})
    except ValueError:
        pass
    best = max((k for k in table if str(model).startswith(k)), key=len, default=None)
    return table[best] if best else UNKNOWN_PRICE


def record(token, model, usage, paid):
    u = usage or {}
    cost = 0.0
    if paid:
        pin, pout = price(model)
        cost = (int(u.get("input_tokens") or u.get("prompt_tokens") or 0) * pin
                + int(u.get("cache_creation_input_tokens") or 0) * pin * 1.25
                + int(u.get("cache_read_input_tokens") or 0) * pin * 0.10
                + int(u.get("output_tokens") or u.get("completion_tokens") or 0) * pout) / 1e6
    with _LOCK:
        data = _load()
        t = data["tokens"].get(token)
        if t is None:
            return cost
        if t["month"] != _month():
            t.update(month=_month(), spent=0.0, requests=0)
        t["spent"] += cost
        t["requests"] += 1
        _save(data)
    return cost


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("--label", required=True); c.add_argument("--limit", type=float, required=True)
    c.add_argument("--url", required=True)
    r = sub.add_parser("revoke"); r.add_argument("--label", required=True)
    sub.add_parser("list")
    a = ap.parse_args(argv)
    if a.cmd == "create":
        print(create(a.label, a.limit, a.url))
    elif a.cmd == "revoke":
        print(f"revoked {revoke(a.label)}")
    else:
        for tok, t in _load()["tokens"].items():
            print(f"{t['label']}: ${t['spent']:.2f} of ${t['limit']:.2f} this month, {t['requests']} requests"
                  + (" (revoked)" if t["revoked"] else ""))


if __name__ == "__main__":
    main()
