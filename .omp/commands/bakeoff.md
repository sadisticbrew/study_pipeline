---
description: Blind writer bake-off. Four models write the same excerpt, and you pick the best by reading. Use "pick <label>" to reveal the models and set the writer.
argument-hint: "[chapter number] | pick <A-D>"
---

Writer bake-off. Arguments: `$ARGUMENTS`. Work from the repo root. The topic is in
`topics/.current`.

The candidates, as agent names:

| Agent | Model selector for `.omp/config.yml` |
|---|---|
| `sp-writer-glm52` | `opencode-go/glm-5.2:low` |
| `sp-writer-muse` | `opencode-go/muse-spark-1.3-contributor:xhigh` |
| `sp-writer-kimi` | `opencode-go/kimi-k2.7-code:low` |
| `sp-writer-dsv4pro` | `opencode-go/deepseek-v4-pro:low` |

## If the arguments start with `pick`

1. Find the newest directory in `bakeoff/` and read its `key.json` and `scorecard.md`.
2. Show the scorecard again with the model names revealed.
3. In `.omp/config.yml`, set `modelRoles.sp_writer` to the picked model's selector. The
   checker must come from a different model family than the writer. If the writer is now
   DeepSeek, set `modelRoles.sp_checker` to `opencode-go/glm-5.2:high`. Otherwise set it
   to `opencode-go/deepseek-v4-pro:high`. Edit only those two lines. Do not use Muse Spark
   as the checker, because at xhigh it took about 39 minutes on a single chapter.
4. Tell the learner that if they hand-edit the winning excerpt until it sounds exactly
   right and save it as `style/exemplar.md`, every future writer will treat it as the gold
   standard for voice. Then stop.

## Otherwise: run a bake-off

### 1. Prepare a shared brief and facts

Use the given chapter, or the next pending one from `python3 tools/state.py next`. Let `CD`
be its directory from `python3 tools/state.py chapter-dir <slug> <n>`. If `CD/brief.md` or
`CD/facts.jsonl` does not exist, carry out steps 0 to 2 of `.omp/commands/chapter.md`, the
brief, the scouts, and the labs, but leave the chapter's status unchanged.

Create `bakeoff/<YYYY-MM-DD>-<slug>-ch<NN>/`, called `RUN` below, and write `RUN/brief.md`.
It is a copy of the chapter brief cut down to an excerpt: the opening, the crux, and the one
section with the most real mechanism in it, with a combined budget of about 1500 words. Add
a note that this is an excerpt. It should still have front matter and the format skeleton,
including a `## Check yourself` with three questions, so that the lint applies unchanged.

### 2. Assign blind labels

Shuffle the four agents onto the labels A to D with a real random draw, for example
`python3 -c "import random; a=['sp-writer-glm52','sp-writer-muse','sp-writer-kimi','sp-writer-dsv4pro']; random.shuffle(a); print(a)"`.
Write the mapping to `RUN/key.json`. Do not mention which model has which label anywhere in
the conversation until `pick`.

### 3. Write, in parallel

Spawn all four writers in one batch. Each gets `OUTPUT=RUN/<label>.md`, `BRIEF=RUN/brief.md`,
`CHAPTER_DIR=CD`, `FACTS=CD/facts.jsonl`, `SOURCES=topics/<slug>/sources.jsonl`,
`TOPIC_DIR=topics/<slug>`, and
`LINT=python3 tools/lint.py RUN/<label>.md --facts CD/facts.jsonl --topic-dir topics/<slug> --base-dir CD --words 1200,1800`.
Record each writer's wall-clock duration from the task results.

### 4. Measure, in parallel

For each label:

- run the lint command with `--json`, and record the error and warning counts and the word
  count
- run `python3 tools/render.py RUN/<label>.md --facts CD/facts.jsonl --sources topics/<slug>/sources.jsonl --base-dir CD`
- spawn an `sp-checker` with `MODE=report-only`, `CHAPTER=RUN/<label>.md`,
  `REPORT=RUN/<label>.check.md`, and the same `CHAPTER_DIR`, `FACTS`, `SOURCES` and
  `TOPIC_DIR`. Spawn all four checkers in one batch.

### 5. Scorecard

Write `RUN/scorecard.md` without model names. Give one row per label with: duration, words,
lint errors and warnings, the checker's counts for contradicted, stretched and unsupported
claims, and the number of `[@unverified]` markers. Below the table, list the paths to each
excerpt's PDFs.

Note in the scorecard that the checker shares a model family with one of the candidates,
so that row's checker counts may be a little generous.

Tell the learner to read the four excerpts, judging the voice above all, then run
`/bakeoff pick <label>`. Do not recommend a label.
