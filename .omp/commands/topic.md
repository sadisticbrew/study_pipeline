---
description: Start a new study topic. Builds a roadmap, a source library, and a lab profile, then asks what you already know.
argument-hint: <subject> [notes about goals or scope]
---

Start a new study topic for the learner: **$ARGUMENTS**

You are the orchestrator of a personal study pipeline. The whole command should take about
ten minutes. Breadth now, depth later: each chapter does its own deep research when it is
generated, so do not read sources in depth here.

Reference files: `learner-profile.md`, `tools/SCHEMAS.md` (state formats), `style/STYLE.md`
(what chapters will be like). Run tools from the repo root.

## 1. Orient

- Read `learner-profile.md` and run `python3 tools/state.py status` to see existing topics.
- Pick a short kebab-case slug for the subject. If that topic already exists, ask the learner
  whether to resume it or start over, and stop until they answer.
- Run `python3 tools/state.py init <slug> --title "<Readable Title>"`.

## 2. Draft the roadmap from your own knowledge

Design the curriculum that would take this particular learner from where the profile says
they are to real expertise in the subject. Do this yourself, now, without searching.

- Group chapters into 3 to 6 parts. Most topics need 8 to 20 chapters, so size the roadmap
  to the subject and do not pad it.
- Each chapter has 3 or 4 core ideas, small enough for 2500 to 3500 words of prose. That
  renders to about 10 to 15 pages, which is a hard ceiling. When a chapter would need more,
  split it.
- Order chapters so each one needs only earlier chapters and the profile's known material.
  The `prereqs` field says, in plain words, what the chapter assumes.
- Where the profile lists something as shaky and the subject depends on it, add a short
  bridge chapter early on instead of assuming it.
- The early chapters build intuition and motivation. The later ones reach the precise,
  expert material: real implementations, the hard edge cases, performance, and how
  practitioners actually reason about the subject.
- Write a one-paragraph `goal` describing what the learner will be able to do at the end.

## 3. Build the source library and lab profile, in parallel

Spawn one `sp-scout` task per part, or per pair of small parts, at most 4, in a single
batch. Each one runs in **library mode** and writes `topics/<slug>/work/scout-<k>.jsonl`.
Give each the subject, its part titles with their core ideas, the learner context in one
line, a target of 4 to 8 sources, and a budget of at most 6 searches.

While they run, decide the lab profile yourself. What does hands-on practice mean for this
subject?

- Code the learner writes and runs: choose `local`, and the toolchains.
- Kernel-level work, root, or system changes: choose `vng`.
- Mostly mathematical or theoretical material: choose `local`, with small Python checks or
  simulations.
- Truly nothing runnable: choose `none`.

Run `python3 tools/lab.py doctor --toolchains <comma list>` and note any toolchain that is
missing.

## 4. Merge and finalize

- Run `python3 tools/state.py merge <slug> topics/<slug>/work/scout-*.jsonl`.
- Skim the merged source titles. If they reveal a clear gap or an important area missing
  from the roadmap, adjust the roadmap. Keep this light.
- Write `topics/<slug>/state.json` with the goal, lab profile, parts and chapters. Every
  chapter starts as `pending`, with `words` of `[2500, 3500]` unless the chapter is clearly
  lighter, and `quiz` set to null.
- Run `python3 tools/state.py validate <slug>`, fix any problems, then run
  `python3 tools/state.py roadmap <slug>`.

## 5. Ask what the learner already knows

Use the `ask` tool once, with one multi-select question per part, listing that part's
chapters by number and title, and asking which ones the learner already knows well. Add a
final single question asking whether the roadmap needs any changes, with the options
"Looks good" and "I want changes".

- Mark each selected chapter with `python3 tools/state.py set <slug> <n> status=known`.
- If the learner wants changes, make them, then validate and regenerate the roadmap again.

## 6. Report

Keep the report short: the roadmap as numbered parts and chapters, showing which are known;
the lab profile and any missing toolchain, with the install command for CachyOS (`pacman`);
the number of sources in the library; and the next step, `/chapter`.
