# 🦥 Sloth — the lazy task triager

*Dump your brain. Sloth sorts it.*

Sloth takes a messy brain-dump — half-formed tasks, notes, random thoughts,
copy-pasted reminders — and hands back a short, prioritized action plan with
time estimates and one "do this first" pick. You never organize; the sloth
does. Built for the Hacktoberfest 2026 DEV Open-Source AI Challenge, Week 3:
**Slow and Steady** (build something with open-source AI that rewards laziness).

## How it works

```
$ python sloth.py triage examples/brain-dump.txt

🦥 Sloth says: do this first → URGENT: reply to client about the invoice

#   Task                                     Effort  Why
------------------------------------------------------------------
1   URGENT: reply to client about invoice    30m     deadline pressure, asked twice
2   fix the leaking kitchen sink             1h      hard deadline (Friday visit)
...
```

The reasoning is done by **Gemma** (Google's open-weight model) running
**locally via Ollama** — no API keys, no cloud, zero cost per run, and your
words never leave your machine. If no local model is reachable, Sloth says so
out loud and falls back to a transparent keyword heuristic (clearly labeled,
never pretending to be the model).

Every run records a trace (`sloth trace`): model, latency, input/output tokens,
cost ($0.00 — that's the point).

## Quickstart

```bash
# 1. Get Ollama + a Gemma model (one time)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:1b

# 2. Triage
python sloth.py triage my-tasks.txt
cat my-tasks.txt | python sloth.py triage --json   # machine-readable
python sloth.py trace                              # latency / tokens / cost
```

No `pip install`. Python 3.10+ stdlib only.

## Honest limits

- A small local model (1B) occasionally misreads a task — **verify before
  acting on anything important** (money, health, legal).
- English-first; messy mixed-language dumps can confuse it.
- The heuristic fallback is dumb on purpose — it ranks by keywords only.
- Not a planner, not a therapist, not a to-do app. It triages text.

## Why open

Running the model locally is the whole point: the automation works with no
internet, private notes stay on your own machine, and it costs nothing to run
forever. A closed API could do the same triage — but it would meter every
brain-dump, keep your words on someone else's server, and stop working the
moment you stop paying.

## License

MIT — see [LICENSE](LICENSE).
