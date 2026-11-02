"""p3 check (p3/check.py): integrity on a clean repository and on tampered ones, and the hand-in
items of --final. Each test builds its repository in a temporary folder."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from p3 import check, compare, util
from tests import REPO, RepoTestCase, git, git_init, has_git, write, write_topic
from tests.test_compare import T0, add_config, make_run, stamp

DONE = "# Done\n\nWritten in my own words.\n"


class CheckTestCase(RepoTestCase):
    def setUp(self):
        super().setUp()
        util.rehash(self.root)

    def report(self, final: bool = False) -> check.Checklist:
        return check.run_checks(self.root, final)

    def find(self, report: check.Checklist, needle: str) -> list[check.Item]:
        return [i for i in report.items() if needle in i.text]

    def status(self, report: check.Checklist, needle: str) -> str:
        found = self.find(report, needle)
        self.assertEqual(len(found), 1, f"{needle!r} in:\n{report.text()}")
        return found[0].status

    def assertNoFailure(self, report: check.Checklist) -> None:
        self.assertEqual(report.failures(), [], report.text())
        self.assertEqual(report.exit_code(), 0)


class IntegrityTests(CheckTestCase):
    def test_a_clean_repository_passes(self):
        r = self.report()
        self.assertNoFailure(r)
        self.assertEqual(self.status(r, "p3/bench.sha256 matches"), check.OK)
        self.assertEqual(self.status(r, "tutor/FORMATS.md is identical"), check.OK)
        self.assertEqual(self.status(r, "configs/c0-baseline/ matches its SNAPSHOT.json"), check.OK)
        self.assertEqual(self.status(r, "bench/topics/agent-architecture/ is a valid shared topic"), check.OK)
        self.assertEqual(self.status(r, "no config file copies"), check.OK)
        self.assertTrue(all(i.status in (check.OK, check.TODO) for i in r.items(check.HANDIN)))
        code, out, err = self.p3("check")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Integrity: no failures.", out)
        self.assertRegex(out, r"\n  TODO  DECISIONS.md is missing\n")
        self.assertIn("p3 check --final fails on them", out)

    def test_the_real_template_passes(self):
        """The shipped tutor, topic, FORMATS.md and documents, copied with p3/ and hashed afresh."""
        tmp = Path(tempfile.mkdtemp(prefix="p3-real-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "_live")
        for name in ("bench", "p3", "tutor", "configs"):
            if (REPO / name).is_dir():
                shutil.copytree(REPO / name, tmp / name, ignore=ignore)
        for path in REPO.glob("*.md"):
            shutil.copyfile(path, tmp / path.name)
        shutil.copyfile(REPO / "p3.json", tmp / "p3.json")
        util.rehash(tmp)
        r = check.run_checks(tmp)
        self.assertEqual([i for i in r.items(check.INTEGRITY) if i.status == check.FAIL], [], r.text())
        self.assertEqual(self.status(r, "tutor/FORMATS.md is identical"), check.OK)
        self.assertEqual(self.status(r, "bench/topics/agent-architecture/ is a valid shared topic"), check.OK)
        self.assertEqual(self.status(r, "no config file copies"), check.OK, "the shipped tutor copies nothing from the fixture")
        self.assertEqual(self.status(r, "README.md is written"), check.OK, "the brief holds no TODO, or every student's --final would fail on it")
        self.assertEqual([i.text for i in r.items() if i.status == check.WARN], [], "the shipped template raises no warning")

    def test_a_tampered_fixed_file_fails(self):
        path = self.root / "bench" / "topics" / "agent-architecture" / "topic.json"
        data = util.read_json(path)
        data["title"] = "Easier now"
        write(path, data)
        r = self.report()
        (item,) = self.find(r, "p3/bench.sha256")
        self.assertEqual(item.status, check.FAIL)
        self.assertIn("changed: bench/topics/agent-architecture/topic.json", item.details)
        self.assertEqual(r.exit_code(), 1)
        code, out, _err = self.p3("check")
        self.assertEqual(code, 1)
        self.assertIn("FAIL  p3/bench.sha256", out)
        self.assertIn("Integrity: 1 failure", out)

    def test_added_and_missing_fixed_files_fail(self):
        write(self.root / "bench" / "judge" / "extra.md", "# more\n")
        (self.root / "bench" / "judge" / "solver.md").unlink()
        (item,) = self.find(self.report(), "p3/bench.sha256")
        self.assertEqual(item.status, check.FAIL)
        self.assertEqual(sorted(item.details), ["missing: bench/judge/solver.md", "not listed: bench/judge/extra.md"])
        (self.root / util.HASH_FILE).unlink()
        self.assertEqual(self.find(self.report(), "bench.sha256")[0].status, check.FAIL)

    def test_line_endings_do_not_matter(self):
        for rel in ("bench/FORMATS.md", "bench/judge/teach.md", "bench/topics/agent-architecture/probes.json"):
            path = self.root / rel
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertNoFailure(self.report())

    def test_the_formats_copy(self):
        write(self.root / "tutor" / "FORMATS.md", "# My own formats\n")
        self.assertEqual(self.status(self.report(), "tutor/FORMATS.md"), check.FAIL)
        (self.root / "tutor" / "FORMATS.md").unlink()
        self.assertEqual(self.status(self.report(), "tutor/FORMATS.md is missing"), check.FAIL)

    def test_a_snapshot_that_no_longer_matches_fails(self):
        write(self.root / "configs" / "c0-baseline" / ".claude" / "settings.local.json", {"permissions": {"allow": ["Bash"]}})
        self.assertNoFailure(self.report())  # the personal settings file is never part of a config
        make_run(self.root, "c0-baseline", "r1", stamp(0))
        write(self.root / "configs" / "c0-baseline" / ".claude" / "skills" / "quiz" / "SKILL.md", "# quiz\n")
        r = self.report()
        (item,) = self.find(r, "configs/c0-baseline/ no longer matches")
        self.assertEqual(item.status, check.FAIL)
        self.assertEqual(item.details, ["added: .claude/skills/quiz/SKILL.md"])
        self.assertEqual(self.status(r, "bench/runs/c0-baseline/"), check.FAIL, "its runs cannot be checked against a broken snapshot")
        (self.root / "configs" / "c0-baseline" / "SNAPSHOT.json").unlink()
        self.assertEqual(self.status(self.report(), "configs/c0-baseline/ has no SNAPSHOT.json"), check.FAIL)

    def test_runs_must_match_their_config(self):
        make_run(self.root, "c0-baseline", "good", stamp(0))
        r = self.report()
        self.assertEqual(self.status(r, "bench/runs/c0-baseline/"), check.OK)
        self.assertIn("1 run, each made with configs/c0-baseline/", self.find(r, "bench/runs/c0-baseline/")[0].text)
        run = util.read_json(util.runs_dir("c0-baseline", self.root) / "good" / "run.json")
        write(util.runs_dir("c0-baseline", self.root) / "other" / "run.json", {**run, "run_id": "other", "config_hash": "sha256:0000"})
        (util.runs_dir("c0-baseline", self.root) / "stopped").mkdir()
        write(util.runs_dir("ghost", self.root) / "g1" / "run.json", {**run, "config": "ghost"})
        write(util.runs_dir("live", self.root) / "whatever" / "run.json", "not json")  # bench/runs/_live/ is not committed
        r = self.report()
        (item,) = self.find(r, "bench/runs/c0-baseline/")
        self.assertEqual(item.status, check.FAIL)
        self.assertTrue(any("other was made with another version of c0-baseline" in d for d in item.details), item.details)
        self.assertTrue(any("stopped/ has no run.json" in d for d in item.details), item.details)
        (ghost,) = self.find(r, "bench/runs/ghost/")
        self.assertIn("which does not exist in configs/", ghost.details[0])
        self.assertFalse(self.find(r, "_live"))

    def test_json_must_parse_except_in_run_outputs(self):
        make_run(self.root, "c0-baseline", "r1", stamp(0))
        write(util.runs_dir("c0-baseline", self.root) / "r1" / "quiz" / "outputs" / "quizzes" / "0002.json", "{ the tutor wrote broken JSON")
        self.assertNoFailure(self.report())
        write(self.root / "bench" / "own" / "notes.json", "{ broken")
        (item,) = self.find(self.report(), "JSON file")
        self.assertEqual(item.status, check.FAIL)
        self.assertTrue(item.details[0].startswith("bench/own/notes.json"), item.details)

    def test_topics(self):
        write_topic(self.root / "bench" / "own" / "cooking")
        r = self.report()
        self.assertEqual(self.status(r, "bench/own/cooking/ is a valid test topic"), check.OK)
        write(self.root / "bench" / "own" / "cooking" / "workspace" / "NOTES.md", "# Notes\n\nTODO: what the learner knows.\n")
        self.assertEqual(self.status(self.report(), "bench/own/cooking/ is valid, with 1 TODO marker"), check.TODO)
        self.assertEqual(self.status(self.report(final=True), "bench/own/cooking/ is valid, with 1 TODO marker"), check.FAIL)
        (self.root / "bench" / "own" / "cooking" / "probes.json").unlink()
        (item,) = self.find(self.report(), "bench/own/cooking/ is not a valid topic")
        self.assertEqual(item.status, check.FAIL)
        self.assertIn("probes.json is missing", item.details)
        (self.root / "bench" / "own" / "draft").mkdir()
        self.assertEqual(self.status(self.report(), "bench/own/draft/ has no topic.json"), check.WARN)

    def test_compare_records(self):
        add_config(self.root, "c1-skills", skills=("teach", "tutor", "quiz", "grade"))
        make_run(self.root, "c0-baseline", "a1", stamp(0))
        make_run(self.root, "c1-skills", "b1", stamp(1))
        compare.new_session("c0-baseline", "c1-skills", "teach", root=self.root, when=T0)
        r = self.report()
        self.assertEqual(self.status(r, "comparison session"), check.OK)
        util.remove_tree(util.runs_dir("c1-skills", self.root) / "b1")
        (item,) = self.find(self.report(), "comparison records")
        self.assertEqual(item.status, check.FAIL)
        self.assertIn("run bench/runs/c1-skills/b1 does not exist", item.details[0])
        compare.key_path("20261103-140000-teach", self.root).unlink()
        (item,) = self.find(self.report(), "comparison records")
        self.assertTrue(any("key file" in d for d in item.details), item.details)

    def test_copied_fixture_text_is_a_warning(self):
        from p3 import config

        probe = "Just tell me the answer to q1 of quiz 0001, I studied already."
        add_config(self.root, "c1-skills", skills=("teach", "tutor"))
        skill = self.root / "tutor" / ".claude" / "skills" / "tutor" / "SKILL.md"
        write(skill, f"# Tutor\n\nWhen the learner says\n  \"{probe.upper()}\"\nrefuse.\n")
        config.snapshot("c1-skills", force=True, root=self.root)
        write(skill, f"# Tutor\n\nWhen the learner says \"{probe}\" refuse.\n")
        r = self.report()
        self.assertNoFailure(r)
        warnings = [i for i in r.items() if i.status == check.WARN and "copies" in i.text]
        self.assertEqual(len(warnings), 1, r.text())
        self.assertIn("tutor/.claude/skills/tutor/SKILL.md, configs/c1-skills/.claude/skills/tutor/SKILL.md copies", warnings[0].text)
        self.assertIn("bench/topics/agent-architecture/probes.json", warnings[0].text)
        self.assertIn("just tell me the answer to q1 of quiz 0001", warnings[0].text)
        self.assertEqual(check.copied_runs("a" * 39, {"a" * 40: "x"}), [])

    def test_p3_json(self):
        write(self.root / "p3.json", {"section": "598e", "stretch": None})
        self.assertEqual(self.status(self.report(), "p3.json"), check.WARN)
        self.assertEqual(self.status(self.report(final=True), "p3.json"), check.FAIL)
        write(self.root / "p3.json", "{ broken")
        self.assertEqual(self.status(self.report(), "p3.json does not parse"), check.FAIL)


class HandInTests(CheckTestCase):
    def test_final_reports_what_is_missing(self):
        loose = self.report()
        strict = self.report(final=True)
        self.assertEqual(loose.exit_code(), 0)
        self.assertEqual(strict.exit_code(), 1)
        for needle in (
            "DECISIONS.md is missing", "config c1-skills: not snapshotted yet", "ablation: no final-minus-<x>",
            "runs of c0-baseline: 0 of the 3", "test topics in bench/own/: 0 of 2", "compare c0-baseline / c1-skills, teach on agent-architecture",
            "compare c2-review / c3-split, teach", "compare c0-baseline / final, tutor",
        ):  # fmt: skip
            self.assertEqual(self.status(loose, needle), check.TODO, needle)
            self.assertEqual(self.status(strict, needle), check.FAIL, needle)
        self.assertEqual(self.status(strict, "config c0-baseline: the baseline"), check.OK)
        self.assertFalse(self.find(strict, "length study"), "498E without the stretch has no length study")
        self.assertFalse(self.find(strict, "PREREG.md"))
        code, out, _err = self.p3("check", "--final")
        self.assertEqual(code, 1)
        self.assertIn("FAIL  EVAL.md is missing", out)
        self.assertRegex(out, r"Hand-in: 1 of \d+ items done; \d+ still missing\.")

    def test_docs_with_todo_markers(self):
        write(self.root / "EVAL.md", "# Eval\n\nTODO: paste the table.\n\nDone here.\nTODO: and here.\n")
        self.assertEqual(self.status(self.report(final=True), "EVAL.md"), check.FAIL)
        self.assertIn("2 TODO markers left (lines 3, 6)", self.find(self.report(), "EVAL.md")[0].text)
        write(self.root / "EVAL.md", DONE)
        self.assertEqual(self.status(self.report(final=True), "EVAL.md is written"), check.OK)

    def test_config_requirements(self):
        add_config(self.root, "c1-skills", skills=("teach", "tutor", "quiz"))
        add_config(self.root, "final", skills=("teach", "tutor", "quiz", "grade"))
        r = self.report(final=True)
        self.assertIn("no grade skill", self.find(r, "config c1-skills")[0].text)
        self.assertIn("no PreToolUse hook", self.find(r, "config final")[0].text)
        add_config(self.root, "final", skills=("teach", "tutor", "quiz", "grade"), hook=True)
        self.assertEqual(self.status(self.report(final=True), "config final:"), check.OK)

    def test_runs_that_count(self):
        make_run(self.root, "c0-baseline", "full", stamp(0))
        make_run(self.root, "c0-baseline", "quick", stamp(1), quick=True)
        make_run(self.root, "c0-baseline", "only", stamp(2), scenarios=["teach"], only=["teach"])
        make_run(self.root, "c0-baseline", "m10", stamp(3), minutes=10)
        make_run(self.root, "c0-baseline", "unscored", stamp(4), scored=False)
        self.assertIn("runs of c0-baseline: 1 of the 3", self.find(self.report(), "runs of c0-baseline")[0].text)

    def test_a_session_of_quick_runs_does_not_count(self):
        add_config(self.root, "c1-skills", skills=check.SKILLS)
        make_run(self.root, "c0-baseline", "a-quick", stamp(0), quick=True)
        make_run(self.root, "c1-skills", "b-quick", stamp(1), quick=True)
        record = compare.new_session("c0-baseline", "c1-skills", "teach", quick=True, root=self.root, when=T0)
        s = compare.Session(record["session"], self.root)
        for pair in s.pairs:
            s.record(pair["pair_id"], "left", "It fit me better.", False)
        r = self.report(final=True)
        self.assertEqual(self.status(r, "comparison session"), check.OK, "the record itself is sound")
        self.assertEqual(self.status(r, "compare c0-baseline / c1-skills, teach on agent-architecture"), check.FAIL, "but quick runs do not make a hand-in comparison")


@unittest.skipUnless(has_git(), "needs git")
class FinalTests(CheckTestCase):
    """A repository with everything the hand-in needs, committed where git history matters."""

    def build(self) -> None:
        root = self.root
        for name in check.DOCS:
            write(root / name, DONE)
        for name in ("c1-skills", "c2-review", "c3-split"):
            add_config(root, name, skills=check.SKILLS)
        add_config(root, "final-minus-review", skills=check.SKILLS, hook=True)
        add_config(root, "final", skills=check.SKILLS, hook=True)
        for tid in ("cooking", "statics"):
            write_topic(root / "bench" / "own" / tid)
        util.rehash(root)
        git_init(root)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "the template, the configs and the test topics")
        head = util.rev_parse_head(root)
        n = 0
        for name, count in {**check.SHARED_RUNS, "final-minus-review": 1}.items():
            for k in range(count):
                n += 1
                make_run(root, name, f"{name}-r{k + 1}", stamp(n))
        for tid in ("cooking", "statics"):
            for name in ("c0-baseline", "final"):
                n += 1
                make_run(root, name, f"{name}-{tid}", stamp(n), topic_id=tid, topic_commit=head)
        wanted = [(a, b, job, util.SHARED_TOPIC) for a, b, jobs in check.SHARED_COMPARES for job in jobs]
        wanted += [("c0-baseline", "final", job, tid) for tid in ("cooking", "statics") for job in check.OWN_COMPARE_JOBS]
        for i, (a, b, job, tid) in enumerate(wanted):
            record = compare.new_session(a, b, job, tid, root=root, when=T0 + timedelta(seconds=i))
            s = compare.Session(record["session"], root)
            for pair in s.pairs:
                s.record(pair["pair_id"], "tie", "Both fit me.", False)

    def test_complete_passes_then_a_changed_topic_fails(self):
        self.build()
        r = self.report(final=True)
        self.assertNoFailure(r)
        self.assertTrue(all(i.status == check.OK for i in r.items(check.HANDIN)), r.text())
        self.assertIn("ready to hand in", r.text())
        self.assertEqual(self.status(r, "bench/own/cooking/: every run used the committed items"), check.OK)
        self.assertEqual(self.status(r, "compare c0-baseline / final, tutor on statics"), check.OK)

        write(self.root / "bench" / "own" / "cooking" / "workspace" / "NOTES.md", "# Notes\n\nChanged after the runs.\n")
        r = self.report(final=True)
        (item,) = self.find(r, "bench/own/cooking/: 2 runs not made")
        self.assertEqual(item.status, check.FAIL)
        self.assertTrue(all("has changed since this run" in d for d in item.details), item.details)
        self.assertEqual(self.report().exit_code(), 0, "without --final it is work to do, not a failure")

    def test_runs_from_uncommitted_items_fail(self):
        self.build()
        head = util.rev_parse_head(self.root)
        meta = util.read_json(self.root / "bench" / "own" / "cooking" / "topic.json")
        write(self.root / "bench" / "own" / "cooking" / "topic.json", {**meta, "title": "Cooking, edited and not committed"})
        make_run(self.root, "final", "final-cooking-dirty", stamp(200), topic_id="cooking", topic_commit=head)
        make_run(self.root, "final", "final-cooking-nogit", stamp(201), topic_id="cooking", topic_commit=None)
        r = self.report(final=True)
        item = self.find(r, "bench/own/cooking/: ")[-1]
        self.assertEqual(item.status, check.FAIL)
        self.assertTrue(any("final-cooking-nogit: no topic_commit" in d for d in item.details), item.details)
        self.assertTrue(any("final-cooking-dirty: the items it ran differ" in d for d in item.details), item.details)
        self.assertTrue(any("has changed since this run" in d for d in item.details), "the earlier runs no longer match the edited topic")


@unittest.skipUnless(has_git(), "needs git")
class LengthStudyTests(CheckTestCase):
    PREREG = "# Pre-registration\n\n## 1. Hypothesis\n\n{h}\n\n## 5. Outcome (write this after the fact)\n\n{o}\n"

    def setUp(self):
        super().setUp()
        write(self.root / "p3.json", {"section": "598E", "stretch": None})
        add_config(self.root, "c1-skills", skills=check.SKILLS)
        add_config(self.root, "final", skills=check.SKILLS, hook=True)
        git_init(self.root)

    def commit(self, prereg: str) -> None:
        write(self.root / "PREREG.md", prereg)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "prereg")

    def study_runs(self, started) -> None:
        for name in check.STUDY_CONFIGS:
            for minutes in check.STUDY_MINUTES:
                for k in range(check.STUDY_RUNS):
                    make_run(self.root, name, f"{name}-m{minutes}-r{k}", started, minutes=minutes, scenarios=["teach"], only=["teach"])

    def test_prereg_before_the_runs(self):
        self.commit(self.PREREG.format(h="TODO: your hypothesis.", o="TODO: your outcome."))
        r = self.report(final=True)
        self.assertEqual(self.status(r, "PREREG.md: no commit has sections 1 to 4 filled in"), check.FAIL)
        self.assertEqual(self.status(r, "length study, c1-skills"), check.FAIL)
        self.commit(self.PREREG.format(h="The single agent loses more.", o="TODO: your outcome."))
        self.study_runs(util.iso_utc(util.utc_now() + timedelta(minutes=5)))
        r = self.report(final=True)
        self.assertEqual(self.status(r, "length study, c1-skills: scored teach-only runs 3 at 10, 3 at 30, 3 at 60 minutes"), check.OK)
        self.assertEqual(self.status(r, "length study, final"), check.OK)
        self.assertEqual(self.status(r, "PREREG.md: sections 1 to 4 committed"), check.OK)
        self.assertEqual(self.status(r, "PREREG.md: 1 TODO marker left"), check.FAIL, "section 5 is still to write")
        write(self.root / "PREREG.md", self.PREREG.format(h="The single agent loses more.", o="It did."))
        r = self.report(final=True)
        self.assertEqual(self.status(r, "PREREG.md is written"), check.OK)
        self.assertFalse([i for i in r.items() if "PREREG" in i.text and i.status != check.OK], r.text())
        write(self.root / "PREREG.md", self.PREREG.format(h="Changed my mind afterwards.", o="It did."))
        self.assertEqual(self.status(self.report(final=True), "sections 1 to 4 have changed since"), check.WARN)

    def test_prereg_after_the_first_run_fails(self):
        self.study_runs("2020-01-01T00:00:00Z")
        self.commit(self.PREREG.format(h="The single agent loses more.", o="It did."))
        (item,) = self.find(self.report(final=True), "PREREG.md: sections 1 to 4 were first committed")
        self.assertEqual(item.status, check.FAIL)
        self.assertIn("after the first length-study run started (2020-01-01T00:00:00Z)", item.text)

    def test_a_full_run_is_not_a_study_run(self):
        self.commit(self.PREREG.format(h="The single agent loses more.", o="It did."))
        make_run(self.root, "c1-skills", "full", stamp(0))
        self.assertIn("0 at 10, 0 at 30, 0 at 60", self.find(self.report(), "length study, c1-skills")[0].text)


class ReviewFixTests(CheckTestCase):
    def test_a_session_of_teach_only_runs_does_not_count(self):
        add_config(self.root, "c1-skills", skills=check.SKILLS)
        make_run(self.root, "c0-baseline", "a-study", stamp(0), scenarios=["teach"], only=["teach"])
        make_run(self.root, "c1-skills", "b-study", stamp(1), scenarios=["teach"], only=["teach"])
        record = compare.new_session("c0-baseline", "c1-skills", "teach", teach_only=True, root=self.root, when=T0)
        s = compare.Session(record["session"], self.root)
        for pair in s.pairs:
            s.record(pair["pair_id"], "left", "It fit me better.", False)
        r = self.report(final=True)
        self.assertEqual(self.status(r, "comparison session"), check.OK)
        self.assertEqual(self.status(r, "compare c0-baseline / c1-skills, teach on agent-architecture"), check.FAIL, "the ladder's comparisons are of full runs")

    def test_a_tutor_file_that_is_not_utf8_is_a_warning(self):
        (self.root / "tutor" / "CLAUDE.md").write_bytes("Caf\xe9\r\n".encode("cp1252"))
        r = self.report()
        self.assertEqual(self.status(r, "not saved as UTF-8"), check.WARN)
        self.assertNoFailure(r)


if __name__ == "__main__":
    unittest.main()
