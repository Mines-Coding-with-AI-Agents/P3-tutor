"""`p3 check [--final]`: is everything in place and unchanged? CI runs it on every push.

It prints a checklist, one line per item:

    OK    the item holds
    TODO  hand-in work not done yet (only without --final; it never fails the check)
    WARN  worth a look, never a failure
    FAIL  something is broken, or, with --final, something the hand-in needs is missing

Integrity (always; any FAIL exits non-zero):
- p3/bench.sha256 matches the fixed files, and tutor/FORMATS.md is identical to bench/FORMATS.md.
- Every configs/*/SNAPSHOT.json hash matches its files; every bench/runs/<config>/*/run.json names
  an existing config whose hash matches.
- Every JSON file under bench/ and configs/ parses (the files a tutor wrote into a run's outputs/
  are results, and the scorer judges those); every topic validates (TODO markers allowed without
  --final).
- Every compare record refers to existing configs and runs, and has its key file.
- A warning when a config file holds a run of 40 or more characters copied from a shared topic, and
  for each file of tutor/'s config that is not UTF-8 (p3 snapshot refuses it).

Completeness (the hand-in; TODO lines without --final, FAIL lines with it):
- README.md, DECISIONS.md, EVAL.md and LEARNING-LOG.md have no TODO marker left, and PREREG.md too
  for 598E or the length-study stretch.
- The configs of the ladder, with the four skills from c1-skills on and a PreToolUse hook in final.
- The scored full runs at 30 minutes on agent-architecture; two own topics, each valid, run by
  c0-baseline and final, with every run made from the committed items; the complete compare sessions
  (of full runs: a session made with p3 compare --quick or --teach-only does not count).
- For 598E or the length study: three scored teach-only runs of c1-skills and final at 10, 30 and
  60 minutes, and PREREG.md committed with sections 1 to 4 filled in before the first of them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from p3 import compare, config, topic, util
from p3.util import P3Error

OK, TODO, WARN, FAIL = "OK", "TODO", "WARN", "FAIL"
SECTIONS = ("498E", "598E")
LENGTH_STUDY = "length-study"
LADDER = ("c0-baseline", "c1-skills", "c2-review", "c3-split", "final")
SKILLED = ("c1-skills", "c2-review", "c3-split", "final")
SKILLS = ("teach", "tutor", "quiz", "grade")
DOCS = ("README.md", "DECISIONS.md", "EVAL.md", "LEARNING-LOG.md")
SHARED_RUNS = {"c0-baseline": 3, "c1-skills": 1, "c2-review": 1, "c3-split": 1, "final": 3}
ABLATION_PREFIX = "final-minus-"
ABLATION_RUNS = 1
BENCH_MINUTES = 30
SHARED_COMPARES = (
    ("c0-baseline", "c1-skills", ("teach", "quiz", "grade", "tutor")),
    ("c1-skills", "c2-review", ("teach", "quiz", "grade")),
    ("c2-review", "c3-split", ("teach",)),
    ("c0-baseline", "final", ("teach", "quiz", "grade", "tutor")),
)
OWN_COMPARE_JOBS = ("teach", "grade", "tutor")
OWN_TOPICS = 2
STUDY_CONFIGS = ("c1-skills", "final")
STUDY_MINUTES = (10, 30, 60)
STUDY_RUNS = 3
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
            out.append(title)
            for item in items:
                out.append(f"  {item.status.ljust(width)}  {item.text}")
                shown = item.details[:MAX_DETAILS]
                out += [f"  {' ' * width}    {d}" for d in shown]
                if len(item.details) > MAX_DETAILS:
                    out.append(f"  {' ' * width}    ... and {len(item.details) - MAX_DETAILS} more")
            out.append("")
        integrity = [i for i in self.items(INTEGRITY) if i.status == FAIL]
        handin = self.items(HANDIN)
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
        return "\n".join(out) + "\n"


INTEGRITY = "Integrity"
HANDIN = "Hand-in"


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
    for tid, kind, folder in topic.list_topics(root):
        rel = util.posix(folder, root) + "/"
        v = topic.validate(folder, kind)
        found[tid] = v
        if v.errors:
            items.append(Item(FAIL, f"{rel} is not a valid topic ({_plural(len(v.errors), 'problem')})", v.errors + v.todos))
        elif v.todos:
            count = sum(int(m.group(1)) for t in v.todos if (m := re.search(r": (\d+) TODO", t)))
            items.append(Item(FAIL if final else TODO, f"{rel} is valid, with {_plural(count or len(v.todos), 'TODO marker')} still to fill in", v.todos))
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
            _need(items, final, False, f"{name} is missing")
            continue
        lines = _todo_lines(util.read_text(path))
        if lines:
            shown = ", ".join(map(str, lines[:10])) + (", ..." if len(lines) > 10 else "")
            _need(items, final, False, f"{name}: {_plural(len(lines), 'TODO marker')} left (line{'s' if len(lines) != 1 else ''} {shown})")
        else:
            _need(items, final, True, f"{name} is written")


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


def check_shared_runs(root: Path, final: bool, ablations: list[str], items: list[Item]) -> None:
    wanted = dict(SHARED_RUNS)
    wanted.update({name: ABLATION_RUNS for name in ablations})
    for name, n in wanted.items():
        have = len(_full_runs(root, name, util.SHARED_TOPIC, BENCH_MINUTES))
        where = f"on {util.SHARED_TOPIC} at {BENCH_MINUTES} minutes"
        if have >= n:
            text = f"runs of {name}: {_plural(have, 'scored full run')} {where} ({n} needed)"
        else:
            hint = f"p3 bench --config {name}" + (f" --repeats {n - have}" if n - have > 1 else "")
            text = f"runs of {name}: {have} of the {_plural(n, 'scored full run')} needed {where} ({hint})"
        _need(items, final, have >= n, text)


def check_own_topics(root: Path, final: bool, validations: dict[str, topic.Validation], items: list[Item]) -> list[str]:
    """Two own topics, each valid with no TODO, run by c0-baseline and final from committed items;
    returns their ids."""
    own = [tid for tid, kind, _ in topic.list_topics(root) if kind == topic.OWN]
    _need(items, final, len(own) == OWN_TOPICS, f"test topics in bench/own/: {len(own)} of {OWN_TOPICS}" + (f" ({', '.join(own)})" if own else " (p3 new-topic <id>)") + ("" if len(own) <= OWN_TOPICS else "; the hand-in needs exactly two"))
    git_ok = util.git_available(root)
    for tid in own:
        rel = f"bench/own/{tid}"
        v = validations.get(tid)
        _need(items, final, bool(v and v.ok(allow_todo=False)), f"{rel}/: " + ("valid, no TODO left" if v and v.ok(allow_todo=False) else "not finished (see its line above)"))
        missing = [name for name in ("c0-baseline", "final") if not _full_runs(root, name, tid)]
        _need(items, final, not missing, f"{rel}/: " + (f"no scored full run of {' or '.join(missing)} yet" if missing else "scored runs of c0-baseline and final"))
        runs = util.list_runs(None, tid, root=root)
        if not runs:
            continue
        if not git_ok:
            items.append(Item(WARN, f"{rel}/: not a git repository here, so whether each run used the committed items is not checked"))
            continue
        current = util.hash_tree(root / "bench" / "own" / tid)
        problems = []
        for rec in runs:
            run_rel = util.posix(rec.dir, root)
            commit, recorded = rec.run.get("topic_commit"), rec.run.get("topic_hash")
            if not commit:
                problems.append(f"{run_rel}: no topic_commit (was it run outside git?)")
                continue
            then = util.hash_tree_at_commit(commit, rel, root)
            if then is None:
                problems.append(f"{run_rel}: commit {commit[:12]} does not hold {rel}/ (commit and push the topic before running it)")
            elif then != recorded:
                problems.append(f"{run_rel}: the items it ran differ from {rel}/ as committed in {commit[:12]}")
            elif recorded != current:
                problems.append(
                    f"{run_rel}: {rel}/ has changed since this run; a test topic is frozen once it has runs, so restore it from git "
                    "(to fix a real mistake in it, follow \"Commit before the first run\" in bench/own/README.md)"
                )
        _need(items, final, not problems, f"{rel}/: " + ("every run used the committed items" if not problems else f"{_plural(len(problems), 'run')} not made from the committed items as they are now"), problems)
    return own


def check_compares(root: Path, final: bool, own: list[str], items: list[Item]) -> None:
    complete: dict[tuple[frozenset, str, str], str] = {}
    for path in compare.session_files(root):
        record, _ = _read_json(path)
        # a session made with p3 compare --quick pairs quick runs, which leave out most scenarios, and
        # one made with --teach-only pairs the length study's runs, not the ladder's full runs
        if isinstance(record, dict) and record.get("complete") is True and not record.get("quick") and not record.get("teach_only") and isinstance(record.get("configs"), list):
            complete.setdefault((frozenset(map(str, record["configs"])), str(record.get("job")), str(record.get("topic"))), str(record.get("session") or path.stem))
    wanted = [(a, b, job, util.SHARED_TOPIC) for a, b, jobs in SHARED_COMPARES for job in jobs]
    wanted += [("c0-baseline", "final", job, tid) for tid in own for job in OWN_COMPARE_JOBS]
    for a, b, job, tid in wanted:
        sid = complete.get((frozenset((a, b)), job, tid))
        hint = f"p3 compare {a} {b} --job {job}" + (f" --topic {tid}" if tid != util.SHARED_TOPIC else "")
        _need(items, final, sid is not None, f"compare {a} / {b}, {job} on {tid}: " + (f"complete ({sid})" if sid else f"no complete session yet ({hint})"))


def _teach_only(rec: util.RunRecord) -> bool:
    return util.run_kind(rec.run) == util.TEACH_ONLY


def prereg_commit(root: Path) -> tuple[str, datetime, str] | None:
    """(commit, time, sections 1 to 4) of the first commit of PREREG.md with no TODO marker before
    its section 5, or None."""
    for commit, when in util.git_log_path("PREREG.md", root):
        data = util.git_show_bytes(commit, "PREREG.md", root)
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
        _need(items, final, done, f"length study, {name}: scored teach-only runs {cells} minutes, of {STUDY_RUNS} each" + ("" if done else f" (p3 bench --config {name} --only teach --minutes M --repeats {STUDY_RUNS})"))
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
    check_copies(root, integrity)

    handin = report.section(HANDIN)
    study = settings.get("section") == "598E" or settings.get("stretch") == LENGTH_STUDY
    check_docs(root, final, study, handin)
    ablations = check_configs(root, final, handin)
    check_shared_runs(root, final, ablations, handin)
    own = check_own_topics(root, final, validations, handin)
    check_compares(root, final, own, handin)
    if study:
        check_length_study(root, final, handin)
    section = settings.get("section") or "no section"
    stretch = settings.get("stretch")
    report.header = f"p3 check{' --final' if final else ''}: {section}" + (f", stretch {stretch}" if stretch else "") + f" ({root})"
    return report


def main(args) -> int:
    """The p3 check command."""
    report = run_checks(final=bool(getattr(args, "final", False)))
    print(report.text(), end="")
    return report.exit_code()
