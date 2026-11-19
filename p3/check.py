"""`p3 check [--final]`: is everything in place and unchanged? CI runs it on every push.

It prints a checklist, one line per item:

    OK    the item holds
    TODO  hand-in work not done yet (only without --final; it never fails the check)
    WARN  worth a look, never a failure
    FAIL  something is broken, or, with --final, something the hand-in needs is missing
    PLUS  work in the repo beyond what the hand-in needs (the "Extra work" section, shown only
          when there is some; it earns bonus points as the Canvas discussion says)

Integrity (always; any FAIL exits non-zero):
- p3/bench.sha256 matches the fixed files, and tutor/FORMATS.md is identical to bench/FORMATS.md.
- Every configs/*/SNAPSHOT.json hash matches its files; every bench/runs/<config>/*/run.json names
  an existing config whose hash matches.
- Every JSON file under bench/ and configs/ parses (the files a tutor wrote into a run's outputs/
  are results, and the scorer judges those); every topic validates (TODO markers allowed without
  --final).
- Every compare record refers to existing configs and runs, and has its key file.
- c1-skills adds no subagent: configs/c1-skills/ holds none, and no quick round in
  reviews/c1-skills.md is of Kind new subagent (a FAIL even without --final).
- A warning when a config file holds a run of 40 or more characters copied from a shared topic, for
  each file of tutor/'s config that is not UTF-8 (p3 snapshot refuses it), and for each Markdown file
  under .claude/agents/ in tutor/ or a snapshot that is not a subagent, because its frontmatter is
  missing or has no name (Claude Code does not load it, and the minimums do not count it).

Completeness (the hand-in; TODO lines without --final, FAIL lines with it). These are the rules of
version 0.2, which asks for less than 0.1 did and accepts everything 0.1 called complete:
- DECISIONS.md has no TODO marker left, and PREREG.md neither for 598E or the length-study stretch;
  REPORT.md is there (p3 report --write writes it). EVAL.md is no longer needed and is not read
  (README.md is the brief, not the student's to write).
- The configs of the ladder, with the four skills from c1-skills on and a PreToolUse hook in final.
- The scored full runs at 30 minutes on agent-architecture (SHARED_RUNS: three of c0-baseline, two
  of final, one of each step between); one scored run of each final-minus-<x>, a full run or one
  made with --only; one own topic, valid, run by c0-baseline and final, with every run made from
  the committed items (a second such topic is a bonus, and an unfinished one only a warning once
  one is done); the complete blind comparison of c0-baseline and final on agent-architecture, one
  session per job (of full runs: a session made with p3 compare --quick or --teach-only does not
  count).
- The reviews (p3/reviews.py reads them): in reviews/c1-skills.md, c2-review.md and c3-split.md at
  least two complete quick rounds, and in each step file a complete major review of a scored full
  run of that step on the shared topic (a rating for every criterion and what the next step
  should fix), first committed complete after that run finished (a warning when git cannot tell);
  reviews/final.md also holds one complete learning session on a test topic in bench/own/, and a
  complete review of a test topic that has its runs. A warning, never a failure, for a complete
  round whose Run line is not written and for a round left untouched once the step has its rounds
  (an untouched optional round in final.md is ignored); a review file that is not UTF-8 is
  reported as that alone, since its headings cannot be read.
- reviews/components.md has a complete entry (Kind and Kept in final) for every skill and subagent
  in a snapshot other than c0-baseline, and those snapshots together hold the section's minimum of
  skills and subagents. An entry for a component no snapshot holds (one tried and taken out in a
  round) may stay, and a ### section with no field label that names no component is prose.
- For 598E or the length study: two scored teach-only runs of c1-skills and final at 10 and at 60
  minutes, a complete blind comparison of their teach-only runs at each of the two lengths (p3
  compare --teach-only), and PREREG.md committed with sections 1 to 4 filled in before the first
  run.

Extra work (PLUS lines; never a failure and never needed): what version 0.1 asked for and 0.2 does
not, when it is there: written feedback on every criterion of a major review, sections of EVAL.md,
Purpose and Review in the inventory, a third run of final, a full run of the ablation, each
additional complete test topic, more learning sessions than one, length-study runs beyond the eight, and for
598E the larger architecture of six skills and eight subagents.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import p3
from p3 import compare, config, reviews, runner, topic, util
from p3.util import P3Error

OK, TODO, WARN, FAIL = "OK", "TODO", "WARN", "FAIL"
PLUS = "PLUS"  # work beyond what the hand-in needs
SECTIONS = ("498E", "598E")
LENGTH_STUDY = "length-study"
LADDER = ("c0-baseline", "c1-skills", "c2-review", "c3-split", "final")
SKILLED = ("c1-skills", "c2-review", "c3-split", "final")
SKILLS = ("teach", "tutor", "quiz", "grade")
DOCS = ("DECISIONS.md",)
REPORT = "REPORT.md"  # written by p3 report --write
SHARED_RUNS = {"c0-baseline": 3, "c1-skills": 1, "c2-review": 1, "c3-split": 1, "final": 2}
ABLATION_PREFIX = "final-minus-"
ABLATION_RUNS = 1
BENCH_MINUTES = 30
BLIND_COMPARE = ("c0-baseline", "final")
BLIND_COMPARE_JOBS = ("teach", "quiz", "grade", "tutor")
# (skills, subagents) at least, over every snapshot other than c0-baseline; SKILLS among the skills
MINIMUMS = {"498E": (4, 5), "598E": (5, 6)}
EARLIER_MINIMUMS = {"598E": (6, 8)}  # what version 0.1 asked of 598E; building that much is extra work now
OWN_TOPICS = 1  # a second complete test topic is a bonus
STUDY_CONFIGS = ("c1-skills", "final")
STUDY_MINUTES = (10, 60)  # the 30-minute point is the ladder's full runs
STUDY_RUNS = 2
EARLIER_STUDY_MINUTES = (30,)  # a length version 0.1 also asked for; runs at it are extra work now
EVAL = "EVAL.md"  # the write-up of version 0.1; what is written in it is extra work now
COPY_RUN = 40
MAX_DETAILS = 12
TODO_MARK = "TODO"


@dataclass
class Item:
    status: str
    text: str
    details: list[str] = field(default_factory=list)


@dataclass
class Checklist:
    """The items of a check, by section, and what they add up to."""

    final: bool
    sections: list[tuple[str, list[Item]]] = field(default_factory=list)
    header: str = ""

    def section(self, title: str) -> list[Item]:
        items: list[Item] = []
        self.sections.append((title, items))
        return items

    def items(self, title: str | None = None) -> list[Item]:
        return [i for t, items in self.sections if title is None or t == title for i in items]

    def failures(self) -> list[Item]:
        return [i for i in self.items() if i.status == FAIL]

    def exit_code(self) -> int:
        return 1 if self.failures() else 0

    def text(self) -> str:
        width = max(len(s) for s in (OK, TODO, WARN, FAIL))
        out = [self.header, ""] if self.header else []
        for title, items in self.sections:
            if title == EXTRAS and not items:
                continue
            out.append(title)
            for item in items:
                out.append(f"  {item.status.ljust(width)}  {item.text}")
                shown = item.details[:MAX_DETAILS]
                out += [f"  {' ' * width}    {d}" for d in shown]
                if len(item.details) > MAX_DETAILS:
                    out.append(f"  {' ' * width}    ... and {len(item.details) - MAX_DETAILS} more")
            out.append("")
        integrity = [i for i in self.items(INTEGRITY) if i.status == FAIL]
        handin = [i for i in self.items(HANDIN) if i.status != WARN]  # a warning is never an item to do
        done = sum(1 for i in handin if i.status == OK)
        if integrity:
            out.append(f"Integrity: {len(integrity)} failure{'s' if len(integrity) != 1 else ''}; each FAIL line above says what is wrong.")
        else:
            out.append("Integrity: no failures.")
        if handin:
            if self.final:
                missing = sum(1 for i in handin if i.status == FAIL)
                out.append(f"Hand-in: {done} of {len(handin)} items done" + (f"; {missing} still missing." if missing else ", ready to hand in."))
            else:
                out.append(f"Hand-in: {done} of {len(handin)} items done (TODO lines are work still to do; p3 check --final fails on them).")
        extras = self.items(EXTRAS)
        if extras:
            out.append(f"Extra work: {_plural(len(extras), 'thing')} beyond what the hand-in needs (the PLUS lines; the Canvas discussion says what the bonus is).")
        return "\n".join(out) + "\n"


INTEGRITY = "Integrity"
HANDIN = "Hand-in"
EXTRAS = "Extra work"


def _plural(n: int, word: str, plural: str | None = None) -> str:
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def _todo_lines(text: str) -> list[int]:
    return [n for n, line in enumerate(text.splitlines(), 1) if TODO_MARK in line]


def _read_json(path: Path):
    try:
        return util.read_json(path), None
    except P3Error as exc:
        return None, str(exc).split(": ", 1)[-1]


# ---- integrity ----


def check_p3_json(root: Path, final: bool, items: list[Item]) -> dict:
    """p3.json: the section (498E or 598E) and the stretch; returns the parsed file ({} if broken)."""
    path = root / "p3.json"
    if not path.is_file():
        items.append(Item(FAIL, "p3.json is missing; it says your section and your stretch, as {\"section\": \"498E\", \"stretch\": null}"))
        return {}
    data, error = _read_json(path)
    if not isinstance(data, dict):
        items.append(Item(FAIL, f"p3.json does not parse: {error or 'it must hold a JSON object'}"))
        return {}
    section, stretch = data.get("section"), data.get("stretch")
    problems = []
    if section not in SECTIONS:
        problems.append(f"section is {section!r}; set it to \"498E\" or \"598E\"")
    if stretch is not None and not (isinstance(stretch, str) and stretch.strip()):
        problems.append(f"stretch is {stretch!r}; set it to the id of your stretch, or null")
    if problems:
        items.append(Item(FAIL if final else WARN, "p3.json: " + "; ".join(problems)))
    else:
        items.append(Item(OK, f"p3.json: section {section}, " + (f"stretch {stretch}" if stretch else "no stretch chosen yet")))
    return data


def check_fixed(root: Path, items: list[Item]) -> None:
    try:
        found = util.verify_fixed(root)
    except P3Error as exc:
        items.append(Item(FAIL, f"{exc}; restore it from git (git checkout -- {util.HASH_FILE})"))
        return
    details = [f"changed: {p}" for p in found["changed"]] + [f"missing: {p}" for p in found["missing"]] + [f"not listed: {p}" for p in found["extra"]]
    if details:
        items.append(Item(
            FAIL, f"{util.HASH_FILE}: {_plural(len(details), 'fixed file')} differ from the course's version; restore {'it' if len(details) == 1 else 'them'} with git (git checkout -- <path>, and delete a file that is not listed)", details,
        ))  # fmt: skip
    else:
        items.append(Item(OK, f"{util.HASH_FILE} matches the {len(util.fixed_files(root))} fixed files"))


def check_formats_copy(root: Path, items: list[Item]) -> None:
    bench, tutor = root / "bench" / "FORMATS.md", root / "tutor" / "FORMATS.md"
    if not bench.is_file():
        items.append(Item(FAIL, "bench/FORMATS.md is missing"))
    elif not tutor.is_file():
        items.append(Item(FAIL, "tutor/FORMATS.md is missing; copy bench/FORMATS.md there"))
    elif util.normalized_bytes(bench) != util.normalized_bytes(tutor):
        items.append(Item(FAIL, "tutor/FORMATS.md differs from bench/FORMATS.md; copy bench/FORMATS.md over it (the tutor must follow the bench's contract)"))
    else:
        items.append(Item(OK, "tutor/FORMATS.md is identical to bench/FORMATS.md"))


def check_encoding(root: Path, items: list[Item]) -> None:
    """A warning for each text file of the live config that is not UTF-8: p3 snapshot refuses it,
    because its hash would differ between a Windows checkout and the commit."""
    folder = root / "tutor"
    bad = util.non_utf8_files(folder, util.config_files(folder))
    if bad:
        items.append(Item(WARN, f"tutor/: {_plural(len(bad), 'config file')} not saved as UTF-8; p3 snapshot refuses them, so {util.NON_UTF8_HINT}", [f"tutor/{rel}" for rel in bad]))


def check_snapshots(root: Path, items: list[Item]) -> dict[str, str]:
    """One item per folder under configs/; returns {name: hash} of the snapshots that match."""
    good: dict[str, str] = {}
    base = root / "configs"
    folders = sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")) if base.is_dir() else []
    if not folders:
        items.append(Item(WARN, "configs/ holds no snapshot; c0-baseline ships with the template, so restore it from git"))
        return good
    for folder in folders:
        name = folder.name
        rel = f"configs/{name}/"
        if not (folder / "SNAPSHOT.json").is_file():
            items.append(Item(FAIL, f"{rel} has no SNAPSHOT.json; make snapshots only with p3 snapshot {name}"))
            continue
        data, error = _read_json(folder / "SNAPSHOT.json")
        if not isinstance(data, dict) or not isinstance(data.get("hash"), str):
            items.append(Item(FAIL, f"{rel}SNAPSHOT.json " + (f"does not parse: {error}" if error else "has no hash")))
            continue
        actual = util.config_hash(folder)
        if actual != data["hash"]:
            recorded = set(data.get("files") or [])
            now = set(util.config_files(folder))
            details = [f"added: {p}" for p in sorted(now - recorded)] + [f"removed: {p}" for p in sorted(recorded - now)]
            details += [f"not UTF-8, which git stores with other line endings than it was hashed with: {p} ({util.NON_UTF8_HINT})" for p in util.non_utf8_files(folder, sorted(now))]
            details = details or ["a file's content changed"]
            items.append(Item(FAIL, f"{rel} no longer matches its SNAPSHOT.json; a snapshot is a fixed record, so restore it from git, or snapshot the change under a new name", details))
            continue
        note = "" if data.get("name") in (None, name) else f" (its SNAPSHOT.json names {data.get('name')!r})"
        items.append(Item(WARN if note else OK, f"{rel} matches its SNAPSHOT.json ({_plural(len(util.config_files(folder)), 'file')}){note}"))
        good[name] = actual
    return good


def check_runs(root: Path, snapshots: dict[str, str], items: list[Item]) -> None:
    base = root / "bench" / "runs"
    folders = sorted(p for p in base.iterdir() if p.is_dir() and p.name != util.LIVE_RUNS_DIR and not p.name.startswith(".")) if base.is_dir() else []
    if not folders:
        items.append(Item(OK, "bench/runs/: no runs yet"))
        return
    for folder in folders:
        name = folder.name
        runs = sorted(p for p in folder.iterdir() if p.is_dir())
        exists = (root / "configs" / name / "SNAPSHOT.json").is_file()
        problems = []
        for run_dir in runs:
            rel = f"bench/runs/{name}/{run_dir.name}"
            if not (run_dir / "run.json").is_file():
                problems.append(f"{rel}/ has no run.json (a run that was stopped; delete it)")
                continue
            run, error = _read_json(run_dir / "run.json")
            if not isinstance(run, dict):
                problems.append(f"{rel}/run.json does not parse: {error or 'not a JSON object'}")
                continue
            if run.get("config") != name:
                problems.append(f"{rel}/run.json names config {run.get('config')!r}, not {name!r}")
            elif not exists:
                problems.append(f"{rel}/run.json names config {name}, which does not exist in configs/")
            elif name in snapshots and run.get("config_hash") != snapshots[name]:
                problems.append(f"{rel} was made with another version of {name} than configs/{name}/ holds; restore that snapshot from git, or delete this run")
        if problems:
            items.append(Item(FAIL, f"bench/runs/{name}/: {_plural(len(problems), 'run')} out of {len(runs)} do not match configs/{name}/", problems))
        elif not runs:
            items.append(Item(OK, f"bench/runs/{name}/: no runs yet"))
        elif name not in snapshots:
            items.append(Item(FAIL, f"bench/runs/{name}/: configs/{name}/ is broken (see above), so its {_plural(len(runs), 'run')} cannot be checked"))
        else:
            items.append(Item(OK, f"bench/runs/{name}/: {_plural(len(runs), 'run')}, each made with configs/{name}/ as it is"))


RUN_OUTPUTS_RE = re.compile(r"^bench/runs/[^/]+/[^/]+/[^/]+/outputs/")


def check_json(root: Path, items: list[Item]) -> None:
    bad, count = [], 0
    for folder in ("bench", "configs"):
        for rel in util.list_files(root / folder):
            path = f"{folder}/{rel}"
            if not rel.endswith(".json") or path.startswith(f"bench/runs/{util.LIVE_RUNS_DIR}/") or RUN_OUTPUTS_RE.match(path):
                continue
            count += 1
            _data, error = _read_json(root / path)
            if error:
                bad.append(f"{path}: {error}")
    if bad:
        items.append(Item(FAIL, f"{_plural(len(bad), 'JSON file')} under bench/ and configs/ do not parse", bad))
    else:
        items.append(Item(OK, f"all {_plural(count, 'JSON file')} under bench/ and configs/ parse (the tutors' own outputs in runs are left to the scorer)"))


def check_topics(root: Path, final: bool, items: list[Item]) -> dict[str, topic.Validation]:
    """One item per topic; returns {topic id: its validation}."""
    found: dict[str, topic.Validation] = {}
    listed = topic.list_topics(root)
    for tid, kind, folder in listed:
        found[tid] = topic.validate(folder, kind)
    finished_own = [tid for tid, kind, _ in listed if kind == topic.OWN and found[tid].ok(allow_todo=False)]
    for tid, kind, folder in listed:
        rel = util.posix(folder, root) + "/"
        v = found[tid]
        if v.errors:
            items.append(Item(FAIL, f"{rel} is not a valid topic ({_plural(len(v.errors), 'problem')})", v.errors + v.todos))
        elif v.todos:
            count = sum(int(m.group(1)) for t in v.todos if (m := re.search(r": (\d+) TODO", t)))
            text = f"{rel} is valid, with {_plural(count or len(v.todos), 'TODO marker')} still to fill in"
            if kind == topic.OWN and len(finished_own) >= OWN_TOPICS:  # an extra test topic, not finished
                items.append(Item(WARN, text + f"; a second test topic is optional, so finish it for the bonus or delete {rel}", v.todos))
            else:
                items.append(Item(FAIL if final else TODO, text, v.todos))
        else:
            items.append(Item(OK, f"{rel} is a valid {'test' if kind == topic.OWN else 'shared'} topic"))
    own = root / "bench" / "own"
    if own.is_dir():
        for folder in sorted(p for p in own.iterdir() if p.is_dir() and not p.name.startswith(".") and not (p / "topic.json").is_file()):
            items.append(Item(WARN, f"bench/own/{folder.name}/ has no topic.json, so it is not a topic; make one with p3 new-topic <id>"))
    return found


def check_compare_records(root: Path, items: list[Item]) -> None:
    files = compare.session_files(root)
    if not files:
        items.append(Item(OK, "bench/compare/: no comparison sessions yet"))
        return
    bad = []
    for path in files:
        rel = f"bench/compare/{path.name}"
        record, error = _read_json(path)
        if not isinstance(record, dict):
            bad.append(f"{rel}: {error or 'not a JSON object'}")
            continue
        sid = path.name[: -len(".json")]
        kpath = compare.key_path(sid, root)
        key = None
        if not kpath.is_file():
            bad.append(f"{rel}: its key file bench/compare/{kpath.name} is missing")
        else:
            key, error = _read_json(kpath)
            if key is None:
                bad.append(f"bench/compare/{kpath.name}: {error}")
        problems = compare.record_problems(record, key if isinstance(key, dict) else {"pairs": {}})
        if not isinstance(key, dict):  # reported above; the record itself can still be checked
            problems = [p for p in problems if not p.startswith("the key")]
        bad += [f"{rel}: {p}" for p in problems]
        configs = record.get("configs") if isinstance(record.get("configs"), list) else []
        for name in configs:
            if isinstance(name, str) and not (root / "configs" / name / "SNAPSHOT.json").is_file():
                bad.append(f"{rel}: config {name} does not exist in configs/")
        missing = set()
        for pair in record.get("pairs") or []:
            run_pair = pair.get("run_pair") if isinstance(pair, dict) else None
            if not (isinstance(run_pair, list) and len(run_pair) == len(configs) == 2):
                continue
            for name, run_id in zip(configs, run_pair):
                if not (util.runs_dir(str(name), root) / str(run_id) / "run.json").is_file():
                    missing.add(f"bench/runs/{name}/{run_id}")
        bad += [f"{rel}: run {m} does not exist" for m in sorted(missing)]
    names = {p.name[: -len(".json")] for p in files}
    base = compare.compare_dir(root)
    for kfile in sorted(base.glob("*.key.json")):
        if kfile.name[: -len(".key.json")] not in names:
            items.append(Item(WARN, f"bench/compare/{kfile.name} has no session file beside it"))
    if bad:
        items.append(Item(FAIL, f"comparison records that do not fit the configs and runs ({_plural(len(bad), 'problem')}); records are written by p3 compare, never by hand", bad))
    else:
        items.append(Item(OK, f"bench/compare/: {_plural(len(files), 'comparison session')}, each with its key, existing configs and runs"))


C1 = "c1-skills"


def check_c1_skills_only(root: Path, items: list[Item]) -> None:
    """c1-skills adds no subagent: subagents arrive in c2-review and c3-split. A rule, not unfinished
    work, so a break FAILs with or without --final."""
    folder = root / "configs" / C1
    snapshot = (folder / "SNAPSHOT.json").is_file()
    review = reviews.read_step(C1, root)
    if not snapshot and review is None:
        return
    problems = []
    if snapshot:
        for name, rel in sorted(reviews.subagents(folder).items()):
            problems.append(f"configs/{C1}/{rel}: the subagent {name}; take it out of tutor/, snapshot {C1} again (p3 snapshot {C1} --force) and make its runs again")
    for r in review.rounds if review else []:
        if r.kind_value == reviews.NEW_SUBAGENT:
            problems.append(f"{review.path}, {reviews.QUICK_ROUNDS} > {r.title}: Kind is new subagent; a quick round of {C1} changes or adds a skill, or makes another change (Kind other)")
    if problems:
        items.append(Item(FAIL, f"{C1} adds a subagent, but c1 is still one agent (subagents arrive in c2-review and c3-split)", problems))
    else:
        items.append(Item(OK, f"{C1}: skills only (no subagent in configs/{C1}/, and no quick round that adds one)"))


def check_agent_files(root: Path, items: list[Item]) -> None:
    """A warning for each Markdown file under .claude/agents/, in tutor/ or a snapshot, that is not a
    subagent because its frontmatter is missing or has no name: Claude Code does not load it, and the
    minimums do not count it. README.md is documentation by design and left out."""
    folders = [("tutor", root / "tutor")] + [(f"configs/{n}", root / "configs" / n) for n in util.list_configs(root)]
    found = [f"{label}/{rel}" for label, folder in folders for rel in reviews.agent_docs(folder)]
    if found:
        items.append(Item(
            WARN, f".claude/agents/: {_plural(len(found), 'Markdown file')} with no frontmatter or no name in it, which Claude Code does not load as a subagent and p3 check does not count; "
            "that is fine for a checklist a subagent reads, but a subagent needs frontmatter with its name and description, opening on the first line", found,
        ))  # fmt: skip


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)


def fixture_windows(root: Path) -> dict[str, str]:
    """{every 40-character run of a shared topic's text (whitespace collapsed, case folded): the
    file it comes from}. JSON files contribute their string values, other text files their text."""
    windows: dict[str, str] = {}
    base = root / "bench" / "topics"
    for rel in util.list_files(base):
        path = base / rel
        try:
            raw = path.read_bytes().decode("utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        texts = [raw]
        if rel.endswith(".json"):
            try:
                texts = list(_strings(json.loads(raw)))
            except json.JSONDecodeError:
                pass
        for text in texts:
            norm = _normalize(text)
            for i in range(len(norm) - COPY_RUN + 1):
                windows.setdefault(norm[i : i + COPY_RUN], f"bench/topics/{rel}")
    return windows


def copied_runs(text: str, windows: dict[str, str]) -> list[tuple[str, str]]:
    """(copied text, source file) for each maximal run of 40 or more characters of `text` found in
    the windows."""
    norm = _normalize(text)
    found, i = [], 0
    while i <= len(norm) - COPY_RUN:
        source = windows.get(norm[i : i + COPY_RUN])
        if source is None:
            i += 1
            continue
        j = i + 1
        while j <= len(norm) - COPY_RUN and norm[j : j + COPY_RUN] in windows:
            j += 1
        found.append((norm[i : j - 1 + COPY_RUN], source))
        i = j - 1 + COPY_RUN
    return found


def check_copies(root: Path, items: list[Item]) -> None:
    windows = fixture_windows(root)
    sources = [("tutor", root / "tutor")] + [(f"configs/{n}", config.config_dir(n, root)) for n in util.list_configs(root)]
    hits: dict[tuple[str, str, str], list[str]] = {}
    for label, folder in sources:
        for rel in util.config_files(folder):
            try:
                text = (folder / rel).read_bytes().decode("utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for copied, source in copied_runs(text, windows):
                hits.setdefault((rel, copied, source), []).append(label)
    if not hits:
        items.append(Item(OK, f"no config file copies {COPY_RUN} or more characters from a shared topic"))
        return
    for (rel, copied, source), labels in sorted(hits.items()):
        where = ", ".join(f"{label}/{rel}" for label in labels)
        snippet = copied if len(copied) <= 90 else copied[:87] + "..."
        items.append(Item(WARN, f"{where} copies {len(copied)} characters from {source}: \"{snippet}\"", ["a config must not special-case bench items; write it in your own words, or leave it out"]))


# ---- completeness ----


def _need(items: list[Item], final: bool, done: bool, text: str, details: list[str] | None = None) -> None:
    items.append(Item(OK if done else (FAIL if final else TODO), text, details or []))


def check_docs(root: Path, final: bool, prereg: bool, items: list[Item]) -> None:
    for name in DOCS + (("PREREG.md",) if prereg else ()):
        path = root / name
        if not path.is_file():
            hint = " (it is new in version 0.2; copy it from the template)" if name in DOCS else ""
            _need(items, final, False, f"{name} is missing{hint}")
            continue
        lines = _todo_lines(util.read_text(path))
        if lines:
            shown = ", ".join(map(str, lines[:10])) + (", ..." if len(lines) > 10 else "")
            _need(items, final, False, f"{name}: {_plural(len(lines), 'TODO marker')} left (line{'s' if len(lines) != 1 else ''} {shown})")
        else:
            _need(items, final, True, f"{name} is written")
    there = (root / REPORT).is_file()
    _need(items, final, there, f"{REPORT}: " + ("there (p3 report --write writes it again after new runs)" if there else "not written yet (p3 report --write, once your runs are scored)"))


def _skills(folder: Path) -> list[str]:
    return [s for s in SKILLS if (folder / ".claude" / "skills" / s / "SKILL.md").is_file()]


def _has_pretooluse_hook(folder: Path) -> bool:
    try:
        hooks = config.settings(folder).get("hooks")
    except P3Error:
        return False
    entries = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    return isinstance(entries, list) and any(isinstance(e, dict) and e.get("hooks") for e in entries)


def check_configs(root: Path, final: bool, items: list[Item]) -> list[str]:
    """The ladder's configs; returns the final-minus-* names."""
    names = util.list_configs(root)
    for name in LADDER:
        folder = root / "configs" / name
        if name not in names:
            _need(items, final, False, f"config {name}: not snapshotted yet (p3 snapshot {name})")
            continue
        problems = []
        if name in SKILLED:
            lacking = [s for s in SKILLS if s not in _skills(folder)]
            if lacking:
                problems.append(f"no {', '.join(lacking)} skill (.claude/skills/<name>/SKILL.md)")
        if name == "final" and not _has_pretooluse_hook(folder):
            problems.append("no PreToolUse hook in .claude/settings.json (the guard)")
        what = {"c0-baseline": "the baseline", "final": "the four skills and a PreToolUse hook"}.get(name, "the four skills")
        _need(items, final, not problems, f"config {name}: " + ("; ".join(problems) if problems else what))
    ablations = [n for n in names if n.startswith(ABLATION_PREFIX)]
    _need(items, final, bool(ablations), "ablation: " + (", ".join(ablations) if ablations else f"no {ABLATION_PREFIX}<x> config yet (final with one component removed)"))
    return ablations


def _full_runs(root: Path, name: str, topic_id: str, minutes: int | None = None) -> list[util.RunRecord]:
    """Scored runs of every scenario (not quick, not --only), at `minutes` when given."""
    return util.list_runs(name, topic_id, scored=True, quick=False, minutes=minutes, kind=util.FULL, root=root)


def _ablation_runs(root: Path, name: str) -> list[util.RunRecord]:
    """Scored runs of an ablation on the shared topic at the bench's length that are not quick: a
    full run, or one made with --only for the scenarios the removed component touches."""
    return util.list_runs(name, util.SHARED_TOPIC, scored=True, quick=False, minutes=BENCH_MINUTES, root=root)


def check_shared_runs(root: Path, final: bool, ablations: list[str], items: list[Item]) -> None:
    where = f"on {util.SHARED_TOPIC} at {BENCH_MINUTES} minutes"
    for name, n in SHARED_RUNS.items():
        have = len(_full_runs(root, name, util.SHARED_TOPIC, BENCH_MINUTES))
        if have >= n:
            text = f"runs of {name}: {_plural(have, 'scored full run')} {where} ({n} needed)"
        else:
            hint = f"p3 bench --config {name}" + (f" --repeats {n - have}" if n - have > 1 else "")
            text = f"runs of {name}: {have} of the {_plural(n, 'scored full run')} needed {where} ({hint})"
        _need(items, final, have >= n, text)
    for waiting in runner.pending_resumes(root):
        if waiting["config"] != util.LIVE_RUNS_DIR and waiting["config"] != "live":
            done, total = waiting["done"], waiting["done"] + waiting["missing"]
            items.append(Item(WARN, f"a repeat of {waiting['config']} that a limit stopped is waiting, with {done} of its {_plural(total, 'scenario')} done; finish it with: uv run p3 bench --resume"))
    for name in ablations:
        have = len(_ablation_runs(root, name))
        if have >= ABLATION_RUNS:
            text = f"runs of {name}: {_plural(have, 'scored run')} {where} ({ABLATION_RUNS} needed, a full run or one made with --only)"
        else:
            text = f"runs of {name}: no scored run {where} yet (p3 bench --config {name}, with --only and the scenarios the removed component touches, or without it for a full run)"
        _need(items, final, have >= ABLATION_RUNS, text)


def check_own_topics(root: Path, final: bool, validations: dict[str, topic.Validation], items: list[Item]) -> tuple[list[str], list[str], list[str]]:
    """The test topics: one is needed, valid with no TODO, run by c0-baseline and final from
    committed items. Returns (the ids of every own topic; the ids of those that are ready: valid,
    with both runs, every run from the committed items; the ids of the OWN_TOPICS that count for
    the hand-in: the ready ones first, then the ones nearest to it). What is missing in a topic
    that does not count is a warning, because a second test topic is a bonus."""
    own = [tid for tid, kind, _ in topic.list_topics(root) if kind == topic.OWN]
    git_ok = util.git_available(root)
    committed: dict[tuple[str, str], str | None] = {}  # (commit, folder): its hash then; a topic's runs often share a commit
    found: dict[str, list[tuple[bool, str, list[str]]]] = {}  # topic id: (done, text, details) of each thing it needs
    notes: list[Item] = []
    for tid in own:
        rel = f"bench/own/{tid}"
        needs = found.setdefault(tid, [])
        v = validations.get(tid)
        valid = bool(v and v.ok(allow_todo=False))
        needs.append((valid, f"{rel}/: " + ("valid, no TODO left" if valid else "not finished (see its line above)"), []))
        missing = [name for name in ("c0-baseline", "final") if not _full_runs(root, name, tid)]
        needs.append((not missing, f"{rel}/: " + (f"no scored full run of {' or '.join(missing)} yet" if missing else "scored runs of c0-baseline and final"), []))
        runs = util.list_runs(None, tid, root=root)
        if not runs:
            continue
        if not git_ok:
            notes.append(Item(WARN, f"{rel}/: not a git repository here, so whether each run used the committed items is not checked"))
            continue
        current = util.hash_tree(root / "bench" / "own" / tid)
        problems = []
        for rec in runs:
            run_rel = util.posix(rec.dir, root)
            commit, recorded = rec.run.get("topic_commit"), rec.run.get("topic_hash")
            if not commit:
                problems.append(f"{run_rel}: no topic_commit (was it run outside git?)")
                continue
            if (commit, rel) not in committed:
                committed[(commit, rel)] = util.hash_tree_at_commit(commit, rel, root)
            then = committed[(commit, rel)]
            if then is None:
                problems.append(f"{run_rel}: commit {commit[:12]} does not hold {rel}/ (commit and push the topic before running it)")
            elif then != recorded:
                problems.append(f"{run_rel}: the items it ran differ from {rel}/ as committed in {commit[:12]}")
            elif recorded != current:
                problems.append(
                    f"{run_rel}: {rel}/ has changed since this run; a test topic is frozen once it has runs, so restore it from git "
                    "(to fix a real mistake in it, follow \"Commit before the first run\" in bench/own/README.md)"
                )
        needs.append((not problems, f"{rel}/: " + ("every run used the committed items" if not problems else f"{_plural(len(problems), 'run')} not made from the committed items as they are now"), problems))
    ready = [tid for tid in own if all(done for done, _, _ in found[tid])]
    nearest = sorted((tid for tid in own if tid not in ready), key=lambda tid: -sum(done for done, _, _ in found[tid]))
    counted = (ready + nearest)[:OWN_TOPICS]
    if len(own) >= OWN_TOPICS:
        extra = "" if len(own) == OWN_TOPICS else "; a second one is a bonus once it is complete"
        count = f"test topics in bench/own/: {len(own)} ({', '.join(own)}; {OWN_TOPICS} needed{extra})"
    else:
        count = f"test topics in bench/own/: {len(own)} of the {OWN_TOPICS} needed (p3 new-topic <id>)"
    _need(items, final, len(own) >= OWN_TOPICS, count)
    for tid in own:
        for done, text, details in found[tid]:
            if tid not in counted and not done:  # another topic covers the hand-in
                items.append(Item(WARN, text + "; a second test topic is optional, so this is only needed for the bonus", details))
            else:
                _need(items, final, done, text, details)
    items += notes
    return own, ready, counted


def complete_sessions(root: Path, teach_only: bool = False) -> dict[tuple[frozenset, str, str, int | None], str]:
    """{(configs, job, topic, minutes): session id} of the complete comparison sessions of one kind:
    of full runs, or with `teach_only` of the length study's teach-only runs. A session made with
    p3 compare --quick pairs quick runs, which leave out most scenarios, so it is never one."""
    complete: dict[tuple[frozenset, str, str, int | None], str] = {}
    for path in compare.session_files(root):
        record, _ = _read_json(path)
        if not (isinstance(record, dict) and record.get("complete") is True and isinstance(record.get("configs"), list)):
            continue
        if record.get("quick") or bool(record.get("teach_only")) != teach_only:
            continue
        minutes = record.get("minutes")
        key = (frozenset(map(str, record["configs"])), str(record.get("job")), str(record.get("topic")), minutes if isinstance(minutes, int) else None)
        complete.setdefault(key, str(record.get("session") or path.stem))
    return complete


def check_compares(root: Path, final: bool, items: list[Item]) -> None:
    """The required blind comparison: c0-baseline against final on the shared topic, every job, of
    full runs. The length study's comparisons are checked with its runs; an optional second one of
    the student's choice is not checked."""
    complete: dict[tuple[frozenset, str, str], str] = {}
    for (configs, job, tid, _minutes), sid in complete_sessions(root).items():
        complete.setdefault((configs, job, tid), sid)
    a, b = BLIND_COMPARE
    for job in BLIND_COMPARE_JOBS:
        sid = complete.get((frozenset((a, b)), job, util.SHARED_TOPIC))
        hint = f"p3 compare {a} {b} --job {job}"
        _need(items, final, sid is not None, f"compare {a} / {b}, {job} on {util.SHARED_TOPIC}: " + (f"complete ({sid})" if sid else f"no complete session yet ({hint})"))


# ---- the reviews ----


def _review_run(root: Path, step: str, run_id: str) -> tuple[util.RunRecord | None, str | None]:
    """(the scored full run of `step` a major review names, None) or (None, what is wrong with it)."""
    rel = f"bench/runs/{step}/{run_id}"
    where = f"{reviews.MAJOR_REVIEW} > Run"
    if not (util.runs_dir(step, root) / run_id / "run.json").is_file():
        return None, f"{where}: {rel} is not a run (no {rel}/run.json); name a run folder under bench/runs/{step}/"
    rec = next((r for r in util.list_runs(step, root=root) if r.dir.name == run_id), None)
    if rec is None:
        return None, f"{where}: {rel}/run.json does not parse"
    full = f"the major review reviews a full run (p3 bench --config {step})"
    if rec.run.get("quick"):
        return None, f"{where}: {rel} is a quick run; {full}"
    if util.run_kind(rec.run) != util.FULL:
        return None, f"{where}: {rel} ran only some scenarios (--only); {full}"
    if rec.run.get("topic") != util.SHARED_TOPIC:
        return None, f"{where}: {rel} is a run on {rec.run.get('topic')}; the major review reviews a full run on {util.SHARED_TOPIC} (p3 bench --config {step})"
    if not rec.scored:
        return None, f"{where}: {rel} is not scored yet (p3 score {rel})"
    return rec, None


def first_complete_commit(root: Path, step: str, run_id: str) -> tuple[str, datetime] | None:
    """(commit, time) of the first commit in which reviews/<step>.md holds a complete major review
    of that run, or None."""
    rel = reviews.step_file(step)
    for commit, when, data in util.git_file_versions(rel, root):
        if data is None:
            continue
        major = reviews.parse_step(data.decode("utf-8", errors="replace"), step).major
        if major.complete and major.run_id == run_id:
            return commit, when
    return None


def _check_rounds(final: bool, review: reviews.StepReview, items: list[Item]) -> None:
    rel, need = review.path, reviews.MIN_ROUNDS[review.step]
    complete = [r for r in review.rounds if r.complete]
    started = [r for r in review.rounds if r.touched and not r.complete]
    details = [review.rounds_problem] if review.rounds_problem else []
    details += [p for r in started for p in r.problems]
    if need and len(complete) < need:
        details += [f"{reviews.QUICK_ROUNDS} > {r.title}: not written yet" for r in review.rounds if not r.touched]
        if len(review.rounds) < need and not review.rounds_problem:
            details.append(f"{reviews.QUICK_ROUNDS}: {_plural(len(review.rounds), 'round')}; add a ### Round section for each round, {need} at least")
        _need(items, final, False, f"{rel}, quick rounds: {len(complete)} of the {need} complete rounds needed", details)
        return
    them = "it" if len(started) == 1 else "them"
    if not need:
        text = f"{rel}, quick rounds (optional): " + (f"{len(complete)} complete" if complete else "none written")
    else:
        text = f"{rel}, quick rounds: {len(complete)} complete ({need} needed)"
    if started:
        text += f", and {_plural(len(started), 'round')} started but not complete (finish {them}, or delete {them})"
    _need(items, final, not started, text, details)
    # what the trail needs and the count does not: the run each round rests on, and no leftover skeleton
    tidy = [f"{reviews.QUICK_ROUNDS} > {r.title}: the Run line is not written; name the run your thoughts rest on" for r in complete if not r.run_written]
    tidy += [f"{reviews.QUICK_ROUNDS} > {r.title}: not written; fill it in or delete it" for r in review.rounds if not r.touched and not r.optional]
    if tidy:
        items.append(Item(WARN, f"{rel}, quick rounds: {_plural(len(tidy), 'thing')} to tidy before you hand in", tidy))


def _check_major(root: Path, final: bool, review: reviews.StepReview, items: list[Item]) -> util.RunRecord | None:
    """The major review's item; returns its run when the review is complete."""
    rel, step, major = review.path, review.step, review.major
    problems = list(major.problems)
    rec = None
    if major.run_id:
        rec, problem = _review_run(root, step, major.run_id)
        if problem:
            problems.append(problem)
    if not problems:
        _need(items, final, True, f"{rel}, major review: complete, of bench/runs/{step}/{major.run_id}")
        return rec
    if major.present and not major.touched:
        shown = [p for p in problems if p.startswith(f"{reviews.MAJOR_REVIEW} > Run: ")]
        _need(items, final, False, f"{rel}, major review: not written yet (after a scored full run of {step}, rate every criterion and say what the next step should fix)", shown)
    else:
        _need(items, final, False, f"{rel}, major review: not complete yet ({_plural(len(problems), 'problem')})", problems)
    return None


def _check_review_order(root: Path, final: bool, review: reviews.StepReview, rec: util.RunRecord, items: list[Item]) -> None:
    """The major review must be written after the run it reviews: the first commit that holds it
    complete comes after the run finished."""
    rel, run_rel = review.path, util.posix(rec.dir, root)
    if not util.git_available(root):
        items.append(Item(WARN, f"{rel}: not a git repository here, so whether the major review was committed after {run_rel} finished is not checked"))
        return
    finished = util.parse_iso(rec.run.get("finished_at")) or util.parse_iso(rec.run.get("started_at"))
    found = first_complete_commit(root, review.step, rec.dir.name)
    if found is None:
        _need(items, final, False, f"{rel}, major review: complete here but in no commit yet; commit it (p3 check compares that commit's time with when {run_rel} finished)")
        return
    commit, when = found
    first = f"{rel}, major review: first committed complete at {util.iso_utc(when)} ({commit[:12]})"
    if finished is not None and when < finished:
        _need(items, final, False, f"{first}, before {run_rel} finished ({util.iso_utc(finished)}); a major review is written after the run it reviews")
        return
    _need(items, final, True, f"{first}, after {run_rel} finished" + (f" ({util.iso_utc(finished)})" if finished else ""))


def _session_problems(session: reviews.Session, own: list[str]) -> list[str]:
    """A session's problems, and, once its Topic is written and there are test topics, whether
    Topic starts with one of their ids."""
    problems = list(session.problems)
    if own and reviews.written(session.topic) and session.topic_id not in own:
        shown = session.topic if len(session.topic or "") <= 40 else (session.topic or "")[:37] + "..."
        problems.append(f"{reviews.LEARNING_SESSIONS} > {session.title}: Topic is {shown!r}; start it with the id of the test topic the session was on ({', '.join(own)})")
    return problems


def _check_sessions(final: bool, review: reviews.StepReview, own: list[str], items: list[Item]) -> None:
    """One complete learning session, on one of the test topics (the file has room for three)."""
    rel, need = review.path, reviews.SESSIONS
    problems = {id(s): _session_problems(s, own) for s in review.sessions}
    complete = [s for s in review.sessions if not problems[id(s)]]
    started = [s for s in review.sessions if s.touched and problems[id(s)]]
    on = sorted({s.topic_id for s in complete}) if own else []  # the test topics the complete sessions name
    details = [review.sessions_problem] if review.sessions_problem else []
    details += [p for s in started for p in problems[id(s)]]
    if len(complete) < need:
        if not started:
            details += [f"{reviews.LEARNING_SESSIONS} > {s.title}: not written yet" for s in review.sessions[:need] if not s.touched]
        if len(review.sessions) < need and not review.sessions_problem:
            details.append(f"{reviews.LEARNING_SESSIONS}: {_plural(len(review.sessions), 'session')}; add a ### Session section, {need} at least")
        _need(items, final, False, f"{rel}, learning sessions: {len(complete)} of the {_plural(need, 'complete session')} needed", details)
        return
    them = "it" if len(started) == 1 else "them"
    text = f"{rel}, learning sessions: {len(complete)} complete ({need} needed)" + (f", on {' and '.join(on)}" if on else "")
    if started:
        text += f", and {_plural(len(started), 'session')} started but not complete (finish {them}, or delete {them})"
    _need(items, final, not started, text, details)


def _check_topic_reviews(final: bool, review: reviews.StepReview, own: list[str], ready: list[str], counted: list[str], items: list[Item]) -> None:
    """A complete review of one test topic: of one that is ready (valid, with its runs) when one
    is. A review still missing for an extra topic, or a placeholder heading left from the template,
    is no problem once one review is done (a second topic, ready and reviewed, is extra work)."""
    rel = review.path
    if not own:
        _need(items, final, False, f"{rel}, test topics: no test topic in bench/own/ yet to review", [review.topics_problem] if review.topics_problem else [])
        return
    sections: dict[str, reviews.TopicReview] = {}
    for t in review.topics:
        sections.setdefault(t.topic, t)
    reviewed = [tid for tid in own if tid in sections and not sections[tid].problems]
    targets = ready or own  # the topics a review can cover
    done = [tid for tid in targets if tid in reviewed]
    placeholders = [t for t in review.topics if t.topic not in own and reviews.has_todo(t.title)]  # the template's headings, not renamed yet
    stray = [
        f"{reviews.TEST_TOPICS} > {t.title}: names no test topic in bench/own/ ({', '.join(own)}); rename it to a topic's id, or delete it"
        for t in review.topics if t.topic not in own and not reviews.has_todo(t.title)
    ]  # fmt: skip
    if not done:
        details = [review.topics_problem] if review.topics_problem else []
        for tid in [t for t in counted if t in targets] or targets[:OWN_TOPICS]:
            t = sections.get(tid)
            if t is not None:
                details += t.problems
            elif placeholders and not review.topics_problem:
                details.append(f"{reviews.TEST_TOPICS} > {placeholders[0].title}: make this heading the topic's id, ### {tid}, and compare c0-baseline and final on it there")
            elif not review.topics_problem:
                details.append(f"{reviews.TEST_TOPICS} > {tid}: missing; add ### {tid}, comparing c0-baseline and final on it")
        _need(items, final, False, f"{rel}, test topics: no complete review of a test topic yet ({OWN_TOPICS} needed)", details + stray)
        return
    _need(items, final, True, f"{rel}, test topics: a complete review of {' and '.join(done)} ({OWN_TOPICS} needed)")
    tidy = stray + [f"{reviews.TEST_TOPICS} > {tid}: no complete review; a second test topic is optional, so review it for the bonus or leave it" for tid in own if tid not in reviewed]
    if tidy:
        items.append(Item(WARN, f"{rel}, test topics: {_plural(len(tidy), 'thing')} you may tidy", tidy))


def check_reviews(root: Path, final: bool, own: list[str], ready: list[str], counted: list[str], items: list[Item]) -> None:
    """Each step's review file: its quick rounds, its major review and when that was committed, and
    in final the learning session and the test-topic review."""
    for step in reviews.STEPS:
        review = reviews.read_step(step, root)
        if review is None:
            _need(items, final, False, f"{reviews.step_file(step)} is missing; it holds your quick rounds and your major review of {step} (copy it back from the template)")
            continue
        problem = util.utf8_problem(root / review.path)
        if problem:
            _need(items, final, False, f"{review.path}: {problem}, so p3 check cannot read its headings; {util.NON_UTF8_HINT}")
            continue
        _check_rounds(final, review, items)
        rec = _check_major(root, final, review, items)
        if rec is not None:
            _check_review_order(root, final, review, rec, items)
        if step == "final":
            _check_sessions(final, review, own, items)
            _check_topic_reviews(final, review, own, ready, counted, items)


def _config_order(name: str) -> tuple:
    return (LADDER.index(name), name) if name in LADDER else (len(LADDER), name)


def built_components(root: Path) -> dict[tuple[str, str], list[str]]:
    """{(kind, name): the snapshots that hold it, in ladder order} over every snapshot other than
    c0-baseline; kind is skill or subagent."""
    found: dict[tuple[str, str], list[str]] = {}
    for name in sorted((n for n in util.list_configs(root) if n != "c0-baseline"), key=_config_order):
        folder = root / "configs" / name
        for skill in reviews.skill_names(folder):
            found.setdefault((reviews.SKILL, skill), []).append(name)
        for agent in reviews.subagents(folder):
            found.setdefault((reviews.SUBAGENT, agent), []).append(name)
    return found


def _entry_problems(entry: reviews.Entry, built: bool = False) -> list[str]:
    """An entry's problems, or one line for an entry with no field written yet; `built` when it is
    the entry of a component a snapshot holds, which must stay."""
    if entry.problems and not entry.touched:
        todo = "write its Kind and its Kept in final" if built else "fill it in for one component, or delete it"
        return [f"{entry.title or '(a ### heading with no name)'}: not written yet; {todo}"]
    return entry.problems


def inventory_problems(root: Path, built: dict[tuple[str, str], list[str]], entries: list[reviews.Entry]) -> list[str]:
    """What keeps reviews/components.md from listing every component built: a missing or incomplete
    entry, a Kind, Step added or Kept in final that the snapshots contradict, a duplicate."""
    problems: list[str] = []
    by_key: dict[str, list[reviews.Entry]] = {}
    for e in entries:
        by_key.setdefault(e.key, []).append(e)
    in_final = None
    if (root / "configs" / "final" / "SNAPSHOT.json").is_file():
        in_final = {k for k, configs in built.items() if "final" in configs}
    steps = set(SKILLED) | {n for n in util.list_configs(root) if n != "c0-baseline"}
    seen: set[int] = set()
    for (kind, name), configs in sorted(built.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        candidates = by_key.get(reviews.name_key(name), [])
        entry = next((e for e in candidates if e.kind == kind), None)
        if entry is None and len(candidates) == 1 and candidates[0].kind is None:
            entry = candidates[0]  # its Kind is TODO or unreadable, which its own problems say
        if entry is None:
            other = reviews.SUBAGENT if kind == reviews.SKILL else reviews.SKILL
            if candidates and (other, name) not in built:
                entry = candidates[0]
                problems.append(f"{name}: its entry says Kind {entry.values.get('Kind')}, but configs/{configs[0]}/ holds it as a {kind}")
            elif candidates:  # only the entry of the skill or subagent of the same name
                problems.append(f"{name} ({kind}, in configs/{configs[0]}/): no entry for the {kind}; the ### {name} there is the {other}'s, so add another ### {name}, with Kind {kind}")
                continue
            else:
                problems.append(f"{name} ({kind}, in configs/{configs[0]}/): no entry; add ### {name} with its Kind and its Kept in final")
                continue
        seen.add(id(entry))
        problems += _entry_problems(entry, built=True)
        ladder = [c for c in configs if c in SKILLED]
        if entry.step and ladder and entry.step != ladder[0]:
            problems.append(f"{name}: Step added is {entry.step}, but it first appears in configs/{ladder[0]}/")
        elif entry.step and not ladder and entry.step not in configs:
            problems.append(f"{name}: Step added is {entry.step}, but only {', '.join(f'configs/{c}/' for c in configs)} hold it")
        if entry.kept is not None and in_final is not None:
            held = (kind, name) in in_final
            if entry.kept and not held:
                problems.append(f"{name}: Kept in final says yes, but configs/final/ does not hold it")
            elif not entry.kept and held:
                problems.append(f"{name}: Kept in final says no, but configs/final/ holds it")
    for e in entries:
        if id(e) in seen or not e.labeled:  # matched above, or a ### section of prose
            continue
        problems += _entry_problems(e)
        if e.step and e.step not in steps:
            problems.append(f"{e.title}: Step added is {e.step}; name the step it was built in ({', '.join(SKILLED)})")
    for group in by_key.values():
        group = [e for e in group if e.labeled or id(e) in seen]
        kinds = [e.kind for e in group]
        for kind in sorted({k for k in kinds if kinds.count(k) > 1}, key=str):
            lines = ", ".join(str(e.line) for e in group if e.kind == kind)
            problems.append(f"{group[0].title}: {kinds.count(kind)} entries (lines {lines}); keep one")
    return problems


def check_inventory(root: Path, final: bool, section: str | None, items: list[Item]) -> None:
    """reviews/components.md lists every skill and subagent built, and the snapshots hold the
    section's minimum of them."""
    rel = reviews.COMPONENTS_PATH
    built = built_components(root)
    skills = sorted(n for k, n in built if k == reviews.SKILL)
    agents = sorted(n for k, n in built if k == reviews.SUBAGENT)
    counts = f"{_plural(len(skills), 'skill')} and {_plural(len(agents), 'subagent')}"
    entries = reviews.read_components(root)
    problem = util.utf8_problem(root / rel) if entries is not None else None
    if entries is None:
        _need(items, final, False, f"{rel} is missing; it lists every skill and subagent you build, each with its kind and whether final kept it (copy it back from the template)")
    elif problem:
        _need(items, final, False, f"{rel}: {problem}, so p3 check cannot read its entries; {util.NON_UTF8_HINT}")
    else:
        problems = inventory_problems(root, built, entries)
        if not built:
            _need(items, final, False, f"{rel}: no skill or subagent in a snapshot other than c0-baseline yet", problems)
        elif problems:
            _need(items, final, False, f"{rel}: not complete ({_plural(len(problems), 'problem')}); every skill and subagent in a snapshot other than c0-baseline needs a complete entry", problems)
        else:
            _need(items, final, True, f"{rel}: a complete entry for every skill and subagent in your snapshots ({counts})")
    known = section in MINIMUMS
    sec = section if known else "498E"
    need_skills, need_agents = MINIMUMS[sec]
    lacking = [s for s in SKILLS if s not in skills]
    done = len(skills) >= need_skills and not lacking and len(agents) >= need_agents
    text = (
        f"components built: {counts} across your snapshots other than c0-baseline "
        f"({sec}{'' if known else ', the default while no section is set,'} needs at least {need_skills} skills, {', '.join(SKILLS[:-1])} and {SKILLS[-1]} among them, and {need_agents} subagents)"
    )
    details = []
    if not done:
        details += [f"skills: {', '.join(skills)}"] if skills else []
        details += [f"required skills not in a snapshot yet: {', '.join(lacking)}"] if lacking else []
        details += [f"subagents: {', '.join(agents)}"] if agents else []
    _need(items, final, done, text, details)


def _teach_only(rec: util.RunRecord) -> bool:
    return util.run_kind(rec.run) == util.TEACH_ONLY


def prereg_commit(root: Path) -> tuple[str, datetime, str] | None:
    """(commit, time, sections 1 to 4) of the first commit of PREREG.md with no TODO marker before
    its section 5, or None."""
    for commit, when, data in util.git_file_versions("PREREG.md", root):
        if data is None:
            continue
        head = _prereg_head(data.decode("utf-8", errors="replace"))
        if TODO_MARK not in head:
            return commit, when, head
    return None


def _prereg_head(text: str) -> str:
    """PREREG.md up to its section 5 (the part fixed before the runs)."""
    text = text.replace("\r\n", "\n")
    match = re.search(r"^#{1,6}\s*5\b", text, re.MULTILINE)
    return text[: match.start()] if match else text


def check_length_study(root: Path, final: bool, items: list[Item]) -> None:
    study = []
    for name in STUDY_CONFIGS:
        counts = []
        for minutes in STUDY_MINUTES:
            recs = [r for r in util.list_runs(name, util.SHARED_TOPIC, scored=True, quick=False, minutes=minutes, root=root) if _teach_only(r)]
            study += recs
            counts.append(len(recs))
        done = all(c >= STUDY_RUNS for c in counts)
        cells = ", ".join(f"{c} at {m}" for c, m in zip(counts, STUDY_MINUTES))
        _need(items, final, done, f"length study, {name}: scored teach-only runs {cells} minutes, {STUDY_RUNS} needed at each" + ("" if done else f" (p3 bench --config {name} --only teach --minutes M --repeats {STUDY_RUNS})"))
    # the study's blind comparisons, one per length: the student's second blind comparison
    sessions = complete_sessions(root, teach_only=True)
    a, b = STUDY_CONFIGS
    for minutes in STUDY_MINUTES:
        sid = sessions.get((frozenset((a, b)), "teach", util.SHARED_TOPIC, minutes))
        hint = f"p3 compare {a} {b} --job teach --teach-only --minutes {minutes}"
        _need(items, final, sid is not None, f"length study, compare {a} / {b} at {minutes} minutes: " + (f"complete ({sid})" if sid else f"no complete teach-only session yet ({hint})"))
    if not (root / "PREREG.md").is_file():
        _need(items, final, False, "PREREG.md is missing")
        return
    if not util.git_available(root):
        items.append(Item(WARN, "PREREG.md: not a git repository here, so when it was committed is not checked"))
        return
    found = prereg_commit(root)
    starts = [t for t in (util.parse_iso(r.run.get("started_at")) for r in study) if t]
    first = min(starts) if starts else None
    if found is None:
        _need(items, final, False, "PREREG.md: no commit has sections 1 to 4 filled in yet; commit them before the first length-study run")
        return
    commit, when, head = found
    if first is not None and when > first:
        _need(items, final, False, f"PREREG.md: sections 1 to 4 were first committed at {util.iso_utc(when)} ({commit[:12]}), after the first length-study run started ({util.iso_utc(first)})")
        return
    when_text = f"committed at {util.iso_utc(when)} ({commit[:12]})"
    _need(items, final, True, f"PREREG.md: sections 1 to 4 {when_text}" + (f", before the first length-study run ({util.iso_utc(first)})" if first else ", before any length-study run"))
    now = _prereg_head(util.read_text(root / "PREREG.md"))
    if " ".join(now.split()) != " ".join(head.split()):
        items.append(Item(WARN, "PREREG.md: sections 1 to 4 have changed since that commit; leave them as they were and add a dated entry in section 6 instead"))


# ---- extra work ----


def eval_sections_written(text: str) -> list[int]:
    """The numbers of the sections of EVAL.md (## 1. to ## 13.) that hold text and no TODO marker."""
    lines = text.replace("\r\n", "\n").split("\n")
    heads = [(n, int(m.group(1))) for n, line in enumerate(lines) if (m := re.match(r"^##\s+(\d+)\.", line))]
    written = []
    for k, (start, number) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        body = "\n".join(lines[start + 1:end])
        if body.strip() and TODO_MARK not in body:
            written.append(number)
    return written


def _numbers(found: list[int]) -> str:
    """"1", "1 and 2", "1, 2 and 3"."""
    words = [str(n) for n in found]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + f" and {words[-1]}"


def check_extras(root: Path, settings: dict, ablations: list[str], own: list[str], ready: list[str], study: bool, items: list[Item]) -> None:
    """What the repo holds beyond what version 0.2 needs: one PLUS line for each. Version 0.1 asked
    for all of it, so a student who had done it by then is ahead, not behind."""
    final_review = None
    for step in reviews.STEPS:
        review = reviews.read_step(step, root)
        if review is None or util.utf8_problem(root / review.path):
            continue
        if step == "final":
            final_review = review
        wanted = [(job, name) for job in reviews.STEP_JOBS[step] for name in reviews.CRITERIA[job]]
        found = [review.major.criteria.get(key) for key in wanted]
        if all(c is not None and c.rating is not None and reviews.written(c.feedback) for c in found):
            items.append(Item(PLUS, f"{review.path}: written feedback on every criterion of the major review ({len(wanted)} of {len(wanted)})"))
    path = root / EVAL
    if path.is_file() and not util.utf8_problem(path):
        written = eval_sections_written(util.read_text(path))
        if written:
            items.append(Item(PLUS, f"{EVAL}: section{'s' if len(written) != 1 else ''} {_numbers(written)} written ({len(written)} of 13)"))
    entries = reviews.read_components(root) if not util.utf8_problem(root / reviews.COMPONENTS_PATH) else None
    built = built_components(root)
    if entries:
        keys = {reviews.name_key(name) for _kind, name in built}
        full = [e for e in entries if e.key in keys and reviews.written(e.values.get("Purpose")) and reviews.written(e.values.get("Review"))]
        if full:
            items.append(Item(PLUS, f"{reviews.COMPONENTS_PATH}: Purpose and Review written for {len(full)} of {_plural(len(built), 'component')}"))
    have, need = len(_full_runs(root, "final", util.SHARED_TOPIC, BENCH_MINUTES)), SHARED_RUNS["final"]
    if have > need:
        items.append(Item(PLUS, f"runs of final: {_plural(have, 'scored full run')} on {util.SHARED_TOPIC}, {have - need} more than needed"))
    for name in ablations:
        if any(util.run_kind(r.run) == util.FULL for r in _ablation_runs(root, name)):
            items.append(Item(PLUS, f"runs of {name}: a full run, where a run made with --only would do"))
    if final_review is not None:
        reviewed = {t.topic for t in final_review.topics if not t.problems}
        more = [tid for tid in ready if tid in reviewed][OWN_TOPICS:]
        for tid in more:
            items.append(Item(PLUS, f"an additional test topic, complete with its runs and its review ({tid})"))
        sessions = [s for s in final_review.sessions if not _session_problems(s, own)]
        if len(sessions) > reviews.SESSIONS:
            items.append(Item(PLUS, f"{final_review.path}, learning sessions: {len(sessions)} complete, {len(sessions) - reviews.SESSIONS} more than needed"))
    if study:
        for name in STUDY_CONFIGS:
            counts = {m: len([r for r in util.list_runs(name, util.SHARED_TOPIC, scored=True, quick=False, minutes=m, root=root) if _teach_only(r)]) for m in sorted(STUDY_MINUTES + EARLIER_STUDY_MINUTES)}
            more = sum(max(0, c - STUDY_RUNS) if m in STUDY_MINUTES else c for m, c in counts.items())
            if more:
                cells = ", ".join(f"{c} at {m}" for m, c in counts.items())
                items.append(Item(PLUS, f"length study, {name}: {_plural(more, 'teach-only run')} beyond the {STUDY_RUNS * len(STUDY_MINUTES)} needed ({cells} minutes)"))
    earlier = EARLIER_MINIMUMS.get(settings.get("section") or "")
    if earlier:
        skills = [n for k, n in built if k == reviews.SKILL]
        agents = [n for k, n in built if k == reviews.SUBAGENT]
        if len(skills) >= earlier[0] and len(agents) >= earlier[1]:
            items.append(Item(PLUS, f"components built: {_plural(len(skills), 'skill')} and {_plural(len(agents), 'subagent')}, the larger architecture of at least {earlier[0]} and {earlier[1]}"))


# ---- the command ----


def run_checks(root: Path | None = None, final: bool = False) -> Checklist:
    """Every check, as a Checklist (nothing is printed)."""
    root = Path(root) if root else util.repo_root()
    report = Checklist(final)
    integrity = report.section(INTEGRITY)
    settings = check_p3_json(root, final, integrity)
    check_fixed(root, integrity)
    check_formats_copy(root, integrity)
    check_encoding(root, integrity)
    snapshots = check_snapshots(root, integrity)
    check_runs(root, snapshots, integrity)
    check_json(root, integrity)
    validations = check_topics(root, final, integrity)
    check_compare_records(root, integrity)
    check_c1_skills_only(root, integrity)
    check_agent_files(root, integrity)
    check_copies(root, integrity)

    handin = report.section(HANDIN)
    study = settings.get("section") == "598E" or settings.get("stretch") == LENGTH_STUDY
    check_docs(root, final, study, handin)
    ablations = check_configs(root, final, handin)
    check_shared_runs(root, final, ablations, handin)
    own, ready, counted = check_own_topics(root, final, validations, handin)
    check_compares(root, final, handin)
    check_reviews(root, final, own, ready, counted, handin)
    check_inventory(root, final, settings.get("section"), handin)
    if study:
        check_length_study(root, final, handin)
    check_extras(root, settings, ablations, own, ready, study, report.section(EXTRAS))
    section = settings.get("section") or "no section"
    stretch = settings.get("stretch")
    report.header = f"p3 {p3.__version__} check{' --final' if final else ''}: {section}" + (f", stretch {stretch}" if stretch else "") + f" ({root})"
    return report


def main(args) -> int:
    """The p3 check command."""
    report = run_checks(final=bool(getattr(args, "final", False)))
    print(report.text(), end="")
    return report.exit_code()
