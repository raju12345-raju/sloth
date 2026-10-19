---
title: Sloth — the lazy task triager (local Gemma does your organizing)
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

## What I Built

**Sloth** is a tiny CLI that takes your messy brain-dump — half-formed tasks,
notes, random thoughts, copy-pasted reminders — and hands back a short,
prioritized action plan with time estimates and one "do this first" pick.

The pitch is one line: **dump your brain, Sloth sorts it.** You never organize;
the sloth does. It was built for Week 3's theme, *Slow and Steady*: software
that rewards laziness. Tomorrow is International Sloth Day, and honestly, the
sloths have it figured out — conserve energy, move at your own pace, let
something else do the work.

Who would pay for this? Freelancers and students drowning in scattered
to-dos — the same people who buy $10/month AI organizers. Sloth does the core
job (turn chaos into a plan) for $0, forever, with their words never leaving
their laptop.

## Demo

[DEMO VIDEO — 90 seconds: paste a real brain-dump, watch Gemma triage it live]

The video shows a real run, end to end: a messy `brain-dump.txt` goes in,
Gemma (running locally, no internet needed) deduplicates it, drops the noise,
ranks every task by impact-per-effort, estimates effort, and picks the single
task to do first. The trace line at the end shows the receipt: model,
latency, tokens in/out, cost $0.00.

Try it yourself — no install beyond Python:

```bash
git clone https://github.com/raju12345-raju/sloth
cd sloth
curl -fsSL https://ollama.com/install.sh | sh && ollama pull gemma3:1b
python sloth.py triage examples/brain-dump.txt
```

## Code

https://github.com/raju12345-raju/sloth

Public repo, MIT license, built entirely inside the Oct 19–25 window. Python
3.10+, stdlib only — no `pip install`, no API keys, no accounts.

## How I Built It

The open-source AI is the core, not decoration. Remove it and the project
collapses to a keyword guesser — which is exactly what the fallback mode is,
and it's labeled as such.

**The pipeline:** your text goes to **Gemma 3 (1B)** running locally via
**Ollama**. A strict system prompt asks for JSON only: deduplicated tasks,
priorities 1–5 by impact-per-effort, effort estimates, one `sloth_pick`, and
up to 3 ignored non-tasks. Sloth parses the JSON defensively (tolerates
markdown fences and chatter), validates the shape, and renders a terminal plan.
Every run appends a trace — model, latency, prompt/completion tokens, cost —
viewable with `sloth trace`.

**Why local:** the whole point is that a brain-dump is *private*. Notes about
money, health, clients — that text should never travel to someone else's
server. Running Gemma on-device means the automation works offline, costs
nothing per run, and can never be taken away by a pricing change.

**Honest engineering notes:** a 1B model occasionally misreads a task, so the
README says plainly to verify before acting on anything important. If Ollama
isn't reachable, Sloth says so out loud and drops to a transparent heuristic
fallback — keyword scoring, clearly labeled, never pretending to be the model.
AI is a layer here, not a lifeline: the tool is never useless, but it's only
*smart* when the model is present.

## Why Does Open Innovation Matter?

Three concrete reasons, not slogans:

1. **Privacy by architecture.** A closed API could do this triage — but every
   brain-dump would travel to a data center. With an open-weight model on my
   own machine, the embarrassing, financial, and half-baked thoughts in my
   notes stay mine. Open made that a default instead of a premium tier.
2. **Zero marginal cost.** Each triage costs $0.00 in tokens, electricity
   aside. A metered API turns "dump your brain daily" from a habit into a
   budget decision. Open weights make the lazy workflow — the entire point of
   the theme — economically sane.
3. **Swappability.** Don't like Gemma 3 1B? Set `SLOTH_MODEL` to any Ollama
   model. The provider is a 30-line abstraction; fine-tuning, quantization,
   or a bigger model are all one env var away. Try negotiating that with a
   closed endpoint.

## My Agent Session

*Optional — including a brief honest note instead of a DevRelay embed: this
build was pair-driven with an AI coding assistant (Muse Spark). The session
itself isn't published as a replay; the repo's commit history and this
write-up are the record.*

## Prize Categories

- **Best Use of Gemma** — Gemma 3 (open-weight) does the actual reasoning,
  run locally via Ollama. It is the product, not a garnish.
- **Best Use of Sentry Agent Tracing** — every run emits a trace (latency,
  tokens in/out, cost), inspectable via `sloth trace`; traces are shown in the
  demo.

## What I didn't do (honest limits)

- No fake benchmarks, no invented user counts. The trace numbers in the demo
  are from a real run on real hardware.
- The 1B model is the floor, not the ceiling — bigger local models give
  better triage, and the README says so.
- No "AI will change your life" claims. It sorts a to-do list. That's enough.
