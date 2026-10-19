#!/usr/bin/env python3
"""
Sloth — the lazy task triager.

Dump your messy brain-dump in, get a prioritized action plan out.
Powered by a local open-weight model (Gemma via Ollama): zero cost,
zero API keys, works offline, your words never leave your machine.

Usage:
    python sloth.py triage notes.txt          # triage a file
    cat notes.txt | python sloth.py triage    # ...or pipe it in
    python sloth.py triage notes.txt --json   # machine-readable output
    python sloth.py trace                     # show run traces (latency/tokens)

If Ollama/Gemma is not reachable, Sloth says so and falls back to a
transparent heuristic triager (clearly labeled -- never pretending
to be the model).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request

DEFAULT_MODEL = os.environ.get("SLOTH_MODEL", "gemma3:1b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TRACE_FILE = os.path.expanduser("~/.sloth/traces.jsonl")

SYSTEM_PROMPT = """You are Sloth, a lazy-but-wise task triager. The user dumps a messy \
list of tasks, notes and random thoughts. Your job: turn it into a short, \
prioritized action plan.

Rules:
- Deduplicate: merge items that are really the same task.
- Drop the noise: ignore greetings, jokes and non-tasks (list them under "ignored", max 3).
- Rank every real task 1-5 by impact-per-effort (1 = do first).
- Estimate effort for each: one of 15m, 30m, 1h, 2h, 4h, 1d, 2d+.
- Pick exactly one "sloth_pick": the single task to do first if the user is lazy.
- "ignored" is ONLY for greetings, laughter and thanks (hi, hey, lol, haha, \
thanks, ok). NEVER put a real task in "ignored" — a task is anything the user \
needs to do, buy, fix, call, book, send, prepare, or remember. When in doubt, \
it is a TASK, not ignored.
- Keep task titles under 12 words. Be concrete, not motivational-poster fluff.

Reply with ONLY valid JSON, no markdown fences, no commentary:
{
  "sloth_pick": "<the one task to do first>",
  "plan": [
    {"task": "<title>", "priority": 1, "effort": "30m", "why": "<<=15 words>"},
    ...
  ],
  "ignored": ["<non-task, max 3>"]
}"""

HEURISTIC_KEYWORDS = {
    1: ["urgent", "asap", "deadline", "today", "overdue", "critical", "broken",
        "down", "emergency", "now", "expire", "expires", "due"],
    2: ["important", "tomorrow", "this week", "meeting", "call", "email",
        "reply", "send", "fix", "review", "submit", "pay", "bill"],
    4: ["someday", "maybe", "eventually", "idea", "consider", "look into",
        "research", "learn"],
}


def call_ollama(prompt, model=DEFAULT_MODEL, timeout=180):
    """Call a local Ollama model. Returns (text, usage_dict). Raises on failure."""
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3, "num_predict": 1200},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL + "/api/generate", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    latency_ms = int((time.monotonic() - t0) * 1000)
    usage = {
        "model": data.get("model", model),
        "latency_ms": latency_ms,
        "prompt_tokens": data.get("prompt_eval_count", 0),
        "completion_tokens": data.get("eval_count", 0),
        "cost_usd": 0.0,
    }
    return data["response"], usage


def extract_json(text):
    """Pull a JSON object out of model output (tolerates fences/chatter)."""
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("no JSON object found in model output")


def heuristic_triage(raw):
    """Transparent keyword-based fallback. Never pretends to be the model."""
    lines = [ln.strip(" -•*\t") for ln in raw.splitlines()]
    plan, ignored = [], []
    for ln in lines:
        if not ln:
            continue
        low = ln.lower()
        if re.match(r"^(hi|hey|hello|lol|haha|ok|thanks|note to self:?)$", low):
            ignored.append(ln[:60])
            continue
        if len(ln) <= 3:
            continue
        prio = 3
        for p, words in HEURISTIC_KEYWORDS.items():
            if any(w in low for w in words):
                prio = min(prio, p)
        effort = "30m"
        if any(w in low for w in ["project", "report", "write", "build", "migrate"]):
            effort = "2h"
        plan.append({"task": ln[:90], "priority": prio, "effort": effort,
                     "why": "keyword heuristic (fallback mode)"})
    plan.sort(key=lambda t: t["priority"])
    pick = plan[0]["task"] if plan else "nothing to do — enjoy the sloth life"
    return {"sloth_pick": pick, "plan": plan, "ignored": ignored[:3],
            "_fallback": True}


def record_trace(usage, mode):
    try:
        os.makedirs(os.path.dirname(TRACE_FILE), exist_ok=True)
        with open(TRACE_FILE, "a") as f:
            f.write(json.dumps({"ts": dt.datetime.now(dt.timezone.utc).isoformat(),
                                "mode": mode, **usage}) + "\n")
    except OSError:
        pass


def render(result, json_out=False):
    if json_out:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    tag = " [heuristic fallback — no local model found]" if result.get("_fallback") else ""
    print(f"\n🦥 Sloth says: do this first → {result['sloth_pick']}{tag}\n")
    print(f"{'#':<3} {'Task':<52} {'Effort':<7} Why")
    print("-" * 100)
    for i, t in enumerate(result["plan"], 1):
        task = str(t.get("task", "?"))[:50]
        effort = str(t.get("effort", "?"))
        why = str(t.get("why", ""))
        print(f"{i:<3} {task:<52} {effort:<7} {why[:30]}")
    if result.get("ignored"):
        print("\nIgnored non-tasks: " + "; ".join(result["ignored"]))
    print()


def normalize(result):
    """Clean up 1B-model quirks: greetings in plan, placeholder text in ignored."""
    noise = re.compile(r"^(hi|hey|hello|lol|haha|ok|thanks|note to self:?)$",
                       re.I)
    plan, ignored = [], list(result.get("ignored") or [])
    for t in result.get("plan") or []:
        title = str(t.get("task", "")).strip()
        if noise.match(title):
            if title not in ignored:
                ignored.append(title)
        else:
            plan.append(t)
    ignored = [x for x in ignored
               if "<" not in str(x) and "non-task" not in str(x).lower()][:3]
    result["plan"] = plan
    result["ignored"] = ignored
    if plan and not result.get("sloth_pick"):
        result["sloth_pick"] = plan[0].get("task", "")
    return result


def looks_degenerate(result, raw):
    """A 1B model sometimes dumps everything into 'ignored'. Catch it."""
    input_lines = [ln for ln in raw.splitlines() if len(ln.strip()) > 3]
    plan = result.get("plan") or []
    return len(input_lines) >= 4 and len(plan) < 2


def cmd_triage(args):
    raw = args.file.read() if args.file else sys.stdin.read()
    if not raw.strip():
        print("Nothing to triage — pipe in a brain-dump or pass a file.", file=sys.stderr)
        return 2
    try:
        prompt = "Triage this brain-dump:\n\n" + raw
        text, usage = call_ollama(prompt, model=args.model)
        result = extract_json(text)
        if not isinstance(result.get("plan"), list) or not result.get("sloth_pick"):
            raise ValueError("model returned unexpected shape")
        if looks_degenerate(result, raw):
            # one retry with a firmer nudge; 1B models need it
            text, usage = call_ollama(
                prompt + "\n\nIMPORTANT: almost everything above is a real task. "
                "Put at most 2 items in 'ignored'.", model=args.model)
            result = extract_json(text)
            if not isinstance(result.get("plan"), list) or not result.get("sloth_pick"):
                raise ValueError("model returned unexpected shape on retry")
        result = normalize(result)
        record_trace(usage, mode="gemma")
        if not args.quiet:
            u = usage
            print(f"[gemma:{u['model']} {u['latency_ms']}ms "
                  f"in={u['prompt_tokens']} out={u['completion_tokens']} $0.00]",
                  file=sys.stderr)
    except Exception as e:
        print(f"[local model unavailable ({e}); using heuristic fallback]",
              file=sys.stderr)
        result = heuristic_triage(raw)
        record_trace({"model": "heuristic", "latency_ms": 0,
                      "prompt_tokens": 0, "completion_tokens": 0,
                      "cost_usd": 0.0}, mode="heuristic")
    render(result, json_out=args.json)
    return 0


def cmd_trace(_args):
    if not os.path.exists(TRACE_FILE):
        print("No traces yet — run `sloth triage` first.")
        return 0
    print(f"{'time':<26} {'mode':<10} {'model':<14} {'ms':>7} "
          f"{'in':>5} {'out':>5} {'cost':>6}")
    with open(TRACE_FILE) as f:
        for line in f:
            t = json.loads(line)
            print(f"{t['ts'][:19]:<26} {t['mode']:<10} {t['model'][:13]:<14} "
                  f"{t['latency_ms']:>7} {t['prompt_tokens']:>5} "
                  f"{t['completion_tokens']:>5} ${t['cost_usd']:>5.2f}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="sloth",
                                description="The lazy task triager (local Gemma).")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("triage", help="triage a messy brain-dump")
    t.add_argument("file", nargs="?", type=argparse.FileType("r"),
                   help="text file (default: stdin)")
    t.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model to use")
    t.add_argument("--json", action="store_true", help="JSON output")
    t.add_argument("--quiet", action="store_true", help="hide the trace line")
    t.set_defaults(func=cmd_triage)
    tr = sub.add_parser("trace", help="show run traces (latency/tokens/cost)")
    tr.set_defaults(func=cmd_trace)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
