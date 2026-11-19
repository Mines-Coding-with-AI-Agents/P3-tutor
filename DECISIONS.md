# Decision log

The decisions you made on the ladder, in your own words.
About one to two pages in total: each answer is two to four sentences with one number or one quote in it.

This file is the write-up of the project since version 0.2.
It replaces `EVAL.md`, which you no longer need to write.
If you already wrote a section of `EVAL.md` that answers a prompt here, keep it and point to it, such as "See EVAL.md, section 3", with one sentence that gives the answer.

The numbers come from `REPORT.md`, which `uv run p3 report --write` writes from your scored runs, so you never copy a table by hand.
Your ratings come from your major reviews in `reviews/`.
Specifics beat polish: a short, honest answer with a number in it is worth more than a long vague one, and "it did not pay off" is a full answer when you measured it.

Answer prompts 1 to 3 as you finish each step, while the decision is still fresh, and the rest once `final` has its runs.
Each prompt ends with a marker line.
Replace that line with your answer.
`uv run p3 check` reports a marker as work still to do, and `uv run p3 check --final` fails while any marker is left.

Please do not let an agent write these for you.
They are about what you chose and what you saw, and the Builder and the Guide never write them.

---

## 1. Step 1: the skill change that mattered most

Of everything you changed while building `c1-skills`, which one change to a skill made the biggest difference, and how do you know?
Name the round, and give the evidence: a rating that moved, a check in `REPORT.md` that moved, or a quote from an output before and after.

TODO: your answer to prompt 1.

---

## 2. Step 2: which review loop earned its cost

In `c2-review` you put reviewers on teach, quiz and grade.
Which loop earned its cost and which did not?
For each of the two, give what it cost in tokens against `c1-skills` and one thing its reviewer caught, or say that it caught nothing.

TODO: your answer to prompt 2.

---

## 3. Step 3: whether splitting the teach job paid

`c3-split` splits the teach job across subagents.
Did the lesson get better by your own ratings, and what did the split cost against `c2-review`?
Say in one sentence whether you would pay that price again.

TODO: your answer to prompt 3.

---

## 4. `final`: what you kept, what you dropped, and a change that did not pay

Which components did `final` keep and which did it drop, and what rule did you use to decide?
Then name one change anywhere on the ladder that did not pay off: what you expected, what you measured, and what you did about it.

TODO: your answer to prompt 4.

---

## 5. The ablation

Which component did you remove, and what did you predict would happen to quality and to cost before you ran it?
Then the result, with the numbers of the ablation's run beside `final`'s, and what one run lets you claim and what it does not.

TODO: your answer to prompt 5.

---

## 6. Your blind picks against your open reviews

You reviewed `final` openly, knowing you built it, and then compared it with `c0-baseline` blind.
Give the blind tally for each job, and say where it agreed with your open reviews and where it did not.
Where they disagreed, say what you think happened.

TODO: your answer to prompt 6.

---

## 7. The test topic

You tuned the tutor on the shared topic only.
On your test topic, did `final` still beat `c0-baseline`, and was the gain smaller, the same, or larger than on the shared topic?
Give one number or one quote from each config's output on it.

TODO: your answer to prompt 7.

---

## 8. The judge check

The bench's judge scored your lessons' facts and your tutor's replies.
Label ten of the items it judged yourself, before you look at its verdicts.
On how many of the ten did you agree with it, and what was one disagreement about?

TODO: your answer to prompt 8.

---

## 9. The stretch

What you tried, what it showed, and the one number that says so.
For the length study, give the outcome your `PREREG.md` rule points to.
If you did not take a stretch, write "No stretch."

TODO: your answer to prompt 9.
