---
description: Report a mistake or a confusing passage in a chapter. Verifies it, fixes the chapter, and records the pitfall so later chapters avoid it.
argument-hint: "[chapter number] <what is wrong or confusing>"
---

The learner reports a problem in a chapter: `$ARGUMENTS`

Work from the repo root. The topic is in `topics/.current`. If no chapter number is given,
use the most recently completed chapter, and confirm which passage is meant if that is
ambiguous.

## 1. Find and understand

Locate the passage in `CD/chapter.md`. Read the facts it cites in `CD/facts.jsonl`, their
sources in `topics/<slug>/sources.jsonl`, and any lab output it describes.

## 2. Verify

Decide which case this is, using primary sources:

- **Error.** The chapter is wrong, or it stretches a fact.
- **Confusing.** The chapter is correct, but the passage is unclear, skips a step, or uses a
  term the learner did not have.
- **Learner misunderstanding.** The chapter is correct and clear.

Read the cited source passage yourself. When the existing facts do not settle the question,
look it up in a primary source. For anything larger than a couple of lookups, spawn an
`sp-scout` in facts mode, and merge its output with
`python3 tools/state.py merge <slug> --chapter <n>`.

## 3. Act

- **Error:** fix the passage with the smallest change that makes it true, in the chapter's
  voice. Correct or add facts through `merge` when a fact was wrong or missing. Then search
  every later chapter with status `done` for the same mistake, and fix it there too. Also
  fix the mistake in `CD/summary.md` and in the `summary.md` of those later chapters,
  because the next chapter's brief is built from them.
- **Confusing:** rewrite only that passage so it is clear. Follow `style/STYLE.md`, and add
  a `.term` definition if a term was missing.
- **Misunderstanding:** do not edit the chapter. Explain the point to the learner patiently,
  pointing to the passage and the source. Then ask yourself honestly whether the text
  invited the misreading, and if it did, treat it as confusing.

After any edit, run `python3 tools/lint.py CD/chapter.md` and fix what it flags in the
edited paragraphs, then run `python3 tools/render.py CD/chapter.md`.

## 4. Record

For an error or a confusing passage, append an entry to `topics/<slug>/pitfalls.md`:

```markdown
## <YYYY-MM-DD> chapter <n>: <short title>
- Kind: error | confusing
- Wrong or unclear: <what the chapter said>
- Correct: <the true statement, or what made it clear>
- Evidence: <fact id or URL>
```

Future checkers read this file, so state the correct version precisely.

## 5. Report

Say what you found, what you changed and where, including later chapters and summaries, and
that the PDFs were re-rendered. Keep it short.
