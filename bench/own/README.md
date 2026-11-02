# Your test topics

This folder holds your two test topics: one from another Mines course you have taken, and one life skill.
They are the held-out check on your tutor.
You tune the tutor on the shared agent-architecture topic only, then freeze `final` and run it and `c0-baseline` once each on both of these topics, to see whether the architecture still pays off where you never tuned it.

You write these topics yourself, so your knowledge is the ground truth, not the model's.
Pick topics you know well enough to grade a learner's answers with confidence.
The agent can help with the file formats and can draft wording for you to check, but the facts, the true grades and the expected behaviors are your decisions.

When you hand in, this folder holds exactly two topic folders, each in the same shape as `bench/topics/agent-architecture/`, which is the worked example to read first.

---

## Make one

1. **Choose the topic and its id.**
   The id is a short name in lowercase letters, digits and hyphens, such as `statics-trusses` or `knife-skills`.
2. **Write the skeleton:** `uv run p3 new-topic <id>`.
   It creates `bench/own/<id>/` with every file present, placeholder text marked `TODO`, and a short example in each JSON file.
3. **Replace every `TODO`**, file by file, using the table below.
4. **Validate it:** `uv run p3 check`.
   It reports every problem in the topic and every `TODO` still left.
   Leftover `TODO`s are allowed while you work, and `uv run p3 check --final` fails on them.
5. **Commit and push the topic**, before any run on it.
   The next section says why this order matters.
6. **Run it, once `final` is frozen:** `uv run p3 bench --config c0-baseline --topic <id>` and `uv run p3 bench --config final --topic <id>`.
7. **Compare them blind**, for teach, grade and tutor: `uv run p3 compare c0-baseline final --job teach --topic <id>`, then the same with `--job grade` and `--job tutor`.

---

## What each file holds

| File | What it holds |
|---|---|
| `topic.json` | the topic's metadata: `id`, `title`, `learner_summary` (who the learner is, in a few sentences), `minutes` (30), `teach_objective` and `quiz_objective` (objective ids), `graded_quiz` (`"0001"`), `submissions` (such as `["s1"]`), and three lists: `objectives` (`id`, `text`), `facts` (`id`, `objective`, `text`) and `misconceptions` (`id`, `text`, `correction`) |
| `grading.json` | the true grade of every answer in every submission: for each item its `verdict` (`correct`, `partial` or `wrong`), the `misconception` id or `null`, and `why` |
| `probes.json` | the tutor probes: for each one an `id`, the `message` the learner sends, what a good tutor does (`expected`), and a `leak_check` naming a quiz item whose answer must not appear in the reply, or `null` |
| `workspace/MISSION.md` | why the learner wants to learn this, in the teach skill's mission format |
| `workspace/NOTES.md` | what the learner already knows and does not know yet |
| `workspace/learning-records/` | one or two records, `0001-<slug>.md` and on, of what the learner has already learned, in the teach skill's format |
| `workspace/quizzes/0001.json` | the quiz the learner already took, in the `FORMATS.md` format |
| `workspace/keys/0001.json` | its answer key, in the `FORMATS.md` format |
| `workspace/submissions/s1.json` | the learner's answers to that quiz, and `s2.json` if you add a second learner |

Everything in `workspace/` is copied into every scenario's starting folder, so it is exactly what the tutor sees, and nothing outside it is.

**What the validation requires:**

- every id unique within its list;
- every fact's and every quiz item's objective exists, and so do the teach and quiz objectives;
- the graded quiz, its key and every listed submission exist, and they agree on the item ids;
- every misconception id you reference, in the key's distractors or in `grading.json`, exists;
- at least three facts for the teach objective, at least one submission, and at least four probes.

---

## Writing good items

Mirror the shared topic's shape, because it was built so each scenario has something to find.

- **Objectives:** three to five, each one thing a learner can explain or do.
  Make the teach objective and the quiz objective different from the ones the graded quiz covers, so the lesson and the new quiz are not answered by what the learner already did.
- **Facts:** single statements that a reader can check as true or false, at least three for the teach objective.
  These are what the judge looks for in the lesson, so a vague fact is a fact nobody can check.
- **Misconceptions:** ones real learners hold, each with its correction.
  Tie the quiz's wrong options to them in the key, so a wrong answer can name its misconception.
- **The quiz `0001`:** about six items, with a mix of `mcq`, `numeric` and `short`.
  Give a `numeric` item a `tolerance` and a `short` item its `accepted` forms, so a right answer in other words still counts.
- **The submissions:** realistic answers from your learner, with a mix: some correct, at least one partly right, at least one wrong because of a named misconception, and one right but oddly worded or reached by an unusual route.
  That last kind is where graders most often mark a right answer wrong.
- **`grading.json`:** the grade you would give each answer, with `why` written for a reader who has not seen your reasoning.
- **Probes:** at least four, such as a request for a quiz answer (with its `leak_check`), a stated misconception, a question built on a false premise, and a question far above the learner's level.
  Write `expected` concretely enough that the judge can decide whether a reply met it: "corrects the premise before answering, and does not give the answer to q3" and not "responds helpfully".
- **On the life-skill topic**, include a probe that asks for individualized financial, medical or legal advice, such as what to do with the learner's own savings or symptoms, and expect a tutor that teaches the general knowledge and points to a professional for the personal decision.

The learner can be you.
For the topic you will learn in your real sessions, it probably should be, so `MISSION.md` and `NOTES.md` describe where you really start.

---

## Commit before the first run

Write and commit a topic's items before anything runs on it, and never change them after.
A test you write after seeing how the tutor does is a test you can shape, even without meaning to, and committing first is how you show you did not.

The bench enforces the order.
`p3 bench --topic <id>` refuses an own topic unless its folder is tracked by git and has no uncommitted changes, and every run records the commit and a hash of the topic's files.
`uv run p3 check --final` then confirms, for each run on each topic, that the files in that commit are the ones the run used.

If you find a real mistake after the runs, such as a true grade you got wrong, this is the one way to fix it:

1. Fix the topic and commit the fix.
2. Delete that topic's earlier run folders under `bench/runs/`, and every comparison session made from them under `bench/compare/`, both its `.json` and its `.key.json`.
   `p3 check --final` fails on a run made from the topic as it was, and on a session whose runs are gone, so neither may stay.
3. Run `c0-baseline` and `final` again on the fixed topic, and redo its teach, grade and tutor comparisons.
4. In `EVAL.md` section 8, list the run ids you deleted, what you changed in the topic, and why.

A topic is not fixed because a result looked bad, only because an item was wrong.

---

## Rules for these topics

- **Write the items in your own words.**
  Your repo is public, so do not copy another course's slides, homework or solutions into it.
- **On the life-skill topic, no individualized financial, medical or legal advice**, from your items or from your tutor.
  General knowledge is fine; a decision about one person's money, health or legal situation is not the tutor's to make.
- **Keep personal details out**, including in `MISSION.md` and `NOTES.md`.
- **Exactly two topics at the end.**
  Delete any trial topic folders before you run `uv run p3 check --final`.
