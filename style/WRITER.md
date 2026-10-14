# Chapter writer procedure

You write one chapter, or one bake-off excerpt, alone and in one voice. The task message
gives you these paths:

- `OUTPUT`: the Markdown file you write.
- `BRIEF`: what to cover, section by section, with word budgets.
- `CHAPTER_DIR`: the chapter directory. Lab includes resolve relative to it.
- `FACTS`: the chapter's `facts.jsonl`. `SOURCES`: the topic's `sources.jsonl`.
- `TOPIC_DIR`: the topic directory, with `glossary.jsonl`, `pitfalls.md`, and earlier chapters.
- `LINT`: the exact lint command to run on your output.

## 1. Read, in this order

1. `learner-profile.md`: who you are teaching.
2. `style/STYLE.md`: how to teach and how to sound. This is the most important file.
3. `style/FORMAT.md`: the markup you must use.
4. `style/exemplar.md` if it exists, otherwise `style/sample/chapter.md`. Absorb the voice.
   If `style/exemplar.md` exists it was hand-edited by the learner, and its voice outranks
   everything else.
5. `BRIEF`, then every fact in `FACTS`, then `TOPIC_DIR/glossary.jsonl` and
   `TOPIC_DIR/pitfalls.md`.
6. The `summary.md` of each earlier chapter in `TOPIC_DIR/chapters/`, so you know what the
   reader has already learned and can connect to it.
7. Every lab in `CHAPTER_DIR/lab/`: its source files and `run.out`.

Read nothing else. In particular, do not read the source of the tools in `tools/`. Their
messages say what to fix.

## 2. Write section by section

The brief is your plan, so do not write a separate one, and do not draft the chapter in your
head before you start. Write the front matter, opening, and crux to `OUTPUT` first. Then,
for each `##` section of the brief, think only about that section, pick the facts it rests
on, and append it to `OUTPUT`. Before each section, reread the end of the previous one so
the transition flows. A section should never read as if it was written in isolation.

While writing:

- Cite facts as you go. If a sentence needs a fact that is not in `FACTS`, either drop the
  claim, soften it to what the facts do support, or mark it `[@unverified]`. Never cite a
  fact for something it does not say.
- Common knowledge and reasoning you show step by step in the text, such as arithmetic,
  need no citation.
- Include lab code and output only with `include=`, and show only the lines that carry the
  idea (see the limits in `style/FORMAT.md`). Describe only what `run.out` shows.
- Mark each new term at its first use, and check that it does not appear earlier.
- Draw the diagrams the brief plans, following "Diagrams" in `style/STYLE.md`: write the
  paragraph that leads into the figure, the `dot` block, then the text that points at what
  to notice. Drop a planned figure if the prose turns out clearer without it, and add one
  the brief did not plan only when the section passes the same test.
- Respect the word budget per section. Running long in one section means cutting later.

## 3. Lint and fix

Run the `LINT` command. Fix each finding with a targeted `edit` of the paragraph it points
at. Never rewrite or regenerate the whole file to fix lint findings. Rewrite the flagged
paragraph so the problem is gone and it still reads naturally. Do not just delete the
offending punctuation or swap in a synonym. Rerun lint. Repeat until there are no errors,
at most three rounds. Fix warnings when the fix makes the text better.

## 4. Report

Reply with: final word count, the number of `[@unverified]` markers and what each one is
about, any brief items you could not cover and why, and any lint findings you left in place
with the reason.
