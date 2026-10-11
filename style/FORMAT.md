# Chapter format

Every chapter is one Pandoc Markdown file, `chapter.md`, inside its chapter directory
`topics/<topic>/chapters/NN-<chapter-slug>/`. `tools/render.py` turns it into PDFs and
`tools/lint.py` checks it. Use only the constructs below. No raw HTML, no raw Typst.

The worked example of every construct is `style/sample/chapter.md`.

## Front matter

```yaml
---
topic: Storage engines
chapter: 4
title: Write-ahead logging
---
```

Never use a level-1 `#` heading. The title comes from the front matter.

## Skeleton, in order

1. **Opening.** No heading. One to three paragraphs that set up a concrete situation and
   the problem it causes. Main point first.
2. **Crux.** A `::: crux` block with the one question the chapter answers.
3. **Body sections.** `##` sections, `###` subsections at most.
4. **Check yourself.** A `## Check yourself` section holding one `::: selftest` block.
5. **Answers.** One `::: answers` block right after the selftest. The renderer moves it to
   the end of the chapter.

## Inline constructs

**New term, first use only.** Mark the first use of every term the reader may not know:

```markdown
A [write-ahead log]{.term def="An append-only file where every change is recorded before it is applied to the data files."} is ...
```

- `def` is one plain sentence. No double quotes inside it, no citations, no markup.
- Add `key="page table"` when the visible text is an inflected form (`page tables`).
- Mark a term once per topic. Terms already in the topic glossary are not re-marked.
- A term must not appear in the text before the place it is marked.

**Citation to a fact.** Technical claims cite fact ids from the chapter's `facts.jsonl`:

```markdown
The call blocks until the device reports the transfer is complete [@F4].
Two facts at once [@F2; @F5].
```

**Unverified claim.** If a claim matters and no fact supports it, mark it honestly. The
renderer shows a visible "unverified" marker:

```markdown
Most engines batch these writes [@unverified].
```

Inline code uses backticks. Math uses `$...$` inline and `$$...$$` for display.

## Block constructs

All blocks are Pandoc fenced divs. The bodies are ordinary Markdown.

| Block | Syntax | Use |
|---|---|---|
| Crux | `::: crux` | The chapter's central question. Exactly one. |
| Aside | `::: {.aside title="..."}` | Side material worth knowing but off the main path. This is where "by the way" content goes, never into parentheses. |
| Misconception | `::: {.misconception title="..."}` | `title` states the wrong belief as a learner would say it. The body explains what is actually true. |
| Try it | `::: tryit` | A hands-on step: a lab, a computation, or a pen-and-paper trace. |
| Self-test | `::: selftest` | An ordered list of questions. |
| Answers | `::: answers` | An ordered list of answers matching the self-test, same count and order. |

## Code

Every code block is one of three kinds.

**Tested code, included from a lab.** The body stays empty and the renderer inlines the
file, so the reader sees exactly what was run:

````markdown
```{.c include="lab/bounded-loop/prog.c" lines="10-34"}
```
````

**Captured output from a lab run.** `run.out` is written by `tools/lab.py run`:

````markdown
```{.output include="lab/bounded-loop/run.out" lines="1-12"}
```
````

`include` paths are relative to the chapter directory. `lines` is optional and 1-based
inclusive.

Show only the lines that carry the idea. One code include shows at most 25 lines, one
output include at most 20, and a chapter shows at most about 90 lines of included code in
total. Describe the rest in prose, because the reader has the full lab on disk.

**Sketch.** Short illustrative code that was not run. Twelve lines at most. It renders
with a visible "sketch" label:

````markdown
```{.go .sketch}
for _, peer := range peers {
    go requestVote(peer)
}
```
````

A code block without `include` or `.sketch` is a format error.

## Diagrams

Graphviz blocks render to vector images. Keep them small and label every node:

````markdown
```{.dot caption="A follower times out and becomes a candidate."}
digraph { rankdir=LR; Follower -> Candidate [label="timeout"]; }
```
````

## Tables

Pipe tables only, with a header row.
