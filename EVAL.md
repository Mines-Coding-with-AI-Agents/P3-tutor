# Evaluation report

This is the report on what each step of your architecture bought and what it cost.
I read it for one thing above all: whether each claim matches its evidence, including the steps that did not pay.
A step you measured carefully and then dropped is as good a result as a step that won.

Two kinds of material go here.
The tables are pasted from commands: `uv run p3 report --configs a,b` for the objective checks and the cost, and `uv run p3 compare --reveal <session-id>` for each blind comparison.
Paste them as they are, and name the session id or the run ids next to each one, so I can find them in `bench/compare/` and `bench/runs/`.
The prose is yours.

Each section ends with a marker line.
Replace that line with your own writing; `uv run p3 check --final` fails while one is left.

Words used below.
A **tally** is the wins for each config and the ties in one blind comparison, and the **p-value** is the reveal's two-sided sign test on the picks that were not ties: with 10 such picks, 8 for one config is suggestive and 9 is strong.
**Could tell** is the share of pairs where you said you could tell which config made which.
The objective checks use the names `p3 report` prints, such as `teach_facts_correct`, `quiz_key_agreement`, `grade_false_wrong` and `tutor_leaks`, and the README's section "The scenarios and the objective checks" says what each one measures.
**Cost** is tokens, output tokens, minutes and subagents per scenario, and the list-price equivalent, which is not what you pay on a subscription.

---

## 1. The baseline, `c0-baseline`

Paste the `p3 report` table for `c0-baseline` (three full runs on the shared topic).

TODO: paste the table and name the three run ids.

What did the baseline do well, and where did it fall short, for each of the four jobs?
Which of the gaps in `KNOWN-GAPS.md` did you see in your own runs, and did you find one that is not listed?
Which number moved the most from one run to the next, and what does that spread mean for a step measured on a single run?

TODO: your reading of the baseline.

---

## 2. Step 1: `c1-skills` against `c0-baseline`

### What you built

The four skills in two or three sentences each: what each one does that the baseline did not, and what you put in `PREFERENCES.md`.

TODO: describe the four skills and your preferences.

### Blind comparisons

Paste the reveal of each of the four sessions (teach, quiz, grade, tutor): the tally, the p-value, could tell, the reasons grouped by winner, and the objective checks.

TODO: paste the four reveals with their session ids.

### Objective checks and cost

Paste `uv run p3 report --configs c0-baseline,c1-skills`.

TODO: paste the report tables.

### Did it pay?

For each job: did the blind picks and the objective checks agree, and if not, which do you believe and why?
`c1-skills` is also the first config with your `PREFERENCES.md`, while `c0-baseline` keeps the neutral one: which of the differences could come from your preferences rather than the skills?
What did the step cost per scenario, and was the gain worth it?
Say what one run of `c1-skills` against three of `c0-baseline` lets you claim, and what it does not.

TODO: your judgment of step 1.

---

## 3. Step 2: `c2-review` against `c1-skills`

### The loops as they ran

For teach, quiz and grade: how many review rounds ran in your bench run, what the reviewers flagged, and whether the revisions moved anything you can point at, a fact corrected, an ambiguous item rewritten, feedback that changed.
Your review records in the run's outputs are the evidence; name the files.

TODO: what the review loops did in the run.

### Blind comparisons, objective checks and cost

Paste the reveals of the teach, quiz and grade sessions, and `uv run p3 report --configs c1-skills,c2-review`.

TODO: paste the three reveals and the report tables.

### Did it pay?

Which loop earned its cost and which did not?
If a loop ran several rounds and the final output was no better than the first draft, say so, because that is the finding.

TODO: your judgment of step 2.

---

## 4. Step 3: `c3-split` against `c2-review`

### Blind comparison, objective checks and cost

Paste the reveal of the teach session and `uv run p3 report --configs c2-review,c3-split`.

TODO: paste the reveal and the report tables.

### Did it pay?

What did the split change in the lesson: its structure, its figures, its references, its fit to you?
What did it cost in tokens, minutes and subagents against `c2-review`, and how much of that was overhead rather than writing?
With one teach pair, the tally is a single judgment, so lean on your reason and the objective checks, and say how confident you are.

TODO: your judgment of step 3.

---

## 5. `final` against `c0-baseline`, with repeats

### What went into `final`

What did you keep from each step, and what did you drop, and why?

TODO: what `final` is made of.

### Blind comparisons

Paste the reveals of the four sessions (teach, quiz, grade, tutor), three run pairs each.

TODO: paste the four reveals with their session ids.

### Objective checks and cost

Paste `uv run p3 report --configs c0-baseline,final`, with three scored runs of each.

TODO: paste the report tables.

### What the repeats let you claim

For each headline number: is the difference between the two configs larger than the spread between runs of the same config?
Where the ranges overlap, say "not distinguishable with three runs", and do not rank the two by their means.
Then the overall cost: how many times more tokens and minutes per scenario does `final` take, and for which jobs is it worth it?

TODO: your reading of `final` against the baseline.

---

## 6. The ablation

Which component did `final-minus-<x>` remove, and what did you expect to happen before you ran it?
Paste `uv run p3 report --configs final,final-minus-<x>`.
What changed, in quality and in cost, and does one run against three let you say the component matters?

TODO: your ablation, its prediction, its table and your reading.

---

## 7. The guard

What does your guard block, and what does it allow?
Paste the result of running its tests, and list the cases they cover: the main conversation reading `keys/` with each of Read, Grep, Glob and Bash, the grader reading them, and the reads that must still work.
Then the bench evidence that the hook runs in the bench and not only in its tests: the run id and scenario of a trace where it allowed the grader's read of `keys/` or blocked the main conversation's, since a hook that fails to start lets every call through.
Then `tutor_leaks` for `final` against `c0-baseline`, and any denial of the guard you found in a trace.

TODO: the guard, its tests and the evidence.

---

## 8. The test topics

### The two topics

Name each topic and its id, why you chose it, and the commit in which you committed its items, before its first run.
If you fixed a real mistake in a topic after its runs, as `bench/own/README.md` describes, list the run ids you deleted, what you changed and why.

TODO: your two topics and their commits.

### Results

For each topic, paste `uv run p3 report --topic <id> --configs c0-baseline,final` and the reveals of the teach, grade and tutor sessions.

TODO: paste the tables and the reveals for both topics.

### Did the architecture still pay off?

Compare each topic with the shared topic: did `final` win where it won before, and did it fail somewhere new?
Was there anything about the topic, its kind of knowledge or its learner, that explains the difference?
On the life-skill topic, did both configs stay inside general knowledge when your probe asked for personal advice?

TODO: your reading of the test topics.

---

## 9. The judge check

Take ten decisions the judge made: for example ten tutor replies it marked met or not met, or ten facts in a lesson it marked present and correct.
Label each one yourself before you look at the judge's verdict, and list your ten labels and its ten verdicts here, with the run id and the scenario of each.
How many of ten did you agree on?
Read the disagreements: is the judge wrong, are you, or is the expected behavior unclear?
What does that agreement mean for the judge numbers you reported above?

TODO: your ten labels, the agreement, and what it means.

---

## 10. A change that did not pay off

At least one change, anywhere in the project, that cost you tokens, time or complexity and did not buy a difference you could measure.
What was it, what did you expect, what did the evidence show, and what did you do about it?

TODO: the change that did not pay off.

---

## 11. The trade-offs

Looking at the whole ladder: which machinery paid for itself, which did not, and how do you know?
If you rebuilt this tutor for P4 with a third of the token budget, what would you keep?
Which number in this report do you trust least, and why?

TODO: your trade-offs.

---

## 12. The stretch

For 598E this is the rider, and its write-up goes here, with `PREREG.md` beside it.
Cover five things:

1. the option's name;
2. what you did, and the files that hold it;
3. the evidence: the blind comparisons, the objective checks and the cost it rests on, pasted or named;
4. what that evidence lets you claim, and what it does not;
5. one thing you would do next, and what result would tell you it worked.

TODO: your stretch.
