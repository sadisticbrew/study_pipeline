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
   and the profile. Anything none of these teach counts as unknown, including background
   the chapter's `prereqs` take for granted. Note which earlier ideas this chapter should
   explicitly connect to.
2. **Crux.** The one question the chapter answers.
3. **Opening situation.** A concrete scenario that makes the problem felt.
4. **Sections.** For each, give a working title, the point it makes, the mechanisms it
   builds on and where the reader learned each one, a word budget, and the source ids most
   likely to ground it. A mechanism the reader has not learned yet is taught in that
   section or an earlier one, with a small example traced by hand (see "Mechanism before
   abstraction" in `style/STYLE.md`), and its words count in the budget. The budgets sum
   to the chapter's `words` range. When the foundations do not fit, cut lower-value
   material first. If that is not enough, raise the maximum, to at most 5000, with
   `python3 tools/state.py set <slug> <n> words=MIN,MAX`, and beyond that ask the learner
   whether to split the chapter.
   When the point rests on a structure, the steps of an algorithm, a flow of execution or
   data, or a sequence of state changes that the reader would otherwise have to hold in
   their head, add a diagram plan: what the figure shows, drawn from the running example,
   and what the prose around it must still explain (see "Diagrams" in `style/STYLE.md`).
   Plan one only where it earns its place. There is no target count, and most sections
   need none. When a figure shows x86-64 machine state from the running example (stack
   slots, frames, registers at an instruction), plan it as generated: name the lab that
   records it and the instruction to snapshot, and put that in the lab plan.
5. **Running example.** One example to carry through the chapter.
6. **New terms.** The terms this chapter introduces. Exclude glossary terms and anything
   the profile says the reader knows.
7. **Misconceptions.** Mistakes learners really make about this material, at most two.
8. **Fact questions.** 12 to 25 precise questions whose answers the chapter will assert:
   rules, numbers, version-specific behavior, edge cases, history, and anything in
   `pitfalls.md` that touches this chapter. Every technical claim this brief makes itself,
   in the opening, the section points, the diagram plans and the misconceptions, needs a
   question unless the chapter derives it step by step. Skip common knowledge. Group the
   questions into 3 to 5 batches of at most 6, by source area, and suggest source ids for
   each batch that a scout can read: web pages, specs, source code, or books with a copy in
   `topics/<slug>/library/` or a readable copy online. For history, suggest a readable
   secondary account rather than the original paper.
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

Resolve `VOICE_EXEMPLAR` once: `style/exemplar.md` if it exists, otherwise
`style/sample/chapter.md`. Read the entire selected file for the comparison below. If it
cannot be read, stop with a blocked handoff; only absence permits the fallback.

Spawn one `sp-writer` with these paths: `OUTPUT=CD/chapter.md`, `BRIEF=CD/brief.md`,
`CHAPTER_DIR=CD`, `FACTS=CD/facts.jsonl`, `SOURCES=topics/<slug>/sources.jsonl`,
`TOPIC_DIR=topics/<slug>`, `VOICE_EXEMPLAR=<resolved path>`, and
`LINT=python3 tools/lint.py CD/chapter.md`. Also pass the lab agent's notes (line ranges,
and what each output shows) and the unanswered questions.

Before accepting the draft for checking, inspect the writer's tool transcript for a
successful read covering the entire resolved `VOICE_EXEMPLAR` before `BRIEF` or drafting.
A self-report is not evidence. If that read is missing, return to the same writer to
read it and revise the draft's style, then verify the recorded read.
Briefly compare the opening and one mechanism-heavy section with the exemplar for pacing,
connected prose, and explanatory depth. Return concrete style problems to the same writer
for correction without changing facts or citations, and compare the revised passages
before proceeding. Lint and claim checking do not establish voice.

## 4. Check

Copy `CD/chapter.md` to `CD/work/draft.md`, so the checker's changes can be seen later. Then
spawn one `sp-checker` with `MODE=fix`, `CHAPTER=CD/chapter.md`, `CHAPTER_DIR=CD`,
`FACTS=CD/facts.jsonl`, `SOURCES=topics/<slug>/sources.jsonl`, `TOPIC_DIR=topics/<slug>`,
`REPORT=CD/check.md`, the slug, and the chapter number.

## 5. Final gates

- Run `python3 tools/lint.py CD/chapter.md`. If it reports errors, which usually come from
  checker edits, spawn `sp-writer` again with the same paths, explicitly reusing the resolved
  `VOICE_EXEMPLAR`, plus an instruction to fix only the flagged paragraphs, without changing
  their factual content or citations. Verify each retry's read and apply the same editorial
  gate before accepting it. Allow at most two rounds. If errors remain, continue, and list
  them in the report.
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
- each book the scouts said would have answered a question, with the path where the learner
  can put a copy (`topics/<slug>/library/<S-id>.pdf`, using the id `merge` gave it)
- the total time, and the time per step

Suggest `/quiz immediate <n>` once the learner has read the chapter, then `/quiz <n>` for
tutoring, `/quiz delayed <n>` about a week later, and `/errata` if they find a mistake.
