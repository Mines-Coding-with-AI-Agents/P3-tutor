# CLAUDE.md - P3, a tutoring agent and its measurement

This file is for development sessions started at the repo root.
If this session started inside `tutor/`, you are the tutor, not a developer: ignore this file and follow `tutor/CLAUDE.md`.

This repo is a student's Project 3 for CSCI 498E/598E: a tutor that runs entirely inside Claude Code and does four jobs (teach, tutor, quiz, grade), and the bench that measures it.
`README.md` is the brief; read the part for the step the student is on before you build anything.
The student directs; you build one step at a time and say what each change does, and the student's own words stay theirs: `DECISIONS.md`, `EVAL.md`, `LEARNING-LOG.md`, `PREREG.md` and `tutor/PREFERENCES.md` are theirs to write.

## The tutor is what the student builds

- The tutor lives in `tutor/`; its config is `tutor/CLAUDE.md`, `tutor/PREFERENCES.md` and everything under `tutor/.claude/`.
  The learner files in `tutor/` (`MISSION.md`, `NOTES.md`, `lessons/`, `quizzes/`, `keys/` and so on) are never part of a config, and neither is `tutor/.claude/settings.local.json`, the personal file Claude Code writes when the student approves a tool.
- Skills go in `tutor/.claude/skills/<name>/SKILL.md`.
  The bench starts each job with `/teach`, `/tutor`, `/quiz` or `/grade` when that skill exists and with `/teach` otherwise, so those four names are fixed.
- Subagents go in `tutor/.claude/agents/<name>.md`; `tutor/.claude/agents/README.md` explains the fields and what the bench showed about them.
- Hooks go in `tutor/.claude/settings.json`, because hooks in subagent frontmatter do not run in the bench's `claude -p` sessions; put any script a hook runs under `tutor/.claude/` so it is part of the config.
- `permissions.allow` in `tutor/.claude/settings.json` becomes the bench's `--allowedTools`, together with `Glob` and `Grep`, which the bench always adds; any other tool that would need a prompt is denied in a bench run; the key `model` sets the model (default `sonnet`).
- `tutor/FORMATS.md` is a copy of `bench/FORMATS.md`, the output contract the bench reads; never change either, and `p3 check` fails if they differ.
- This file, and any skills or subagents under a root `.claude/`, also load when the student runs `claude` inside `tutor/`, but never in a bench run, so tutor behavior belongs in `tutor/`.

## Leave as is

- Course-owned: `bench/` except `bench/own/` (the student's two test topics), `p3/`, the test files already in `tests/`, and `.github/workflows/`.
  The student adds test files of their own to `tests/`, such as `tests/test_guard.py` for the guard hook.
  `p3/bench.sha256` pins `bench/FORMATS.md`, `bench/scenarios.json`, `bench/judge/`, `bench/topics/` and every `.py` file in `p3/`.
  If one looks buggy, show the student the evidence and have them report it to the instructor.
- Written by commands, never by hand: `configs/` (`p3 snapshot`), `bench/runs/` (`p3 bench`, `p3 score`) and `bench/compare/` (`p3 compare`).
- In a blind comparison the student's picks are the measurement: never say or guess which config made an output, never open `bench/compare/*.key.json`, and never suggest a pick or a reason.
- A config must not special-case bench items: `p3 check` warns when a config file copies 40 or more characters from a shared topic.

## Commands

From the repo root, `uv run p3 <command>` or, without uv, `python -m p3 <command>`; both work.

- `p3 snapshot <name> [--force]` copies the tutor's config into `configs/<name>/`.
- `p3 bench --config <name>|live [--topic <id>] [--repeats N] [--quick] [--minutes M] [--only <ids>] [--no-score]` runs the scenarios on a config and scores them.
- `p3 score <run-dir> [--offline] [--no-model]`, `p3 report`, `p3 new-topic <id>`, and `p3 check [--final]` before every push.
- `p3 compare <config-a> <config-b> --job teach|quiz|grade|tutor [--topic <id>] [--minutes M]`, then `p3 compare --reveal <session-id>`; `--list` and `--resume <session-id>` too.
- Unit tests: `python -m unittest discover -s tests -t .`; they run against `tests/fake_claude.py` and never call Claude.

## Cost

- Every `p3 bench` scenario is a real Claude Code session on the student's own subscription, and it counts against their usage limits.
  A full run on `agent-architecture` is ten sessions (teach, quiz, a grade per submission, a tutor per probe) plus the scoring calls; `--quick` is five; `--repeats` multiplies either.
- Before any `p3 bench`, say how many sessions it will start, suggest `--quick` or `--only` while iterating, and ask before starting.
- A full `p3 bench` run takes far longer than a foreground command may run: start it in the background, or ask the student to run it in their own terminal.
  A run that stops midway has no `run.json`; delete its folder rather than commit it.
- `p3 bench` stops by itself at a usage limit or a sign-in problem and sets that repeat aside under `bench/runs/_live/_aborted/`; report what it printed, and do not retry until the student says the limit has reset.
- `p3 score` makes judge and solver calls too (`--no-model` skips them); `p3 compare`, `p3 report` and `p3 check` make none.
- `cost_usd_list` is the list-price equivalent Claude Code reports, not what the student pays on a subscription.
- The repo is public, history included: keep keys, tokens and private information out of it.

## Instructor only

`python -m p3 rehash` rewrites `p3/bench.sha256` after the instructor changes a fixed file.
Never run it in a student's repo: when `p3 check` reports a hash mismatch, restore the fixed file from git instead (`git checkout -- <path>`).
In the template, `configs/c0-baseline/` must equal the shipped `tutor/`, so a change to `tutor/` there is followed by `python -m p3 snapshot c0-baseline --force`; `template-ci` checks it.
