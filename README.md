# Study pipeline

A personal textbook generator that runs inside [oh-my-pi](https://omp.sh). It turns any
technical subject into a roadmap and then into OSTEP-style chapters, as Markdown plus light
and dark PDFs, written for the reader in `learner-profile.md`.

## Commands

Run `omp` from this directory. Every command keeps its state in `topics/`, so you can stop
and resume across sessions.

| Command | What it does |
|---|---|
| `/topic <subject> [notes]` | Drafts a roadmap, builds a source library, picks a lab profile, and asks which chapters you already know. |
| `/chapter [n] [slug]` | Brief, then fact scouts and lab builder in parallel, then one writer, a claim checker, lint, and render. |
| `/bakeoff [n]` | Four writer models write the same excerpt blind. `/bakeoff pick <A-D>` reveals them and sets the writer. |
| `/quiz [n]` | Tutor session with guiding questions. Records what is solid and what is shaky, and updates your profile's progress notes. |
| `/quiz immediate\|delayed [n]` | Unaided test: two new questions per core idea, no hints, scored at the end. Results append to `topics/<slug>/assessments.jsonl`, and `tools/state.py assess` compares them over time. |
| `/errata [n] <problem>` | Verifies a reported mistake, fixes the chapter and any later ones, and records the pitfall for future checks. |

## Models

Roles live in `.omp/config.yml`: `sp_writer`, `sp_checker` (always a different family from
the writer), `sp_scout`, and `sp_lab`. The orchestrator is whatever model your `omp` session
runs. A capable mid-tier model works well, for example
`omp --model opencode-go/glm-5.2:high`.

## How correctness is handled

- Scouts copy short verbatim quotes from pinned versions of primary sources into
  `facts.jsonl`. They read every source through `tools/fetch.py`, which keeps a text copy
  and remembers links that failed, so a dead link is not retried by every agent.
- The writer may only assert what those facts support, and must mark anything else
  `[@unverified]`, which shows up visibly in the PDF.
- Lab code and output are included from real sandboxed runs (`tools/lab.py`), never typed by
  the model.
- A checker from another model family verifies each claim, and `/errata` feeds the mistakes
  you find back into future checks through `pitfalls.md`.

## Tools

All tools are Python stdlib only. Each one supports `--help`.

- `tools/state.py`: topics, roadmap, merging sources and facts, glossary, and progress.
- `tools/fetch.py`: downloads a source once, as text, into `topics/<slug>/cache/`, and fails
  fast on dead or stalled links.
- `tools/lab.py`: runs labs with bubblewrap, or with virtme-ng for kernel work.
  `lab.py doctor` checks this machine.
- `tools/lint.py`: style and format gate. Tune the thresholds and phrase lists in
  `style/lint.toml`.
- `tools/render.py`: Pandoc to Typst to PDF, using vendored fonts in `style/fonts/`.
- `tools/claims.py`: each paragraph beside the facts it cites. The checker starts here.

`style/sample/` is a complete reference chapter. Run
`python3 tools/render.py style/sample/chapter.md` to preview template changes.

Requires: pandoc, typst, graphviz, bubblewrap, curl, poppler (`pdftotext`), and virtme-ng
(only for kernel labs).

## Books

Scouts read a book from your own copy when there is one, and otherwise look for a readable
copy online. To give them your copy, put it at
`topics/<slug>/library/<S-id>.pdf` (or `.epub`, `.html`, `.txt`), using the book's id from
`sources.jsonl`. The folder is not tracked by git. After `/chapter`, the report lists any
book the scouts needed but could not read.
