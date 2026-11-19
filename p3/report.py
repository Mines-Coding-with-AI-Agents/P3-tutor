"""`p3 report`: Markdown tables of the scored runs, for pasting into EVAL.md.

    p3 report [--topic t] [--configs a,b,...] [--minutes M] [--quick] [--teach-only]
    p3 report --reviews
    p3 report --write

One row per config (and lesson length, when runs at several lengths exist) with each headline number
as the mean over its scored full runs and the range in brackets, then one cost table per job. A full
run ran every scenario: runs made with --only are left out, because a job they did not run would
count as zero tokens and minutes. --teach-only shows only the runs of the teach scenario alone (the
length study) instead, and --quick only the quick runs.

After those tables, in a report of the shared topic's full runs (the runs the major reviews review)
and once any review file in reviews/ holds a rating, comes "Your ratings": the 1 to 5 ratings of the
major reviews, one row per criterion grouped by job, one column per step, and a dash where there is
no rating. A report of a test topic, of quick runs or of teach-only runs leaves it out. --reviews
prints only that table.

--write writes REPORT.md at the repo root instead of printing: the shared topic's tables exactly as the
default report prints them, then "The ablation" (each final-minus-* config's scored run on the shared
topic at its default lesson length that is not a quick run, beside final's full runs, for the jobs
that run covered), one part per test topic in bench/own/ with scored full runs, and "Lesson length"
(the --teach-only tables) when teach-only runs exist. A part with nothing to show is left out.
--write takes no other option.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import p3
from p3 import reviews, topic, util
from p3.claude import COST_LABEL
from p3.util import P3Error

LADDER = ("c0-baseline", "c1-skills", "c2-review", "c3-split", "final")
QUALITY = (
    ("teach_facts_correct", "teach facts", "share"),
    ("teach_misconceptions", "teach misconc.", "count"),
    ("teach_length_ratio", "length ratio", "share"),
    ("teach_dead_links", "dead links", "count"),
    ("quiz_key_agreement", "key agreement", "share"),
    ("quiz_wrong_key", "wrong keys", "count"),
    ("quiz_ambiguous", "ambiguous items", "count"),
    ("grade_verdict_agreement", "verdict agreement", "share"),
    ("grade_false_wrong", "false wrong", "share"),
    ("grade_misconception_hit", "misconc. hit", "share"),
    ("tutor_leaks", "leaks", "count"),
    ("tutor_behavior_met", "behavior met", "share"),
)
COST = (
    ("tokens_total", "tokens", "tokens"),
    ("tokens_output", "output tokens", "tokens"),
    ("minutes", "minutes", "minutes"),
    ("subagents", "subagents", "count"),
    ("cost_usd_list", "list-price $", "usd"),
)
JOBS = ("teach", "quiz", "grade", "tutor")
REPORT_FILE = "REPORT.md"
ABLATION_PREFIX = "final-minus-"


def config_order(names) -> list[str]:
    """The ladder order: c0-baseline, c1-skills, c2-review, c3-split, final, final-minus-*, then the rest."""

    def key(name: str):
        if name in LADDER:
            return (0, LADDER.index(name), name)
        if name.startswith("final-minus-"):
            return (1, 0, name)
        return (2, 0, name)

    return sorted(set(names), key=key)


def _fmt(value: float, kind: str) -> str:
    if kind == "share":
        return f"{value:.2f}"
    if kind == "count":
        return f"{value:.1f}".removesuffix(".0")
    if kind == "tokens":
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"{value / 1_000:.1f}k"
        return f"{value:.0f}"
    if kind == "minutes":
        return f"{value:.1f}"
    if kind == "usd":
        return f"{value:.2f}"
    return str(value)


def cell(values: list, kind: str, runs: int) -> str:
    """mean (min-max) over the values that exist, with n= when fewer values than runs; "-" when none."""
    present = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not present:
        return "-"
    mean = sum(present) / len(present)
    text = _fmt(mean, kind)
    lo, hi = min(present), max(present)
    extra = []
    if len(present) > 1 and _fmt(lo, kind) != _fmt(hi, kind):
        extra.append(f"{_fmt(lo, kind)}-{_fmt(hi, kind)}")
    if len(present) < runs:
        extra.append(f"n={len(present)}")
    return f"{text} ({', '.join(extra)})" if extra else text


def table(header: list[str], rows: list[list[str]], left: int = 1) -> str:
    """A Markdown table: the first `left` columns aligned left, the others right."""
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" if i < left else "---:" for i in range(len(header))) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def ratings_table(root: Path | None = None) -> str | None:
    """The "Your ratings" section as Markdown, or None while no review file holds a rating."""
    found = reviews.all_ratings(root)
    if not any(found.values()):
        return None
    rows = []
    for job, criteria in reviews.CRITERIA.items():
        for name in criteria:
            rows.append([job, name] + [str(found.get(step, {}).get((job, name), "-")) for step in reviews.STEPS])
    out = [
        "## Your ratings", "",
        "Your ratings from 1 to 5 in the major reviews (reviews/<step>.md), which review full runs on the shared topic; "
        "a dash means no rating there yet, one that p3 check does not accept, or a job that step does not review (Tutor in c2-review; Quiz, Feedback and Tutor in c3-split).", "",
        table(["job", "criterion", *reviews.STEPS], rows, left=2), "",
    ]  # fmt: skip
    return "\n".join(out)


def groups(topic_id: str, configs: list[str] | None, minutes: int | None, quick: bool, teach_only: bool = False) -> list[tuple[str, int, list]]:
    """(config, minutes, [RunRecord]) of the scored runs of one kind (full runs, or teach-only runs
    with `teach_only`), in ladder order then by minutes."""
    found: dict[tuple[str, int], list] = {}
    kind = util.TEACH_ONLY if teach_only else util.FULL
    for rec in util.list_runs(topic=topic_id, scored=True, quick=quick, minutes=minutes, kind=kind):
        name = rec.run.get("config")
        if configs and name not in configs:
            continue
        found.setdefault((name, int(rec.run.get("minutes") or 0)), []).append(rec)
    order = configs or config_order(name for name, _ in found)
    out = []
    for name in order:
        for (cname, mins), recs in sorted(found.items(), key=lambda kv: kv[0][1]):
            if cname == name:
                out.append((name, mins, recs))
    return out


def result_tables(rows_by: list[tuple[str, int, list]], teach_only: bool = False, jobs: tuple[str, ...] = JOBS, notes: bool = True, total: bool = True) -> list[str]:
    """The Quality table and the cost tables of `rows_by` (as groups() gives them) as Markdown lines,
    ending with the line on what costs mean. `teach_only` keeps the teach checks alone, `jobs` the
    checks and cost tables of those jobs, `notes` the reading notes under the Quality table, and
    `total` the "Cost: all jobs" table."""
    several_lengths = len({m for _, m, _ in rows_by}) > 1
    out: list[str] = []
    head = ["config"] + (["minutes"] if several_lengths else []) + ["runs"]
    columns = [q for q in QUALITY if q[0].split("_")[0] in jobs and (not teach_only or q[0].startswith("teach_"))]
    quality_rows = []
    for name, mins, recs in rows_by:
        summaries = [r.score.get("summary") or {} for r in recs]
        row = [f"`{name}`"] + ([str(mins)] if several_lengths else []) + [str(len(recs))]
        row += [cell([s.get(key) for s in summaries], kind, len(recs)) for key, _, kind in columns]
        quality_rows.append(row)
    out += ["### Quality", "", table(head + [label for _, label, _ in columns], quality_rows), ""]
    if notes:
        out += [
            "Teach facts, key agreement, verdict agreement, false wrong, misconception hit and behavior met are shares (0 to 1); "
            "misconceptions, dead links, wrong keys, ambiguous items and leaks are counts per run.",
            "A dash means no run could be scored on that check, and n= says how many of the runs could.",
            "A job that failed counts against the config: no lesson scores 0 teach facts, no quiz and key 0 key agreement, a missing grades file disagrees on every item, "
            "and a tutor scenario with no reply is not met; leaks need a reply to check, so such a scenario is left out of them.",
            "The length ratio is a rough reading-time estimate (visible words / 150) over the minutes requested; 0.6 to 1.5 counts as on length.",
            "",
        ]
    for job in jobs + (("total",) if total else ()):
        cost_rows = []
        for name, mins, recs in rows_by:
            costs = [((r.score.get("summary") or {}).get("cost") or {}).get(job) or {} for r in recs]
            if not any(c.get("scenarios") for c in costs):
                continue
            row = [f"`{name}`"] + ([str(mins)] if several_lengths else []) + [str(len(recs))]
            row += [cell([c.get(key) for c in costs], kind, len(recs)) for key, _, kind in COST]
            cost_rows.append(row)
        if cost_rows:
            title = "Cost: all jobs" if job == "total" else f"Cost: {job}"
            out += [f"### {title}", "", table(head + [label for _, label, _ in COST], cost_rows), ""]
    out.append(f"Costs are per run, summed over the job's scenarios; list-price $ is the {COST_LABEL}.")
    return out


def report_text(
    topic_id: str = util.SHARED_TOPIC, configs: list[str] | None = None, minutes: int | None = None, quick: bool = False, teach_only: bool = False,
    ratings: bool = True,
) -> str:
    """The report as Markdown, ending with "Your ratings" when `ratings`, the report is of the shared
    topic's full runs, and any review holds one."""
    rows_by = groups(topic_id, configs, minutes, quick, teach_only)
    runs_word = "teach-only runs" if teach_only else "full runs"
    what = f"quick {runs_word}" if quick else (runs_word if teach_only else "full runs (quick runs and --only runs left out)")
    if not rows_by:
        hint = ""
        quick_others = sorted({name for name, _, _ in groups(topic_id, configs, minutes, not quick, teach_only)})
        teach_others = sorted({name for name, _, _ in groups(topic_id, configs, minutes, quick, not teach_only)})
        if quick_others and not quick:
            hint = f"; only quick runs are scored so far ({', '.join(quick_others)}): add --quick to see them"
        elif teach_others and not teach_only:
            hint = f"; only teach-only runs are scored so far ({', '.join(teach_others)}): add --teach-only to see them"
        else:
            kind = util.TEACH_ONLY if teach_only else util.FULL
            unscored = [r for r in util.list_runs(topic=topic_id, scored=False, quick=quick, minutes=minutes, kind=kind) if not configs or r.config in configs]
            if unscored:
                one = len(unscored) == 1
                noun = runs_word[:-1] if one else runs_word
                hint = f"; {len(unscored)} {noun} {'is' if one else 'are'} not scored yet: score {'it' if one else 'each'} with p3 score {util.posix(unscored[-1].dir, util.repo_root())}"
        raise P3Error(f"no scored {what} on topic {topic_id}" + (f" for {', '.join(configs)}" if configs else "") + (hint or "; run p3 bench first"))
    out = [f"## Results on {topic_id}", "", f"Scored {what}; each cell is the mean over the runs, with the range in brackets.", ""]
    out += result_tables(rows_by, teach_only=teach_only)
    yours = ratings_table() if ratings and topic_id == util.SHARED_TOPIC and not quick and not teach_only else None
    if yours:
        out += ["", yours.rstrip("\n")]
    return "\n".join(out) + "\n"


def _covered_jobs(run: dict) -> tuple[str, ...]:
    """The jobs a run had scenarios for, in JOBS order."""
    found = {sc.get("job") for sc in run.get("scenarios") or [] if isinstance(sc, dict)}
    return tuple(job for job in JOBS if job in found)


def ablation_text(root: Path | None = None) -> str | None:
    """The "The ablation" part of REPORT.md, or None when no final-minus-* config has a scored run on
    the shared topic at its default lesson length that is not a quick run. Per such config, its latest
    such run (a full run or an --only run) beside `final`'s scored full runs at that length: the
    Quality and cost tables of the jobs the ablation run covered, and for an --only run a line saying
    which scenarios it covered."""
    root = Path(root) if root else util.repo_root()
    minutes = topic.load(util.SHARED_TOPIC, root).minutes
    final = util.list_runs("final", util.SHARED_TOPIC, scored=True, minutes=minutes, quick=False, kind=util.FULL, root=root)
    names = sorted({r.run.get("config") for r in util.list_runs(topic=util.SHARED_TOPIC, scored=True, minutes=minutes, quick=False, root=root) if str(r.run.get("config")).startswith(ABLATION_PREFIX)})
    out: list[str] = []
    for name in config_order(names):
        rec = util.list_runs(name, util.SHARED_TOPIC, scored=True, minutes=minutes, quick=False, root=root)[-1]
        jobs = _covered_jobs(rec.run)
        if not jobs:
            continue
        rows_by = ([("final", minutes, final)] if final else []) + [(name, minutes, [rec])]
        out += [f"### `{name}`", ""]
        tables = result_tables(rows_by, jobs=jobs, notes=False, total=len(jobs) == len(JOBS))
        tables = ["#" + line if line.startswith("### ") else line for line in tables]  # one level under the config's heading
        if rec.run.get("only"):
            ids = ", ".join(str(sc.get("id")) for sc in rec.run.get("scenarios") or [] if isinstance(sc, dict))
            cut = tables.index("#### Quality") + 4
            tables[cut:cut] = [f"`{name}` was run with --only and covers only these scenarios: {ids}; its costs add up only those, while the costs of `final` add up every scenario of each job.", ""]
        out += tables + [""]
    if not out:
        return None
    intro = [
        "## The ablation", "",
        f"Each `{ABLATION_PREFIX}*` config's latest scored run on {util.SHARED_TOPIC} at {minutes} minutes (not a quick run) beside `final`'s scored full runs, for the jobs that run covered; each cell is the mean over the runs, with the range in brackets.", "",
    ]  # fmt: skip
    if not final:
        intro += ["`final` has no scored full run at this length yet, so only the ablation runs are shown.", ""]
    return "\n".join(intro + out).rstrip("\n") + "\n"


def _topic_part(topic_id: str, **kwargs) -> str | None:
    """report_text for a topic, or None when it has nothing to show."""
    try:
        return report_text(topic_id, **kwargs)
    except P3Error:
        return None


def report_file_text(root: Path | None = None, when: datetime | None = None) -> str | None:
    """The whole of REPORT.md, or None when no part has anything to show. Parts, in order: the note
    under "# Report", the shared topic's tables as p3 report prints them, "The ablation", one part per
    test topic in bench/own/, and "Lesson length" (the --teach-only tables)."""
    root = Path(root) if root else util.repo_root()
    when = (when or util.utc_now()).astimezone(timezone.utc)
    parts = []
    if shared := _topic_part(util.SHARED_TOPIC):
        parts.append(shared)
    ablation = ablation_text(root)
    if ablation:
        parts.append(ablation)
    for topic_id, kind, _folder in topic.list_topics(root):
        if kind == topic.OWN and (own := _topic_part(topic_id)):
            parts.append(own)
    lengths = _topic_part(util.SHARED_TOPIC, teach_only=True)
    if lengths:
        parts.append(lengths.replace(f"## Results on {util.SHARED_TOPIC}", "## Lesson length", 1))
    if not parts:
        return None
    note = (
        f"This file is written by `p3 report --write` (p3 {p3.__version__}, {when.strftime('%Y-%m-%d %H:%M')} UTC). "
        "Do not edit it by hand: it is written again whenever new runs are scored."
    )
    return "\n".join(["# Report", "", note, ""] + [part.rstrip("\n") + "\n" for part in parts])


def write_report(root: Path | None = None) -> Path:
    """Write REPORT.md at the repo root and return its path. Raises P3Error when there is nothing to report."""
    root = Path(root) if root else util.repo_root()
    text = report_file_text(root)
    if text is None:
        raise P3Error(f"no scored runs to report yet, so {REPORT_FILE} was not written; run p3 bench first")
    path = root / REPORT_FILE
    util.write_text(path, text)
    return path


def main(args) -> int:
    """The p3 report command."""
    if getattr(args, "write", False):
        others = [flag for flag, given in (
            ("--topic", args.topic is not None), ("--configs", bool(args.configs)), ("--minutes", args.minutes is not None),
            ("--quick", args.quick), ("--teach-only", bool(getattr(args, "teach_only", False))), ("--reviews", bool(getattr(args, "reviews", False))),
        ) if given]  # fmt: skip
        if others:
            raise P3Error(f"--write takes no other option, so run p3 report --write on its own (it was given with {', '.join(others)})")
        path = write_report()
        print(f"Wrote {path.name} at the repo root; run p3 report --write again after new runs are scored.")
        return 0
    if getattr(args, "reviews", False):
        yours = ratings_table()
        if yours is None:
            raise P3Error(
                "no ratings in reviews/ yet: each criterion of a major review (reviews/<step>.md) holds a line Rating: N, "
                f"N a whole number from {reviews.RATING_MIN} to {reviews.RATING_MAX}; p3 check says what each review still needs"
            )
        print(yours, end="")
        return 0
    configs = [c.strip() for c in args.configs.split(",") if c.strip()] if args.configs else None
    print(report_text(args.topic or util.SHARED_TOPIC, configs, args.minutes, args.quick, bool(getattr(args, "teach_only", False))), end="")
    return 0
