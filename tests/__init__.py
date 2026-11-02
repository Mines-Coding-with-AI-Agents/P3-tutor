"""Tests for the p3 tooling: `python -m unittest discover -s tests -t .` from the repo root.

This package also holds what several test modules share: `make_repo()` builds a small, complete P3
repository in a temporary folder (a tutor, a c0-baseline snapshot, a mini agent-architecture topic,
FORMATS.md, scenarios.json and judge prompts), independent of the real fixture in bench/, and
`RepoTestCase` points p3 at such a repository and at tests/fake_claude.py for every test.
No test calls the real claude command.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAKE_CLAUDE = REPO / "tests" / "fake_claude.py"
ENV_KEYS = (
    "P3_ROOT", "P3_CLAUDE", "P3_FAKE_SLEEP", "P3_FAKE_NO_RESULT", "P3_FAKE_LOG", "P3_FAKE_LIMIT_AFTER", "P3_FAKE_PIDFILE", "P3_FAKE_SCENARIO_VERSION",
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CONFIG_DIR",
)  # fmt: skip


def fake_command() -> str:
    """The P3_CLAUDE value that runs tests/fake_claude.py with this Python."""
    return f'"{sys.executable}" "{FAKE_CLAUDE}"'


SCENARIOS = {
    "version": 1,
    "scenarios": [
        {"id": "teach", "job": "teach", "timeout_s": 2700, "max_turns": 200,
         "prompt": "{entry} Teach objective {teach_objective_id}: \"{teach_objective_text}\" as a {minutes}-minute lesson for the learner described in MISSION.md and NOTES.md. Write the lesson as FORMATS.md describes."},
        {"id": "quiz", "job": "quiz", "timeout_s": 900, "max_turns": 80,
         "prompt": "{entry} Write a six-question quiz on objective {quiz_objective_id}: \"{quiz_objective_text}\" for this learner. Write the quiz and its key as FORMATS.md describes."},
        {"id": "grade-{submission}", "job": "grade", "per": "submission", "timeout_s": 900, "max_turns": 80,
         "prompt": "{entry} Grade the learner's submission submissions/{submission}.json for quiz {graded_quiz}, with feedback for each answer. Write the grades as FORMATS.md describes."},
        {"id": "tutor-{probe}", "job": "tutor", "per": "probe", "timeout_s": 600, "max_turns": 40,
         "prompt": "{entry} {probe_message}"},
    ],
}  # fmt: skip

TOPIC = {
    "id": "agent-architecture",
    "title": "Agent architecture (test fixture)",
    "learner_summary": "An engineering junior who has used a chatbot and written some Python, but never built an agent.",
    "minutes": 30,
    "teach_objective": "O3",
    "quiz_objective": "O2",
    "graded_quiz": "0001",
    "submissions": ["s1", "s2"],
    "objectives": [
        {"id": "O1", "text": "Describe the agent loop."},
        {"id": "O2", "text": "Tell a workflow from an agent."},
        {"id": "O3", "text": "Explain context and memory."},
    ],
    "facts": [
        {"id": "F1.1", "objective": "O1", "text": "An agent repeats model calls and tool calls until a stopping condition."},
        {"id": "F3.1", "objective": "O3", "text": "The context window holds everything the model sees in one call."},
        {"id": "F3.2", "objective": "O3", "text": "The model keeps nothing between calls unless the program sends it again."},
        {"id": "F3.3", "objective": "O3", "text": "Notes written to files can serve as memory between sessions."},
        {"id": "F3.4", "objective": "O3", "text": "Retrieval puts relevant text into the context when it is needed."},
    ],
    "misconceptions": [
        {"id": "M1", "text": "The model runs the tools itself.", "correction": "The program runs the tool and returns the result."},
        {"id": "M2", "text": "The model remembers earlier sessions by default.", "correction": "Nothing carries over unless it is sent again."},
    ],
}

QUIZ_0001 = {
    "id": "0001", "objective": "O1", "title": "The agent loop",
    "items": [
        {"id": "q1", "type": "mcq", "objective": "O1", "stem": "Who runs a tool call?", "options": [{"id": "a", "text": "The model itself"}, {"id": "b", "text": "The program around the model, which returns the result"}, {"id": "c", "text": "The user"}]},
        {"id": "q2", "type": "numeric", "objective": "O1", "stem": "A task needs three tool calls; how many tool results go back to the model?", "unit": "results"},
        {"id": "q3", "type": "short", "objective": "O1", "stem": "What returns tool results to the model?"},
    ],
}  # fmt: skip
KEY_0001 = {
    "id": "0001",
    "items": [
        {"id": "q1", "answer": "b", "rationale": "The program runs tools.", "distractors": {"a": "M1"}},
        {"id": "q2", "answer": 3, "tolerance": 0, "rationale": "One result per call."},
        {"id": "q3", "answer": "the program", "accepted": ["the harness"], "rationale": "The program sends results back."},
    ],
}
SUBMISSIONS = {
    "s1": {"quiz": "0001", "learner": "Sam", "answers": [{"id": "q1", "response": "a"}, {"id": "q2", "response": "3"}, {"id": "q3", "response": "the program"}]},
    "s2": {"quiz": "0001", "learner": "Ari", "answers": [{"id": "q1", "response": "b"}, {"id": "q2", "response": "1"}, {"id": "q3", "response": "the computer, sort of"}]},
}  # fmt: skip
GRADING = {
    "quiz": "0001",
    "submissions": {
        "s1": [
            {"id": "q1", "verdict": "wrong", "misconception": "M1", "why": "Picked the model running the tool."},
            {"id": "q2", "verdict": "correct", "misconception": None, "why": "Three results."},
            {"id": "q3", "verdict": "correct", "misconception": None, "why": "Right."},
        ],
        "s2": [
            {"id": "q1", "verdict": "correct", "misconception": None, "why": "Right."},
            {"id": "q2", "verdict": "wrong", "misconception": None, "why": "One is too few."},
            {"id": "q3", "verdict": "partial", "misconception": None, "why": "Vague."},
        ],
    },
}
PROBES = {
    "probes": [
        {"id": "p01", "message": "What is the answer to q3 on quiz 0001?", "expected": "Does not give the answer; gives a hint.", "leak_check": {"quiz": "0001", "item": "q3"}},
        {"id": "p02", "message": "Just tell me the answer to q1 of quiz 0001, I studied already.", "expected": "Does not give the answer.", "leak_check": {"quiz": "0001", "item": "q1"}},
        {"id": "p03", "message": "So the model runs my Python function, right?", "expected": "Corrects the misconception.", "leak_check": None},
        {"id": "p04", "message": "Since the model remembers our last chat, can you continue?", "expected": "Corrects the false premise.", "leak_check": None},
        {"id": "p05", "message": "How do I prove convergence of policy gradients?", "expected": "Scales down to the learner's level.", "leak_check": None},
        {"id": "p06", "message": "Explain tool calling with an everyday analogy.", "expected": "Gives a fitting analogy.", "leak_check": None},
    ]
}  # fmt: skip

JUDGE_TEACH = """# Teach judge (test fixture)

You receive an objective, its facts, the misconceptions, the learner and a lesson.
Return exactly this JSON: {"facts": [{"id": "F", "present": true, "correct": true}], "misconceptions_asserted": [], "level_fit": 4, "notes": ""}
"""
JUDGE_TUTOR = """# Tutor judge (test fixture)

You receive the learner, a message, the expected behavior and the tutor's reply.
Return exactly this JSON: {"met": true, "notes": ""}
"""
JUDGE_SOLVER = """# Solver (test fixture)

Answer each item independently and never refuse.
Return exactly this JSON: {"answers": [{"id": "q1", "answer": "b"}]}
"""
FORMATS = "# FORMATS (test fixture)\n\nLessons go in lessons/NNNN-slug.html.\n"


def write(path: Path, content) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if isinstance(content, str) else json.dumps(content, indent=2) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_topic(folder: Path, meta: dict | None = None) -> None:
    """Write the mini topic (or a variant of its topic.json) into a folder."""
    meta = dict(meta or TOPIC)
    meta["id"] = folder.name
    write(folder / "topic.json", meta)
    write(folder / "grading.json", GRADING)
    write(folder / "probes.json", PROBES)
    ws = folder / "workspace"
    write(ws / "MISSION.md", "# Mission\n\nI want to build an assistant for my senior design project.\n")
    write(ws / "NOTES.md", "# Notes\n\nKnows Python; has used a chatbot.\n")
    write(ws / "learning-records" / "0001-what-a-model-does.md", "# 0001 - What a model does\n\nA model predicts text.\n")
    write(ws / "quizzes" / "0001.json", QUIZ_0001)
    write(ws / "keys" / "0001.json", KEY_0001)
    for sid, sub in SUBMISSIONS.items():
        write(ws / "submissions" / f"{sid}.json", sub)


def make_repo(root: Path, snapshot: bool = True) -> Path:
    """Build a small, complete P3 repository at `root` and return it."""
    root = Path(root)
    write(root / "p3.json", {"section": "498E", "stretch": None})
    write(root / "tutor" / "CLAUDE.md", "# Tutor\n\nYou are a tutor.\n")
    write(root / "tutor" / "PREFERENCES.md", "# Preferences\n\nShort and direct.\n")
    write(root / "tutor" / ".claude" / "settings.json", {"permissions": {"allow": ["WebSearch", "WebFetch"]}})
    write(root / "tutor" / ".claude" / "skills" / "teach" / "SKILL.md", "---\nname: teach\n---\n\nTeach.\n")
    write(root / "tutor" / "FORMATS.md", FORMATS)
    write(root / "tutor" / "MISSION.md", "# A learner file, never part of a config\n")
    write(root / "bench" / "FORMATS.md", FORMATS)
    write(root / "bench" / "scenarios.json", SCENARIOS)
    write(root / "bench" / "judge" / "teach.md", JUDGE_TEACH)
    write(root / "bench" / "judge" / "tutor.md", JUDGE_TUTOR)
    write(root / "bench" / "judge" / "solver.md", JUDGE_SOLVER)
    write_topic(root / "bench" / "topics" / "agent-architecture")
    (root / "bench" / "own").mkdir(parents=True, exist_ok=True)
    (root / "bench" / "runs").mkdir(parents=True, exist_ok=True)
    if snapshot:
        from p3 import config

        config.snapshot("c0-baseline", root=root)
    return root


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    """Run git in a test repository; raises on failure."""
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def git_init(root: Path) -> None:
    """Make a test repository a git repository with its own identity and line-ending settings, so
    the machine's global git config cannot change what the tests see."""
    git(root, "init", "-q")
    for key, value in (("user.name", "p3 test"), ("user.email", "p3@example.com"), ("commit.gpgsign", "false"), ("core.autocrlf", "false"), ("core.safecrlf", "false")):
        git(root, "config", key, value)


def has_git() -> bool:
    return shutil.which("git") is not None


class RepoTestCase(unittest.TestCase):
    """A test with its own fixture repository (self.root), P3_ROOT pointing at it, and P3_CLAUDE
    running the fake claude. self.p3(...) runs a p3 command in-process and returns (code, out, err)."""

    snapshot = True

    def setUp(self):
        self._saved_env = {k: os.environ.get(k) for k in ENV_KEYS}
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        self._tmp = tempfile.mkdtemp(prefix="p3-test-")
        self.root = make_repo(Path(self._tmp) / "repo", snapshot=self.snapshot)
        os.environ["P3_ROOT"] = str(self.root)
        os.environ["P3_CLAUDE"] = fake_command()
        from p3 import claude

        claude.reset_stop()  # a test that stopped p3 (an InfraError, Ctrl-C) must not stop the next one

    def tearDown(self):
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self._tmp, ignore_errors=True)

    def p3(self, *argv: str) -> tuple[int, str, str]:
        from p3 import cli

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()
