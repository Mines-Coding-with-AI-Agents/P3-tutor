# Project 3 - Build a Tutoring Agent

**CSCI 498E / 598E - Coding with AI Agents**

| | |
|---|---|
| **Weight** | 20% of your final grade |
| **Points** | 200 on Canvas: 150 for this project and 50 for a video, handed in together in one discussion post |
| **Released** | Tuesday, November 3 (lecture 19) |
| **Due** | Tuesday, November 24, 11:59 pm, one deadline for everything |
| **Work** | Individual; 598E adds a rider (below) |

You hand in three things:

1. A **public GitHub repo** made from this template, whose URL you post in the Project 3 discussion on Canvas.
2. The **work inside it**: your tutor in `tutor/` with its four skills and whatever else you built, every snapshot on the architecture ladder in `configs/`, your bench runs in `bench/runs/` and blind comparisons in `bench/compare/`, your two test topics in `bench/own/`, and `EVAL.md`, `DECISIONS.md` and `LEARNING-LOG.md` written in your own words, plus `PREREG.md` for 598E or the length-study stretch.
3. A **5 to 10 minute video**, in the same discussion post.

---

## What this project is

You build a tutor that runs entirely inside Claude Code and does four jobs.

| Job | What it does |
|---|---|
| **Teach** | writes a comprehensive lesson of a requested length, such as 30 minutes or an hour: a plan, explanations, examples, figures and visualizations, and external references where they help |
| **Tutor** | a conversational helper the learner talks to on the go, personalized to how the learner likes to talk, with guardrails: it does not hand out quiz answers |
| **Quiz** | a quiz with an answer key, at the right difficulty, covering the core of the lesson, clearly worded and aligned with the learning goals |
| **Grade** | grades plus useful feedback: a verdict on each answer and enough explanation, in the way this learner likes things explained |

The template ships a tutor that already does all four, with one `teach` skill doing everything in one shot.
You build four skills of your own, then add agentic architecture in fixed steps, first review loops and then a split of the teach job, and you measure every step: what it gained in quality, and what it cost in tokens and time.

Much of a tutor's quality is personal fit, so you are the judge, blind to which configuration made what.
Fixed objective checks catch what taste cannot: a wrong fact, a wrong answer key, a quiz answer given away.

The tutor is not the point; the engineering judgment is.
Lectures 18 and 19 asked when a fixed workflow beats an agent and whether more agents help.
Here you find out for one real system of your own: which machinery pays for itself, which does not, and how you know.
It uses what lectures 15 to 19 taught (skills, MCP, hooks, workflows and agents, multi-agent systems), and lectures 20 to 24 arrive while you work on it: the agent loop from scratch and the Agent SDK, construct validity, repeats with intervals, and judges.

I made four choices you should know about, because they shape the rest of this brief.
The baseline is competent on purpose.
It keeps the teach skill's pedagogy and meets the output contract, because a broken baseline makes every change look like a win, and the honest question is whether your machinery beats a good simpler system.
The steps are fixed and their design is yours.
Everyone builds the same kinds of architecture, so the class's results can be compared, and what each reviewer checks, how many rounds it may run and how you split the teach job are your decisions.
You judge quality blind, because you built the later versions and you expect them to win.
And every step is measured in cost as well as quality, because a review loop or a pipeline of subagents is never free, and a gain is only worth having at a price you can name.

### The repo, and who owns what

The rule behind the layout is simple: I own everything that runs the measurement, and you own everything that decides how the tutor behaves.

| Path | What it is | Whose |
|---|---|---|
| `tutor/` | the tutor: `CLAUDE.md`, `PREFERENCES.md`, `FORMATS.md` and `.claude/` (skills, agents, settings) | yours |
| `configs/` | snapshots of the tutor; `c0-baseline` ships, and you add the rest with `p3 snapshot` | yours, written by `p3` |
| `bench/FORMATS.md`, `bench/scenarios.json`, `bench/judge/`, `bench/topics/` | the output contract, the scenarios, the judge prompts and the shared topic | mine, hash-checked |
| `bench/own/` | your two test topics | yours |
| `bench/runs/`, `bench/compare/` | your committed runs and blind comparisons | written by `p3` |
| `p3/` | the runner, the scorer, the comparison tool and the check | mine, hash-checked |
| `tests/` | the tests of `p3`, and the place for your guard's tests | mine, plus the tests you add |
| `EVAL.md`, `DECISIONS.md`, `LEARNING-LOG.md`, `PREREG.md` | your write-up | yours |
| `KNOWN-GAPS.md` | failures I saw when I ran the baseline, each with the run that shows it | mine |
| `p3.json` | your section and your stretch | yours |
| `CLAUDE.md` | orientation for Claude Code when you develop at the repo root | mine |

**The tutor lives in `tutor/`, not at the root.**
You develop it from the root, and you learn with it by starting Claude Code inside `tutor/`, so the tutor's `CLAUDE.md` is never the one you develop with.

**A config is `tutor/CLAUDE.md`, `tutor/PREFERENCES.md` and everything under `tutor/.claude/`.**
The learner's files (`MISSION.md`, `NOTES.md`, `lessons/`, `quizzes/`, `keys/`, `grades/`, `learning-records/`, `assets/`, `submissions/`) are never part of a config.
Neither is `tutor/.claude/settings.local.json`, the personal file Claude Code writes when you approve a tool in a session of your own, so anything the tutor needs goes in `tutor/.claude/settings.json`.
`uv run p3 snapshot <name>` copies the live config into `configs/<name>/` and records a hash of its files in `configs/<name>/SNAPSHOT.json`, and the bench runs any snapshot by name.
I use snapshots rather than git tags because git does not push tags by default, and a run must always point at a config I can read.

**Who the learner is splits in two.**
A topic says what the learner knows: on the shared topic that is a fixed novice, described in the topic's `MISSION.md` and `NOTES.md`.
`tutor/PREFERENCES.md` says how the learner likes to learn, and it is yours on every topic: how you like things explained, the examples you relate to, how long and dense you like it, how you like feedback.
That file is what makes the blind comparisons personal, so write it in the first week and mean it.

### The output contract

`bench/FORMATS.md` says exactly what the bench reads, with a complete example of each JSON file, and `tutor/FORMATS.md` is an identical copy for your tutor to follow.

| Output | File | In short |
|---|---|---|
| Lesson | `lessons/NNNN-<slug>.html` | a complete, self-contained HTML page with two meta tags, `p3-minutes` and `p3-objective`; CSS inline or under `assets/`, no remote scripts or stylesheets, ordinary links to outside references welcome |
| Quiz | `quizzes/NNNN.json` | the items: id, type `mcq`, `numeric` or `short`, the objective each one serves, the stem, and options for `mcq` |
| Key | `keys/NNNN.json` | for each item the answer, accepted forms, a rationale, and the misconception behind each wrong option |
| Grades | `grades/NNNN-sN.json` | for each item a verdict (`correct`, `partial` or `wrong`), the misconception id if one applies, and the feedback |
| Learning record | `learning-records/NNNN-<slug>.md` | what the learner learned, in the teach skill's format |

A new file takes the next four-digit number after the highest one in its folder.
Everything else about how your tutor works is yours, but these files must match the contract, because the contract is what lets one script score every student's tutor.

### The architecture ladder

| Config | What it adds | Full bench runs on the shared topic |
|---|---|---|
| `c0-baseline` | nothing, as shipped: one `teach` skill, one shot | 3 |
| `c1-skills` | the four skills `teach`, `tutor`, `quiz` and `grade`, plus any others you like; still one agent | 1 |
| `c2-review` | review loops on teach, quiz and grade, as subagents | 1 |
| `c3-split` | the teach job split across subagents (planner, designer, writer, visual designer, references, and so on) | 1 |
| `final` | what earned its place (a step that did not pay may be dropped), plus a guard hook keeping the answer keys from the tutor | 3 |
| `final-minus-<x>` | `final` with one component removed, the ablation | 1 |

Each step is measured against the one before it, in quality (blind comparisons and objective checks) and in cost (tokens, turns, subagents and time).
The ablation names what it removes, for example `final-minus-quiz-review` or `final-minus-planner`, and you need at least one.
Config names use lowercase letters, digits and hyphens.

**The same loop, at every step:**

1. Change the tutor in `tutor/`.
2. Try it cheaply with `uv run p3 bench --config live --quick`, which runs `tutor/` as it stands and writes under `bench/runs/_live/`, a folder git ignores.
   Add `--only teach` (or any list of scenario ids) to rerun just the part you are working on.
3. When you are happy with it, snapshot it: `uv run p3 snapshot c1-skills`.
4. Run the full bench on the snapshot: `uv run p3 bench --config c1-skills`.
5. Run the blind comparisons against the step before (the table in "Blind comparison" below says which), and reveal each one.
6. Paste the tables from `uv run p3 report --configs c0-baseline,c1-skills` into `EVAL.md`, and write what the step bought and what it cost.
7. Commit `configs/`, `bench/runs/` and `bench/compare/`.

A snapshot is frozen once it has runs.
`p3 snapshot` refuses to overwrite a name without `--force`, and overwriting one that has runs makes `p3 check` fail, because those runs no longer match their config; make a new name instead.

#### Step 1: four skills (`c1-skills`)

Write `tutor/.claude/skills/teach/SKILL.md`, `tutor/.claude/skills/tutor/SKILL.md`, `tutor/.claude/skills/quiz/SKILL.md` and `tutor/.claude/skills/grade/SKILL.md`, however you like.
The four names are fixed so the bench can start each job with `/<job>`; nothing else about them is.
A config without one of them routes that job to `/teach`, which is how `c0-baseline` does all four jobs with one skill.
Add any other skills you want, on any topic.
This step is still one agent: no subagents yet.

Two facts about how the bench starts a job help when you write these.
The skill receives the rest of the bench's request as its arguments, and the exact wording of every request is in `bench/scenarios.json`.
A tutor probe is one message, and the reply that gets scored is the final message of the session, so the `tutor` skill must answer in the chat and not in a file.

One thing to say when you claim what this step bought.
`c0-baseline` keeps the neutral `PREFERENCES.md` the template ships, and `c1-skills` is the first config with yours, so this step, and every comparison of `c0-baseline` against `final`, measures your skills and your preferences together.
Say so in `EVAL.md`, and say which differences you think came from which.

#### Step 2: review loops (`c2-review`)

Add review loops on teach, quiz and grade, with the reviewers as subagents; the tutor gets none.
A review here is about quality, not agreement, and a reviewer that votes "looks good" is worth nothing.
These are the dimensions I expect each job's reviews to cover:

| Job | What the review checks |
|---|---|
| **Quiz** | difficulty; coverage of the lesson's core; wording and the ways an item could be misunderstood; writing quality; alignment with the learning goal |
| **Grade** | whether the feedback is useful, explains enough, and is personalized the way this learner likes |
| **Teach** | separate reviews for technical correctness and fact-checking, for pedagogy, for alignment with the learning goal, and for overall quality |

Some advice that will save you time:

- **Give each reviewer a specific checklist.**
  "Review this" gets you a polite summary; "check that every distractor matches a named misconception and that no stem gives away its answer" gets you a finding.
- **Give each reviewer a fresh context.**
  A subagent starts with a context of its own and sees only what you hand it, so it reads the draft the way the learner will, without the writer's reasoning to lean on.
- **Cap the rounds.**
  Decide how many revise-and-review rounds a loop may run, and what ends it early.
  A loop with no cap is a loop that can spend your week, and in the bench it can also run into the scenario's time or turn limit ("The scenarios and the objective checks" lists them), which turns it into a recorded timeout.
- **Know what the quiz review checks coverage against.**
  In the bench, the quiz scenario's workspace has no lesson, so there coverage means the objective's text and what `MISSION.md` and `NOTES.md` say the learner needs.
  In your own sessions, review a quiz against the lesson in `lessons/` when there is one.
- **Record what happened.**
  Have each loop write a short record, for example `reviews/NNNN-quiz.md`: how many rounds ran, what each reviewer flagged, and what changed.
  The bench keeps every new file a scenario writes, so the record lands in the run's outputs, and you can then say whether the revisions moved anything.
- **Keep drafts out of the folders the bench reads.**
  The teach check expects exactly one new lesson in `lessons/`, so a draft saved there turns a good run into a recorded failure; put drafts in a folder of your own, such as `drafts/`.
- **Watch the permission denials.**
  In my own review-loop config, the teach session tried seven times to copy the finished draft into `lessons/` with a shell command, was denied each time, and then wrote the whole lesson out again, which costs output tokens and turns.
  `run.json` lists every scenario's denials; either allow the narrow command you need in `tutor/.claude/settings.json`, or tell the skill how to finish without it.

#### Step 3: split up the teach job (`c3-split`)

Split the teach job only, across subagents with jobs of your design: course planning, design, material writing, a visual and figure designer, a references finder, and so on.
Tutor, quiz and grade are not split.
Subagents are Markdown files in `tutor/.claude/agents/`, and `tutor/.claude/agents/README.md` explains what goes in one and which frontmatter fields matter.
You measure this step on teach, against `c2-review`.

#### `final`, the guard, and the ablation

`final` is what earned its place.
A step that did not pay for itself may be dropped, and saying so with the numbers behind it is a good result.

`final` also adds a guard: a PreToolUse hook that keeps the answer keys in `keys/` away from the main conversation while the grader can still read them.
It matters because every scenario's workspace holds a quiz's key, and a tutor that can read the key can hand out the answer.
In `c0-baseline` there is no guard, because a single agent has to read the keys to grade.
These are the facts the guard rests on, from the Claude Code documentation and my own checks of the version the bench runs:

- **Put the hook in `tutor/.claude/settings.json`.**
  Hooks in a subagent's frontmatter do not run in the bench's headless sessions, and the project's settings hooks do.
- **Tell the grader from the main conversation by the hook's input.**
  Inside a subagent the input carries `agent_type` (the subagent's name) and an `agent_id`; in the main conversation neither is there.
  A hook that exits with code 2 blocks the tool call, and the model sees what the hook wrote to stderr.
- **Only exit code 2 blocks.**
  A hook that fails in any other way, such as a script that is not found, a Python command that does not exist on the machine, or a script that raises an exception, lets the tool call through, so a broken guard looks exactly like no guard.
  Reference the script by a path that resolves from the workspace root, as the hooks documentation does with `$CLAUDE_PROJECT_DIR`, because the bench runs each scenario in a fresh folder.
  Then confirm once, with a `--config live` run and its trace, that the hook really runs in the bench: the grader's reads of `keys/` go through, and a read by the main conversation comes back with your hook's message.
- **Cover Read, Grep, Glob, Bash and PowerShell.**
  A guard on Read alone is a guard that `cat keys/0001.json` walks around.
  On Windows, Claude Code also has a PowerShell tool, on by default, so match `Bash|PowerShell` for shell commands, as the hooks documentation advises; my pilot's tutors reached for PowerShell on their own.
  The bench always gives your tutor Glob and Grep, but in your own sessions on macOS, Linux and WSL, Claude Code searches with `find` and `grep` through Bash instead, so Bash is not optional.
- **Do not use a permission deny rule for this.**
  A deny rule applies to subagents too, so it would block the grader, and a hook cannot lift a deny.

Which agents may read the keys is your decision: the grader, and perhaps a quiz reviewer.
The guard comes with its own tests, as in lecture 17's lab: a small unittest file, for example `tests/test_guard.py`, that runs your hook script with sample hook inputs on stdin and checks that it blocks what it should and allows what it should.

Then snapshot `final` and run it three times, and make at least one `final-minus-<x>` by removing one component and running it once.
Commit `tutor/` when you snapshot `final`, so you can remove a component, snapshot the ablation, and get back with `git restore tutor/`.

---

## The bench

The bench runs every config through the same scenarios from the same starting state, scores the outputs with fixed checks, and records what each scenario cost.

### The topics

**The shared development topic is agent architecture.**
It is a generic introduction, written for a fixed novice: an engineering junior who has used a chatbot and written some Python, but never built an agent, and wants to build an assistant for a senior design project.
I wrote it, so my knowledge is the ground truth, not the model's, and it is not a copy of this course's lectures.
It has five objectives (O1 the agent loop, O2 tools and tool calling, O3 context and memory, O4 workflows and agents, O5 multi-agent systems), the facts each one must get right, six misconceptions a novice holds, a starting workspace, true grades for two learner submissions, and six tutor probes.
The bench teaches O3, quizzes on O4, and grades two submissions of the six-item quiz `0001` on O1 and O2.
You tune your tutor on this topic and only this topic.

**You pick two test topics: one from another Mines course you have taken, and one life skill.**
You write each one yourself in `bench/own/<id>/`, in the same shape as the shared topic, and `bench/own/README.md` walks you through it, starting from `uv run p3 new-topic <id>`.
Commit a topic's items before its first run; the bench refuses to run a topic with uncommitted changes, and `p3 check --final` confirms from git history that every run used the items you committed.
When `final` is frozen, you run `c0-baseline` and `final` once each on both test topics.
They are the held-out check: does the architecture still pay off on statics or on cooking, where you never tuned it?
You also use `final` for at least three real learning sessions on one of the two, and write them up in `LEARNING-LOG.md`.

### The scenarios and the objective checks

Each scenario runs headless, `claude -p` in a fresh folder outside your repo that holds the config, the topic's starting workspace and `FORMATS.md`, so every config faces the same test and no tutor can reach `bench/`.

| Scenario | The request | Objective checks (fixed) |
|---|---|---|
| `teach` | `/teach` a 30-minute lesson on objective O3 for this learner | self-contained HTML; the declared minutes and objective; length against the request; links that resolve; key facts present and correct, misconceptions asserted, and fit to the learner's level (the judge) |
| `quiz` | `/quiz` a six-question quiz with its key on objective O4 | the JSON follows the contract; every item tagged with an existing objective; two independent solvers answer without the key, which flags likely wrong keys and likely ambiguous items |
| `grade-s1`, `grade-s2` | `/grade` one learner submission for quiz `0001`, with feedback for each answer | verdicts against the true grades; how often a right answer is marked wrong; the misconception named when one applies; feedback present |
| `tutor-p01` to `tutor-p06` | one probe message through `/tutor` | quiz answers not given away (the key's answers searched for in the reply); the expected behavior (the judge) |
| cost | - | tokens (input, output, cache), turns, subagents, web searches and fetches, minutes, and the list-price equivalent, per scenario |

A full run is these ten scenarios; `--quick` runs `teach`, `quiz`, `grade-s1`, `tutor-p01` and `tutor-p02`, once.

Each scenario has a time and a turn limit, set in `bench/scenarios.json` and the same at every lesson length: `teach` 45 minutes and 200 turns, `quiz` and each `grade` 15 minutes and 80 turns, and each tutor probe 10 minutes and 40 turns.
A scenario that reaches its limit is stopped and recorded as a timeout or an error, and that is a result about your tutor, so design review loops and pipelines to finish well inside these limits.

A few of the checks need saying plainly.
**The length check is a rough reading-time estimate:** the lesson's visible words divided by 150 words a minute, against the minutes requested, and a ratio from 0.6 to 1.5 counts as on length.
A lesson with a good interactive exercise and few words reads as short, so treat the ratio as a warning light and not a verdict.
**The judge** is a fixed prompt in `bench/judge/` and a pinned model (`claude-sonnet-5-5`), used only for what a script cannot check: whether the key facts are present and correct, whether a listed misconception is asserted, the fit to the learner's level, and whether a tutor reply did what the probe expected.
**The solvers** are `claude-sonnet-5-5` and `claude-haiku-5-5`.
When both agree with each other and not with your key, the key is probably wrong; when they disagree with each other, the item is probably ambiguous.
After lecture 24 you check the judge against ten labels of your own and report how often you agree, because a judge you have not checked is a number you cannot lean on.

The headline numbers that `p3 report` and the reveal use are `teach_facts_correct`, `teach_misconceptions`, `teach_length_ratio`, `teach_dead_links`, `quiz_key_agreement`, `quiz_wrong_key`, `quiz_ambiguous`, `grade_verdict_agreement`, `grade_false_wrong`, `grade_misconception_hit`, `tutor_leaks` and `tutor_behavior_met`, plus the cost: total tokens, output tokens, minutes, subagents and the list-price equivalent, per job and in total.
Each one, per run:

- `teach_facts_correct`: the share (0 to 1) of the teach objective's facts that the judge found in the lesson, present and correct.
- `teach_misconceptions`: how many of the topic's misconceptions the judge found the lesson asserting, a count.
- `teach_length_ratio`: the rough reading-time estimate over the minutes requested, where 0.6 to 1.5 counts as on length.
- `teach_dead_links`: how many of the lesson's links answered 404 or 410, a count, unknown with `--offline`.
- `quiz_key_agreement`: the share of the items that can be scored where the Sonnet solver's answer matches your key.
- `quiz_wrong_key`: how many items both solvers answered alike and differently from your key, the likely wrong keys.
- `quiz_ambiguous`: how many items the two solvers answered differently, the likely ambiguous items.
- `grade_verdict_agreement`: the share of graded answers whose verdict matches the true grade.
- `grade_false_wrong`: of the answers whose true verdict is correct, the share graded partial or wrong.
- `grade_misconception_hit`: of the answers with a true misconception, the share where the grade names the same one.
- `tutor_leaks`: how many replies gave away the answer to the quiz item a probe asks about, counted over the probes that got a reply.
- `tutor_behavior_met`: the share of probes whose reply did what the probe expected, in the judge's view.

A job that failed counts against the config: a missing lesson scores 0 facts, a missing quiz or key 0 key agreement, a missing grades file disagrees on every answer, and a probe with no reply is not met.

### What a run leaves behind

A run of config `c1-skills` writes `bench/runs/c1-skills/<run-id>/`, where the run id is the time, the topic, the minutes and the repeat, such as `20261105-141502-agent-architecture-m30-r1`.

| File | What it holds |
|---|---|
| `run.json` | the config and its hash, the topic and its hash and commit, the Claude Code version, the model, and per scenario its status, duration, turns, tokens, subagents, web use and permission denials |
| `score.json` | every check's result, the headline numbers, and what the scoring itself cost |
| `<scenario>/outputs/` | every file the scenario wrote or changed, at its own path: open `teach/outputs/lessons/` in a browser to read the lesson |
| `<scenario>/result.json` | the final result line, including the tutor's reply |
| `<scenario>/trace.jsonl.gz` | the whole stream of the session, gzipped, including every subagent's messages |
| `<scenario>/stderr.txt` | anything Claude Code printed to stderr, when there was something |

Commit your runs.
They are the evidence, and `p3 check` confirms each one points at a config whose hash still matches.

### Blind comparison

`p3 compare` puts two configs' outputs for the same task side by side, without telling you which is which, and records your pick.

**Why blind.**
You built the later configs, you know which one has the review loops, and you expect it to win.
That expectation leaks into what you see, which is why medical trials hide which pill is which.
Hiding the labels leaves you with the outputs alone.

**How it works.**

1. Both configs need scored full runs on the topic at the same lesson length, the topic's 30 minutes unless you add `--minutes M`; the comparison refuses with a clear message when one has none.
   Quick runs are left out, and `--quick` pairs them instead, which is for trying the tool out: `p3 check` does not count a session of quick runs.
   Runs made with `--only` are left out too, so a run of one scenario never takes a full run's place; `--teach-only` pairs the length study's teach-only runs instead.
2. Run it yourself, in your own terminal, because the picks must be yours: `uv run p3 compare c0-baseline c1-skills --job tutor`.
   It pairs the two configs' runs by repeat order, oldest first, and for each pair it decides at random which config goes on the left, from a secret seed it keeps in a key file.
3. A local page opens in your browser, one pair at a time, labelled only "Left" and "Right", with "Pair k of n".
   Lessons show side by side in frames, and quizzes, grades and tutor replies as readable text.
4. For each pair you answer three questions: which fits you better (left, right or tie), why in one sentence (required), and whether you could tell which configuration made which (yes or no).
5. Each answer is saved as you submit it, so closing the browser loses nothing; `uv run p3 compare --resume <session-id>` picks up where you stopped, and `uv run p3 compare --list` shows your sessions.
6. When every pair is done, run `uv run p3 compare --reveal <session-id>`.
7. Commit both files it wrote, `bench/compare/<session-id>.json` and `bench/compare/<session-id>.key.json`.
   Do not open the key file before you reveal; the page never reads it, and neither should you.

If a browser is awkward, `--terminal` writes each pair as one side-by-side HTML file, prints its path, and asks the three questions in the terminal.
Comparing costs time and no tokens, because the pairs come from runs you already have.

**What a pair is, and how many you get.**
A teach pair is the two lessons from one pair of runs, and a quiz pair is the two quizzes with their keys.
A grade pair is one learner answer with each version's verdict and feedback, so one pair of runs gives 12 of them (six items in each of two submissions).
A tutor pair is the two replies to one probe, so one pair of runs gives six.
These are the comparisons `p3 check --final` looks for:

| Comparison | Topic | Jobs | Pairs |
|---|---|---|---|
| `c0-baseline` against `c1-skills` | shared | teach, quiz, grade, tutor | 1, 1, 12, 6 |
| `c1-skills` against `c2-review` | shared | teach, quiz, grade | 1, 1, 12 |
| `c2-review` against `c3-split` | shared | teach | 1 |
| `c0-baseline` against `final` | shared | teach, quiz, grade, tutor | 3, 3, 36, 18 |
| `c0-baseline` against `final` | each test topic | teach, grade, tutor | 1, one per graded answer, one per probe |

A lesson takes about five minutes to skim and judge, a quiz a few minutes, and a grade or tutor pair under a minute, so plan on two to three hours of comparing across the project, spread over the three weeks.

**Reading the tally.**
Ties are set aside, and the question is whether one config won more of the rest than chance would give it.
If two versions were equally good, your picks would be coin flips.
With 10 picks, a version that is no better still wins 8 or more about 5% of the time by luck alone, so 8 of 10 is suggestive; it wins 9 or more about 1% of the time, so 9 of 10 is strong; and 6 of 10 says nothing at all.
The reveal prints the exact two-sided sign-test p-value, which counts either config winning that often, so it shows about 0.11 for 8 of 10 and about 0.02 for 9 of 10.
With one or three teach or quiz pairs, no tally can reach those numbers (even 3 of 3 has a p-value of 0.25), so for those two jobs your reasons and the objective checks carry the weight; lecture 23 adds the intervals.

**The limits.**

- **Blinding fails when the versions look obviously different.**
  A split pipeline's lessons may have a look you recognize at once, which is why every pick asks whether you could tell, and why the reveal reports how often you could.
- **Preference is not learning.**
  A lesson you enjoy is not always one you learn more from, which is why the objective checks sit beside the picks.
- **On the shared topic you are not the novice.**
  Judge each pair by whether it would have fit you as a learner when you were new to agents.
- **The results are one person's taste, and that is the point.**
  They are yours, made with your `PREFERENCES.md`, and they are not averaged across the class.
- **Pairs from one run are not independent.**
  The 12 grade pairs from one pair of runs come from the same four grading sessions, two for each config, so they say less than 12 separate runs would.

**The reveal shows quality first, then cost.**
It prints, in this order: the tally (wins for each config, and ties), the sign-test p-value with a line on reading it, the share of pairs where you could tell, your reasons grouped by the config that won, then the objective checks for the job as means over the session's runs, and only then a cost table for the job: mean tokens, output tokens, minutes and subagents per scenario for each config.
The order is deliberate.
You decide what the quality difference is before you know its price, and then you decide whether it was worth it.

---

## Start here

Every command below runs from the root of your own P3 repo, `work/p3-tutor` once you have cloned it, and every `p3` command starts with `uv run`.
Say "In work/p3-tutor, run ..." to Claude Code, or run it yourself in a terminal in that folder.
If you do not have `uv`, every command also works as `python -m p3 ...` (on macOS and Linux, `python3 -m p3 ...`), because `p3` uses only Python's standard library, from Python 3.11 on.

1. Click **Use this template** at the top of this repo, then **Create a new repository**.
2. **Name it `p3-tutor`** and make it **Public**.
3. Clone it into `work/`, your own space in the course repo: say **"clone my P3 repo into work/p3-tutor"** to Claude Code, or in a terminal at the root of the course repo run `gh repo clone <your-github-username>/p3-tutor work/p3-tutor`.
   Git ignores `work/`, so this repo never collides with a course update.
   At the start of every Claude Code session you use for P3, ask it to read `work/p3-tutor/CLAUDE.md`, a short orientation for the agent on how this repo works and what not to edit.
4. Check that `uv --version` prints a version number; you installed `uv` for lecture 12.
5. Open `p3.json` and set `section` to your course, `"498E"` or `"598E"`.
   Leave `stretch` as `null` until you choose one.
6. Run `uv run p3 check`.
   On a fresh copy it prints a checklist and exits cleanly: the items you have not done yet are listed as work to do, which is not an error, and only a failure means something is broken.
7. Commit and push, open the **Actions** tab of your repo, and wait for the `p3-check` run to go green.
   CI never calls a model; it checks the files you committed.
8. Run the baseline once, quickly: `uv run p3 bench --config c0-baseline --quick`.
   This is the first command that draws on your Claude plan: five scenarios and their scoring.
   It prints a summary table when it finishes, and writes `bench/runs/c0-baseline/<run-id>/`.
9. Open the lesson it wrote, under `teach/outputs/lessons/` in that run folder, in your browser, and read `result.json` in the two tutor scenarios.
   Then read `KNOWN-GAPS.md`.
   The gaps there are starting points I saw, not a checklist.
10. When that works, start the baseline's three full runs in your own terminal: `uv run p3 bench --config c0-baseline --repeats 3`.
    That is 30 sessions plus their scoring, about 20 to 25 minutes for the baseline in my pilot, so start it when you can leave it running.

Please do all of this on the first day.
Setup is the step with the most ways to go wrong, and you want it behind you while there is plenty of time.

A full bench run takes much longer than a quick one: the lesson alone is allowed up to 45 minutes.
So run full runs yourself in a terminal, or ask Claude Code to run them in the background, because Claude Code stops a foreground command after ten minutes at most.

**When you learn with the tutor**, open a terminal in `work/p3-tutor/tutor` and start `claude` there.
The tutor's learner files (`MISSION.md`, `NOTES.md`, `lessons/` and the rest) are created in `tutor/` as you go.
Claude Code also reads the `CLAUDE.md` of every folder above the one it starts in, so a session in `tutor/` sees the repo's root `CLAUDE.md` and, inside the course repo, the course's own.
The bench avoids that, because it runs each scenario in a fresh folder outside your repo, in your system's temporary folder.
On Windows that folder is inside your home folder, so a `CLAUDE.md` in your home folder itself would reach every scenario; `p3 bench` warns when it finds one above the temporary folder and records it in `run.json`, and you should move it before you make runs you will commit.
If a real session ever acts more like a course assistant than your tutor, that is why, and you can learn from a copy of `tutor/` outside the course repo instead.

### A pace that works

There are no checkpoints, and nothing is checked on these dates.
This is the pace I would keep.

- **Week 1, Nov 3 to 9:** set up, run `c0-baseline` (its three full runs), read `KNOWN-GAPS.md`, write `PREFERENCES.md` and the four skills, and snapshot `c1-skills`.
  The P4 proposal (Fri Nov 6) competes with this week, so I kept it light.
- **Week 2, Nov 10 to 16:** the review loops (`c2-review`) and the teach split (`c3-split`), with blind comparisons at each step; write the test topics' items and commit them.
- **Week 3, Nov 17 to 24:** `final` with the guard, its repeats (after lecture 23 on Nov 17), the judge check (after lecture 24 on Nov 19), the ablation, the test topics, the real learning sessions, the write-up and the video.

I estimate about 15 hours in all.
The deadline is two days before Thanksgiving, so plan to be done before the holiday traffic starts.

---

## Commands

Run each one as `uv run p3 ...`, or as `python -m p3 ...` without `uv`.

| Command | What it does |
|---|---|
| `p3 check [--final]` | prints a checklist of the repo's state and fails when something is broken (a changed fixed file, a snapshot whose files no longer match its hash, a run whose config changed, a topic that does not validate); with `--final` it also fails on anything not yet done |
| `p3 snapshot <name> [--force]` | copies the live config from `tutor/` into `configs/<name>/` with its hash, and refuses to overwrite a name without `--force` |
| `p3 bench --config <name>` | runs the scenarios on a snapshot, scores them and prints a summary table; `--config live` runs `tutor/` as it stands, into the ignored `bench/runs/_live/` |
| `p3 score <run-dir>` | scores a run, or scores it again; `--offline` skips the link checks, and `--no-model` skips every check that calls a model |
| `p3 report [--topic t] [--configs a,b,...]` | prints Markdown tables for `EVAL.md`: one row per config with each headline number as the mean and range over its scored full runs (runs made with `--only` are left out), with the run count, and a cost table per job; `--minutes M` keeps one lesson length, `--quick` shows the quick runs instead, and `--teach-only` the length study's teach-only runs |
| `p3 compare <config-a> <config-b> --job <job>` | starts a blind comparison of two configs on `teach`, `quiz`, `grade` or `tutor`, and takes `--topic t`, `--minutes M`, `--quick`, `--teach-only` (with `--job teach`), `--terminal` and `--port P` |
| `p3 compare --resume <session-id>` | continues a comparison you closed |
| `p3 compare --reveal <session-id>` | shows the result of a finished comparison, quality first and then cost |
| `p3 compare --list` | lists your comparison sessions |
| `p3 new-topic <id>` | writes a skeleton test topic in `bench/own/<id>/` |

The options of `p3 bench`:

| Option | What it does |
|---|---|
| `--topic <id>` | the topic, `agent-architecture` by default; an id is looked up in `bench/topics/` and then in `bench/own/` |
| `--repeats N` | run the whole set N times, one after another |
| `--quick` | run `teach`, `quiz`, `grade-s1` and the first two tutor probes, once |
| `--minutes M` | the lesson length to request, the topic's by default, which is 30 on the shared topic (the length study uses 10, 30 and 60) |
| `--only <ids>` | run only these scenarios, as a comma-separated list such as `teach,tutor-p03`; such a run is not a full run, so `p3 report`, `p3 compare` and `p3 check` leave it out, except that `--only teach` runs are the length study's and `--teach-only` shows them |
| `--jobs N` | run up to N scenarios of a repeat at the same time, which saves time but not tokens |
| `--keep` | keep each scenario's working folder, to look inside it afterwards; a later `p3 bench` deletes kept folders more than a day old |
| `--no-score` | skip scoring; score later with `p3 score <run-dir>` |
| `--offline` | skip the link checks when scoring |

---

## What the runs cost

Everything that runs `claude` draws on your own Claude plan: the scenarios, and the scoring calls after them (the judge, and the two solvers).
Comparing costs nothing, and neither does `p3 check`, `p3 report` or `p3 snapshot`.

Every `claude -p` call carries a fixed load before it does any work: in my checks, 24,000 to 49,000 input tokens, almost all of them cached reads of Claude Code's own instructions and tools.
Every subagent pays a share of that again, plus whatever it reads, which is why fan-out is what drains a weekly limit.
A split teach pipeline with three reviewers is the most expensive thing in this course so far, and the repeats are limited to `c0-baseline` and `final` for that reason.
The dollar figure in `run.json` and in the reports is the list-price equivalent that Claude Code reports, not what you pay on a subscription; on your plan, the cost is your usage limit.

The runs the project needs:

| What | Runs |
|---|---|
| The ladder, on the shared topic | `c0-baseline` 3, `c1-skills` 1, `c2-review` 1, `c3-split` 1, `final` 3, each `final-minus-<x>` 1: at least 10 full runs |
| The test topics | `c0-baseline` and `final`, once each on both topics: 4 full runs |
| The length study (598E, or the stretch) | 18 teach-only runs |

Plus the quick runs you make while you iterate.

These are my pilot's numbers, with Claude Code 2.1.314 and Sonnet: the baseline averaged over three full runs, and one full run of a review-loop config of my own (four skills, with reviewers on teach, quiz and grade, at most two rounds each).

| Scenario | `c0-baseline` | minutes | review loops | minutes |
|---|---|---:|---|---:|
| `teach` | 744k tokens (28k output) | 2.8 | 4.96M tokens (109k output), 5 subagents | 9.8 |
| `quiz` | 161k tokens (5k output) | 0.6 | 747k tokens (30k output), 2 subagents | 3.6 |
| each `grade` | 160k tokens (3k output) | 0.45 | 311k tokens (9k output), 1 subagent | 1.05 |
| each tutor probe | about 105k tokens (1.5k output) | 0.25 | about the same, no review loop | 0.25 |
| **full run** | **1.85M tokens (49k output), $1.75** | **5.8** | **6.99M tokens (167k output), $4.48** | **17.1** |
| scoring a full run | about 57k tokens, $0.19 | under 1 | the same | under 1 |

The minutes are summed over a run's scenarios, which is about how long a run takes with the default `--jobs 1`.
A quick run of the baseline was 1.1M tokens and about 4 minutes.
Most of these tokens are cached reads of Claude Code's own instructions and tools, which cost far less than new input or output, so the list-price column grows more slowly than the token column.
The review loops made the teach scenario about 6.7 times as expensive in tokens and 3.5 times as slow, and a split teach pipeline adds more on top; if your `final` costs about what my review-loop config did, its three runs are about 21 million tokens.

Some habits that keep the cost down:

- Iterate on `--config live --quick`, and on `--only` with the one scenario you are changing.
- Make full runs only of snapshots you mean to keep.
- Spread the full runs over several days, and check `/usage` in Claude Code before a big one.
- Try a review loop or a split pipeline on one quick teach scenario before you run it in full.

---

## Ground rules

- **Using Claude Code is the point**, not something to disclose or apologize for.
  This is a course about driving agents well.
- **Your repo is public, and so is its history.**
  Do not commit API keys, passwords, or private information about anyone.
  Your learning sessions leave files in `tutor/` too, such as `MISSION.md` and `NOTES.md`, so keep personal details out of them.
  You never need an API key in this project, because the bench uses your Claude Code sign-in.
- **What to edit and what not to.**
  `tutor/`, `bench/own/`, `p3.json` and your own writing are yours, and `configs/`, `bench/runs/` and `bench/compare/` are yours through the `p3` commands that write them.
  Do not edit `bench/` outside `bench/own/`, or `p3/`: they are hash-checked, and `p3 check` fails in CI when they change.
  Do not edit `tutor/FORMATS.md` either; it must stay identical to `bench/FORMATS.md`.
  If you think one of those files has a bug, tell me, and I will fix it for everyone.
- **No special-casing of bench items.**
  The bench is public, and a config that recognizes a bench item by its text and treats it specially gets no credit on that topic.
  `p3 check` warns when a config file holds 40 or more characters copied from the shared topic, and the grading pass searches configs for bench strings.
  Your test topics are the held-out check, which is why you tune on the shared topic only.
- **The measurements come from the commands.**
  Runs, scores and comparison records are written by `p3`; do not edit them by hand, and do not delete a run because you did not like its numbers.
  There are two exceptions.
  A run that failed for a reason outside your tutor, such as a usage limit or a sign-in problem, measures nothing; `p3 bench` sets such a repeat aside by itself, and "When it breaks" says what to do with anything it missed.
  And a test topic with a real mistake in it is fixed by the procedure in `bench/own/README.md`, which deletes that topic's earlier runs and the comparisons made from them.
- **The judgment is yours.**
  Make every blind pick yourself; an agent must never make them for you, because your picks are the measurement.
  The same goes for your test topics' true grades, your judge-check labels, `LEARNING-LOG.md`, `DECISIONS.md` and the prose in `EVAL.md`.
- **On the life-skill topic, no individualized financial, medical or legal advice.**
  Your tutor may teach the general knowledge of a topic like budgeting or first aid, and it must not tell a learner what to do with their own money, health or legal situation.
  Write a probe that tests exactly that.
- **On the topic from another Mines course, write the items in your own words.**
  Do not copy that course's slides, homework or solutions into a public repo.
- **Build skills you would reuse.**
  P3 skills are designed to be reusable in P4, so write them to work outside the bench, not only inside it.

---

## How the 150 points are planned

This is how I plan to grade.
Canvas is the record, and if I change this table before the deadline I will announce it there.

| Part | Points |
|---|---|
| The tutor runs; `p3 check` passes in CI; every config snapshotted; runs committed | 10 |
| `c1-skills`: the four skills, measured against `c0-baseline` | 20 |
| `c2-review`: review loops on teach, quiz and grade, measured | 20 |
| `c3-split`: the teach job split across subagents, measured | 20 |
| `final`: repeats against `c0-baseline`, the ablation, and the guard hook with its tests | 15 |
| Test topics: items written first, both runs, blind comparisons, three real sessions on one | 20 |
| `EVAL.md` analysis (the trade-offs, the judge check, the change that did not pay), `DECISIONS.md` and `LEARNING-LOG.md` | 20 |
| One stretch (498E: any one; 598E: the rider, required) | 25 |

"Measured" means the blind comparisons, the objective checks and the cost, written up in `EVAL.md` with what they let you claim.
A step that did not pay for itself earns its points when you measured it and said so.

I would rather say this now than have you find out later: the core work is 125 of 150 points, so with the video, complete core work without a stretch is 175 of 200.
That is 87.5%, so here an A needs a stretch.
The stretch is worth doing properly and not worth doing in the last hour.

---

## One stretch

The stretch is 25 of the 150 points.
For 498E it is one of the five options below, your choice.
For 598E it is the rider, which is required, and you do not do the other options: doing one as well adds no points, because the project is capped at 150.

Set `stretch` in `p3.json` to the option's id, so I know which one you did (for the length study it also switches on that study's checks in `p3 check --final`), and write it up in the last section of `EVAL.md`.
For 598E, set `section` to `"598E"` and `stretch` to `"length-study"`.
Pick your option early and try a small piece of it first, because most of them draw on your Claude plan.

| Id | Option |
|---|---|
| `length-study` | 1. The length study |
| `personalization-swap` | 2. Personalization swap |
| `cheaper-tutor` | 3. A cheaper tutor |
| `mcp-server` | 4. An MCP server the tutor uses |
| `agent-sdk-grader` | 5. The grader ported to the Agent SDK |

1. **The length study** (the 598E rider, below).
   In 498E, set `stretch` to `length-study`, and `p3 check --final` checks its runs and `PREREG.md` exactly as it does for 598E.
2. **Personalization swap:** two learner profiles on the same topic; show that lesson, quiz and feedback change as intended and stay correct.
   Write a second `PREFERENCES.md` for a learner unlike you, snapshot `final` with it under a second name, run both, and show both halves: the changes match the profile, and the objective checks hold.
3. **A cheaper tutor:** the same quality, by blind comparison and objective checks, with Haiku subagents or fewer calls.
   A subagent can name its own model in its frontmatter.
   Run the cheaper config as many times as `final`, so both sides of the comparison have repeats.
4. **An MCP server the tutor uses** (a review scheduler, a progress store), measured (lecture 16).
   Ask me before you start this one, so we agree on how the bench's scenarios start your server.
5. **The grader ported to the Agent SDK** (lecture 21) and measured against the Claude Code version.
   Keep the SDK code outside `p3/` and `bench/`, for example in `sdk/`, have it write grades in the `FORMATS.md` format, and compare it with your Claude Code grader on the same submissions, in quality and in cost.

---

## The 598E rider: the length study

Does splitting up the teach job matter more as lessons get longer, and does quality fall faster with length for a single agent than for the split pipeline?

| | 10 minutes | 30 minutes | 60 minutes |
|---|---|---|---|
| `c1-skills` | 3 runs | 3 runs | 3 runs |
| `final` | 3 runs | 3 runs | 3 runs |

Eighteen teach runs on the shared topic, teach only, with `p3 bench --minutes`, for example `uv run p3 bench --config c1-skills --only teach --minutes 60 --repeats 3`.
Set `section` to `"598E"` in `p3.json`, which makes `p3 check --final` look for these runs and for `PREREG.md`.

1. **`PREREG.md` before the runs**, as in P2: which config loses more as length grows, and the smallest difference that matters.
   Commit it before the first of the eighteen runs; git history proves the order, and `p3 check --final` reads it.
2. **Comparisons within a length, never across:** blind `c1-skills` against `final` at each length, and whether `final`'s win rate grows with length.
   `uv run p3 compare c1-skills final --job teach --teach-only --minutes 10` pairs only the 10-minute teach-only runs, three pairs; run it again with `--minutes 30` and `--minutes 60`.
   `--teach-only` keeps the ladder's full runs out of the 30-minute session, so every length gets exactly the study's three pairs.
   Never compare a 10-minute lesson with a 60-minute one, because judges also favor longer outputs (lecture 24).
3. **Length accuracy:** actual against requested length, because a "60-minute" lesson that is really 35 confounds the comparison.
   `uv run p3 report --configs c1-skills,final --teach-only` gives every cell's numbers.
4. **Cost against length:** tokens per minute of lesson for each config, and whether the pipeline's overhead grows in step with length or faster.
5. **Threats to validity** (lecture 22): blinding failures, judge bias, and three runs per cell.

I estimate 4 to 6 extra hours.
The risk is tokens: six 60-minute lessons go through your multi-agent pipeline, so run the 60-minute cells over several days, and try one before you commit to the rest.
The time limit does not grow with the lesson: a teach scenario has 45 minutes at every length, so try one 60-minute run of `final` first and see whether its pipeline finishes in time.

---

## The video

The video is worth 50 points, and it goes in the same Canvas discussion post as your repo URL.
Record 5 to 10 minutes, with any tool and any quality; a phone or a screen recording with your voice over it is fine.
Cover three things, in whatever order feels natural:

1. **The project.**
   What you built and what you found: show your tutor's architecture, one reveal from a blind comparison and one cost table, and say what they do and do not let you claim.
2. **Your observations.**
   Which machinery paid for itself and which did not, what surprised you, and what your real learning sessions taught you that the bench could not.
3. **The challenges and how you solved them.**
   A real one, in your words.
   Where you overruled the agent is a good story to tell here.

I am asking for this because the skills, the subagents and the runs can come from an agent and the video cannot.
It is your voice, your reasons and your story, and I care about the story and not about production quality.

---

## The deadline

Everything is due **Tuesday, November 24, at 11:59 pm**.
There are no checkpoints, because I would rather you finish the whole thing by the deadline than turn something in halfway.
On Canvas you make one post in the Project 3 discussion, with the URL of your repo and your video.
Run `uv run p3 check --final` and push your last commit before you post.

Late work loses 20%, and nothing is accepted more than a week late.
Canvas is the system of record for the deadline.
If Canvas and this file ever disagree, Canvas wins, and please tell me so I can fix it.

---

## When it breaks

- **`claude` is not found.**
  `p3` looks for Claude Code in the environment variable `P3_CLAUDE` first, and then for `claude` on your PATH, and its message names `P3_CLAUDE` when it finds neither.
  Check that `claude --version` works in the same terminal.
  If it does not, point `P3_CLAUDE` at the program: in Git Bash, `export P3_CLAUDE="C:/Users/<you>/.local/bin/claude.exe"`; in PowerShell, `$env:P3_CLAUDE = "C:\Users\<you>\.local\bin\claude.exe"`; on macOS or Linux, `export P3_CLAUDE="$HOME/.local/bin/claude"`, each with the path where your `claude` really is.
  A path with spaces in it works as it is, with or without quotes around the whole path.
- **`claude -p` fails or asks you to sign in.**
  Open `claude` once in a terminal and sign in, then run the command again.
  The bench stops at the first scenario that fails this way, as it does at a usage limit (next item).
- **You see "removed ANTHROPIC_API_KEY so the bench uses your Claude subscription".**
  That is `p3` protecting you.
  In headless mode an API key in your shell silently replaces your subscription login, and after lecture 20 many of you have one set, so `p3` removes `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from every `claude` it starts, and says so.
  It also removes Claude Code's own session variables, so running the bench from inside a Claude Code session is fine.
- **A run hits your usage limit.**
  `p3 bench` stops at the first scenario that reports a usage limit, a sign-in problem or an API outage, stops every scenario still running, and starts no new one.
  That repeat says nothing about your tutor, so it is not saved as a run: its files go to `bench/runs/_live/_aborted/`, which git ignores, the repeats after it do not run, and the repeats before it are kept.
  If the limit comes while a run is being scored, the run keeps its `run.json` with no `score.json`, and `p3 report`, `p3 compare` and `p3 check` ignore it until you score it with `uv run p3 score <run-dir>`.
  Wait for the reset (`/usage` shows when), and run the bench again.
  In the meantime, do the work that needs no Claude: your test topics, blind comparisons of runs you have, and the write-up.
  If you ever find a committed run whose `result.json` files say Claude was not working, delete that run, because it measures nothing.
  A scenario that failed for any other reason, such as a timeout or a lesson that was never written, is a result: keep it and report it.
- **A scenario keeps hitting permission denials.**
  `run.json` lists them per scenario.
  The bench passes your config's `permissions.allow` list from `tutor/.claude/settings.json` to Claude Code, and in a fresh folder that list is the only thing that allows a tool, so add the tool there and try it with `--config live` before you snapshot.
  The bench always adds `Glob` and `Grep` to that list, because on macOS, Linux and WSL Claude Code leaves them out unless they are named, and every config should be able to search its workspace the same way on every system.
- **A scenario times out or writes nothing.**
  Read its trace (`trace.jsonl.gz` opens with any gzip tool, and Claude Code can read it for you), and rerun just that scenario with `--config live --only <id> --keep` to look inside its working folder afterwards.
- **`p3 bench` refuses your test topic.**
  It runs a test topic only when every file in it is committed and unchanged; commit it, then run again.
  When git itself cannot be used here, the message says why instead, such as git missing from your PATH, a repository git does not trust (its message names the `git config --global --add safe.directory` fix), or a folder that is not its own clone.
- **The scorer warns that no link could be checked.**
  This Python cannot verify web certificates, which happens with the python.org installer on macOS until its `Install Certificates.command` has run (in the Python folder in Applications).
  Run it, then score the run again with `uv run p3 score <run-dir>`; until then the run's dead links are unknown, not zero.
- **`p3 compare` refuses.**
  Both configs need scored full runs on that topic at the same lesson length, and the message says which one is missing.
  If you ran with `--no-score`, run `uv run p3 score <run-dir>` first; for runs at another length, add `--minutes M`.
- **`p3 check` fails.**
  Read the failing lines; each one names the file.
  The usual causes are an edit under `bench/` outside `bench/own/` or under `p3/` (restore it with `git restore`), a changed `tutor/FORMATS.md`, a snapshot edited by hand or overwritten after it had runs, a run that was stopped midway (its folder has no `run.json`; delete it), and a test topic changed after its runs (see "Commit before the first run" in `bench/own/README.md`).
  A file saved in a Windows "ANSI" encoding instead of UTF-8 can also make a snapshot or a test topic stop matching its hash; `p3 check` and `p3 snapshot` name such files.
- **Windows.**
  The template is written to run on Windows, macOS and Linux, and its own tests run on all three, but Windows is the setup I have tested least.
  Use Git Bash for the commands, as in P2; PowerShell works for `p3` too.
  Git stores this repo's text files with LF line endings, and every hash `p3` computes ignores the difference, so a checkout with Windows line endings does not break the check.
  Your guard hook runs on your machine, so register it with the Python command that works in your own terminal (`python` on Windows, `python3` on macOS and Linux), and use forward slashes in its paths.
  If something fails, send me the exact output.

Still stuck after 20 minutes?
Come to office hours: Tue and Thu, 9 to 10 am and 2 to 3 pm, CTLM 246L.
Bring the exact error message, because the words on the screen usually save us half the debugging time.

And if anything in this brief is unclear or seems wrong, tell me.
That is a bug too, and I would rather fix it than have you guess.

---

## Credits

The baseline `teach` skill in `tutor/.claude/skills/teach/` is a fork of the `teach` skill in [mattpocock/skills](https://github.com/mattpocock/skills) (`productivity/teach`), by Matt Pocock, under the MIT license.
I kept its workspace model and its pedagogy and changed it to do all four jobs in one pass; `THIRD-PARTY.md` holds the license notice.
Thank you to its author for publishing it.
