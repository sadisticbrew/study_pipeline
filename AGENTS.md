# Study pipeline

This repository is a personal textbook generator for one learner, described in
`learner-profile.md`. The learner drives it with slash commands: `/topic`, `/chapter`,
`/bakeoff`, `/quiz`, and `/errata`, defined in `.omp/commands/`. Specialist agents live in
`.omp/agents/`, and their models are mapped through `modelRoles` in `.omp/config.yml`.

## Map

- `style/STYLE.md`: how chapters teach and sound. `style/FORMAT.md`: the chapter markup.
  `style/WRITER.md`: the writer procedure. `style/sample/`: a complete reference chapter.
- `tools/SCHEMAS.md`: every state and data file format.
- `tools/state.py`: topics, roadmap, merging sources and facts, glossary, and progress.
- `tools/fetch.py`: reads a source (URL, or S-id for the learner's own book copies) once,
  as text, into the topic cache, and fails fast on dead or stalled links.
- `tools/lab.py`: runs chapter labs in a sandbox (bubblewrap, or virtme-ng for kernel work).
- `tools/lint.py`: style and format gate. `tools/render.py`: Markdown to light and dark PDFs.
- `tools/claims.py`: each paragraph of a chapter with the facts it cites, for checking.
- `tools/models_opencode.py`: switches the model roles back to OpenCode Go models.
- `topics/<slug>/`: all state for one topic.

## Rules for every agent

- Use the tools in `tools/` for state changes they cover, instead of hand-editing generated
  files (`roadmap.md`, `glossary.md`, `glossary.jsonl`, `unreachable.jsonl`, `run.out`,
  `run.status.json`).
- Never invent sources, quotes, citations, or program output. A missing fact is better than
  a wrong one.
- Never use sudo on the host. Kernel-level labs run in the `vng` runner.
- `learner-profile.md` belongs to the learner. Only `/quiz` updates its `## Progress`
  section, and other sections change only with the learner's explicit agreement.
- Run tools from the repo root.
