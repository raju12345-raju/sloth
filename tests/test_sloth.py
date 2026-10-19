"""Tests for sloth.py. The heuristic fallback and output parsing are tested
without a model; model-dependent paths are tested with a stubbed Ollama."""
import io
import json
import sys
import unittest
from unittest import mock

sys.path.insert(0, "..")
import sloth


class TestHeuristic(unittest.TestCase):
    def test_urgent_ranked_first(self):
        r = sloth.heuristic_triage("buy milk\nURGENT: fix production bug\nmaybe learn spanish")
        self.assertEqual(r["plan"][0]["priority"], 1)
        self.assertIn("production", r["plan"][0]["task"].lower())

    def test_noise_ignored(self):
        r = sloth.heuristic_triage("hi\nlol\nfix the sink")
        self.assertTrue(any("hi" in x for x in r["ignored"]))
        self.assertEqual(len(r["plan"]), 1)

    def test_empty(self):
        r = sloth.heuristic_triage("")
        self.assertEqual(r["plan"], [])

    def test_flagged_as_fallback(self):
        r = sloth.heuristic_triage("do thing")
        self.assertTrue(r["_fallback"])


class TestExtractJson(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(sloth.extract_json('{"a": 1}'), {"a": 1})

    def test_fenced(self):
        self.assertEqual(sloth.extract_json('```json\n{"a": 2}\n```'), {"a": 2})

    def test_chatter(self):
        self.assertEqual(
            sloth.extract_json('Sure! Here it is:\n{"a": 3}\nHope that helps!'),
            {"a": 3})

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            sloth.extract_json("no json here at all")


class TestTriageCommand(unittest.TestCase):
    def _run(self, argv, stdin_text):
        with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
            with mock.patch.object(sys, "stdout", new=io.StringIO()) as out:
                with mock.patch.object(sys, "stderr", new=io.StringIO()):
                    code = sloth.main(argv)
        return code, out.getvalue()

    def test_fallback_on_model_failure(self):
        with mock.patch.object(sloth, "call_ollama",
                               side_effect=ConnectionError("nope")):
            code, out = self._run(["triage"], "URGENT: water the plants")
        self.assertEqual(code, 0)
        self.assertIn("water the plants", out)

    def test_model_path_json(self):
        fake = (json.dumps({"sloth_pick": "nap",
                            "plan": [{"task": "nap", "priority": 1,
                                      "effort": "30m", "why": "rest matters"}],
                            "ignored": []}),
                {"model": "gemma3:1b", "latency_ms": 5,
                 "prompt_tokens": 10, "completion_tokens": 20,
                 "cost_usd": 0.0})
        with mock.patch.object(sloth, "call_ollama", return_value=fake):
            with mock.patch.object(sloth, "record_trace"):
                code, out = self._run(["triage", "--json"], "take a nap")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["sloth_pick"], "nap")

    def test_empty_input_rejected(self):
        code, _ = self._run(["triage"], "   \n")
        self.assertEqual(code, 2)


class TestNormalize(unittest.TestCase):
    def test_greeting_moved_to_ignored(self):
        r = sloth.normalize({"sloth_pick": "x",
                             "plan": [{"task": "hi", "priority": 5,
                                       "effort": "1m", "why": "greeting"},
                                      {"task": "fix sink", "priority": 1,
                                       "effort": "30m", "why": "leak"}],
                             "ignored": []})
        self.assertEqual(len(r["plan"]), 1)
        self.assertIn("hi", r["ignored"])

    def test_placeholder_ignored_dropped(self):
        r = sloth.normalize({"sloth_pick": "x",
                             "plan": [{"task": "fix sink", "priority": 1,
                                       "effort": "30m", "why": "leak"}],
                             "ignored": ["<non-task, max 3>", "lol"]})
        self.assertEqual(r["ignored"], ["lol"])


if __name__ == "__main__":
    unittest.main()
