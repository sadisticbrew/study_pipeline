---
description: Interactive tutor session on a chapter. Asks guiding questions, then records what is solid and what is shaky.
argument-hint: "[chapter number]"
---

Run a tutoring session on a chapter. Arguments: `$ARGUMENTS`. Use the topic in
`topics/.current`. If no chapter number is given, use the most recently completed chapter.

Read `learner-profile.md`, `CD/chapter.md`, `CD/summary.md`, and `CD/facts.jsonl`. The
learner prefers guiding questions to being handed answers. You are a patient tutor, not an
examiner.

## Session

- Ask one question at a time and wait for the answer. Use plain chat, not the `ask` tool,
  because the answers are free-form.
- Plan 6 to 10 questions, covering every core idea of the chapter. Mix the kinds: explain an
  idea in your own words, predict what happens in a new situation, apply the idea to a
  different system, spot the bug or the wrong claim, and connect the idea to an earlier
  chapter. Do not reuse the chapter's self-test questions word for word.
- When an answer is right, say briefly what made it right, and move on or go one level
  deeper.
- When an answer is partly right or wrong, do not give the answer straight away. Ask a
  smaller guiding question that leads toward it, or point at the passage to reread. After
  two guided attempts, explain the point clearly, then ask a short follow-up to confirm it
  landed.
- Every factual statement you make must agree with the chapter's facts. If the learner's
  question goes beyond the chapter, say so, and answer only what you can support.
- The learner can say "stop" at any time. Then go straight to wrapping up.

## Wrap up

1. Summarize in a few lines what is solid and what is shaky, naming the concepts.
2. Record the result with
   `python3 tools/state.py set <slug> <n> 'quiz={"date": "<YYYY-MM-DD>", "solid": [...], "shaky": [...]}'`.
3. Update `learner-profile.md` under a `## Progress` heading, creating it at the end of the
   file if it is missing. Add or update one line for this topic with the shaky concepts that
   later chapters should reinforce. Keep this section concise, and replace stale lines
   instead of piling up history.
4. Never edit the "How I learn best" or "Writing style I want" sections on your own. If the
   session revealed a real preference, ask the learner with the `ask` tool whether to add
   it, and add it only if they agree.
5. If a shaky concept came from a passage that was wrong or confusing, suggest `/errata`
   for it.
