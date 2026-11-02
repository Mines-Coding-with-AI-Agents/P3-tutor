# Decision log

Your design document for `final`, in your own words.
About two pages in total.
`EVAL.md` says what each step bought and cost; this file says what you built and why it is built that way.

Answer these as you go, not the night before it is due.
Each answer is easier to write while the decision is still fresh, and a reason written down before the measurement is worth more than one written after it.
Specifics beat polish: name the files, the subagents and the numbers.

Each section ends with a marker line.
Replace that line with your answer.
`uv run p3 check --final` fails while any marker is left, so a finished log is part of being done.

Please do not let the agent write these for you.
These answers are about what you chose and what you knew, and the agent cannot know that.

---

## 1. The architecture

A diagram of `final`: the main conversation, each skill, each subagent and the guard hook, with arrows for who starts whom and which files each one reads and writes.
ASCII art in a code block or a Mermaid block are both fine; for example:

```
/quiz (skill, main conversation)  writes drafts/0002.json
  -> quiz-reviewer (subagent, fresh context)  reads drafts/, keys/
  <- revise, at most 2 rounds
  => quizzes/NNNN.json, keys/NNNN.json, reviews/NNNN-quiz.md
```

Draw yours, all four jobs, and delete the example.

TODO: your diagram.

---

## 2. The components

One row per component of `final`: every skill, every subagent, the guard, and anything else, such as a script or an MCP server.
The kind is skill, subagent, hook or other.
"Why this kind" is the question that matters most here: why is this a skill and not a subagent, or a subagent and not a step inside a skill, or a hook and not an instruction?

| Name | Kind | Job | Why this kind |
|---|---|---|---|
| TODO | | | |

---

## 3. The review loops

For each of teach, quiz and grade: who reviews, what is on each reviewer's checklist, how each reviewer gets a fresh context, how many rounds a loop may run and what ends it early, and what each loop records.
Then one design choice you could have made the other way, such as one reviewer against several, a cap of one round against three, or a reviewer that edits against one that only reports, and why you chose as you did.

TODO: your review loops.

---

## 4. The teach split

The roles you split the teach job into, what each one receives and returns, what runs in order and what in parallel, and who puts the lesson together at the end.
Why this split and not a smaller one?
What did you try that you took out again?

TODO: your teach split.

---

## 5. The guard

What the hook blocks and what it allows, how it tells the grader from the main conversation, which tools it covers, and how its tests show it works.
Then the gap you know of: one way the main conversation could still reach a key, or a case your tests do not cover, and why you accepted it or how you closed it.

TODO: your guard.

---

## 6. What I would cut first

If `final` had to get cheaper tomorrow, which component would you cut first, and which last?
Point at the evidence for each, in `EVAL.md` or in a run, and say what you expect the tutor to lose.

TODO: what you would cut first.
