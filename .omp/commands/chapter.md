---
description: Generate the next (or the given) chapter of the current topic as Markdown and PDF.
argument-hint: "[chapter number] [topic slug]"
---

Generate a study chapter. Arguments: `$ARGUMENTS`. Both are optional. With no chapter number,
use the next pending chapter. With no topic, use the current one in `topics/.current`.

You are the orchestrator. You write the brief, the summary, and nothing else. Specialist
agents do the research, labs, writing, and checking. Work from the repo root. Track the time
taken by each step, because the final report includes it.

## 0. Resolve

- If no topic is given, read `topics/.current`.
- If no chapter number is given, run `python3 tools/state.py next <slug>`.
- If the chapter's status is `done`, ask the learner before regenerating it. If it is
  `known`, tell the learner and stop.
- Run `python3 tools/state.py set <slug> <n> status=in_progress`, then
  `python3 tools/state.py chapter-dir <slug> <n>` to get the chapter directory, `CD` below.

## 1. Write the brief

Read the chapter's entry in `topics/<slug>/state.json` and the entries just before and
after it, the `summary.md` of every earlier done chapter, the core ideas of earlier
chapters marked `known`, `topics/<slug>/glossary.jsonl`, `topics/<slug>/pitfalls.md`,
`topics/<slug>/sources.jsonl`, and `learner-profile.md`. Then write `CD/brief.md` with:

1. **Starting point.** What the reader knows at this moment, from summaries, known chapters,
   and the profile. Note which earlier ideas this chapter should explicitly connect to.
2. **Crux.** The one question the chapter answers.
3. **Opening situation.** A concrete scenario that makes the problem felt.
4. **Sections.** For each, give a working title, the point it makes, a word budget (the
   budgets sum to the chapter's `words` range), and the source ids most likely to ground it.
5. **Running example.** One example to carry through the chapter.
6. **New terms.** The terms this chapter introduces. Exclude glossary terms and anything
   the profile says the reader knows.
7. **Misconceptions.** Mistakes learners really make about this material, at most two.
8. **Fact questions.** 12 to 25 precise questions whose answers the chapter will assert:
   rules, numbers, version-specific behavior, edge cases, history, and anything in
   `pitfalls.md` that touches this chapter. Skip what is common knowledge, or what the
   chapter derives itself, such as arithmetic shown step by step. Group the questions into
   3 to 5 batches of at most 6, by source area, and suggest source ids for each batch.
9. **Lab plan.** Following the topic's `lab` profile: for each lab, give a name, what it
   demonstrates, the runner, the expected result (`success` or `failure`), and what its
   output should make visible. Or write "no lab" with a reason.

## 2. Research and labs, in parallel

In one batch, spawn:

- One `sp-scout` per fact-question batch, in **facts mode**. Each writes
  `CD/work/scout-<k>.jsonl`. Give it the slug, the questions, the suggested source ids, the
  path to `topics/<slug>/sources.jsonl`, and a budget of at most 8 searches and about five
  minutes.
- One `sp-lab`, if the lab plan has labs. Give it `CD`, the lab plan, and the topic's lab
  profile.

When they finish, run
`python3 tools/state.py merge <slug> --chapter <n> CD/work/scout-*.jsonl`. Note any questions
the scouts could not answer. Pass them to the writer, who must then avoid those claims or
mark them `[@unverified]`.

## 3. Write

Spawn one `sp-writer` with these paths: `OUTPUT=CD/chapter.md`, `BRIEF=CD/brief.md`,
`CHAPTER_DIR=CD`, `FACTS=CD/facts.jsonl`, `SOURCES=topics/<slug>/sources.jsonl`,
`TOPIC_DIR=topics/<slug>`, and `LINT=python3 tools/lint.py CD/chapter.md`. Also pass the
lab agent's notes (line ranges, and what each output shows) and the unanswered questions.

## 4. Check

Spawn one `sp-checker` with `MODE=fix`, `CHAPTER=CD/chapter.md`, `CHAPTER_DIR=CD`,
`FACTS=CD/facts.jsonl`, `SOURCES=topics/<slug>/sources.jsonl`, `TOPIC_DIR=topics/<slug>`,
`REPORT=CD/check.md`, the slug, and the chapter number.

## 5. Final gates

- Run `python3 tools/lint.py CD/chapter.md`. If it reports errors, which usually come from
  checker edits, spawn `sp-writer` again with the same paths, plus an instruction to fix
  only the flagged paragraphs, without changing their factual content or citations. Allow
  at most two rounds. If errors remain, continue, and list them in the report.
- Run `python3 tools/lab.py check CD` if the chapter has labs. A stale or failed lab must be
  fixed with `sp-lab` before rendering, because the chapter would otherwise show output
  that does not match its code.
- Run `python3 tools/render.py CD/chapter.md`.

## 6. Record

- Run `python3 tools/state.py glossary <slug> <n>`.
- Write `CD/summary.md`: about 200 words on what the reader now knows. Cover the ideas,
  the terms introduced, the connections made, and any threads left open for later chapters.
  Write it for the next chapter's brief, not as marketing. Base it on the final
  `CD/chapter.md` and `CD/check.md`, not on the brief or the lab notes, so it carries the
  checker's corrections instead of the claims they replaced.
- Run `python3 tools/state.py set <slug> <n> status=done`, then
  `python3 tools/state.py roadmap <slug>`.

## 7. Report

Report briefly:

- the paths to `chapter<n>.pdf` and `chapter<n>-dark.pdf`
- the word count against the budget
- the checker's summary line, and anything it flagged for a human
- each remaining `[@unverified]` claim, in one line
- the lab results
- the total time, and the time per step

Suggest `/quiz <n>` once the learner has read the chapter, and `/errata` if they find a
mistake.
