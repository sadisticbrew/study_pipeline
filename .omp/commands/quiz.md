---
description: Interactive tutor session on a chapter, or with immediate or delayed, an unaided test recorded in an append-only history.
argument-hint: "[immediate|delayed] [chapter number]"
---

Run a tutoring session on a chapter. Arguments: `$ARGUMENTS`. Use the topic in
`topics/.current`. If no chapter number is given, use the most recently completed chapter.
If the first argument is `immediate` or `delayed`, run an unaided test instead, following
only "Test mode" at the end.

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

## Test mode

A test measures what the learner can recall and apply unaided, so that results can be
compared over time. `immediate` is for right after reading the chapter, before any tutoring
on it, and `delayed` is for days or weeks later. Both run the same way, and only the label in
the history differs. Without a chapter number, `delayed` takes the chapter whose latest test
is oldest, from `python3 tools/state.py assess <slug>`.

1. Run `python3 tools/state.py assess <slug> <n>`. It prints the chapter's core ideas, the
   points per core idea in every earlier test, and every question already asked. Read
   `learner-profile.md`, `CD/chapter.md`, and `CD/facts.jsonl`.
2. Before asking anything, plan two questions for each core idea. Every question is new:
   not a self-test question, not an example the chapter works through, and not a question
   from the history, even reworded. Test the idea itself in a situation the chapter did not
   show: predict what happens, apply it to a new input or system, explain why a design is
   the way it is, or spot the bug. Keep each one answerable from the chapter alone and at
   the depth the chapter taught, so that tests stay comparable. Note the expected answer
   for each and check it against the chapter's facts.
3. Tell the learner briefly that this is a test without notes or hints, that "I don't know"
   is a fine answer, and that feedback comes at the end.
4. Ask one question at a time in plain chat. Between questions, do not hint, correct, or
   confirm. Acknowledge the answer in a few words and ask the next. If the learner asks for
   help, say it comes at the end. On "stop", go straight to scoring what was answered.
5. Score each answer against its expected answer: 2 when the reasoning is right and
   complete, 1 when the idea is right but a step is missing or wrong, 0 when it is wrong or
   not known. Judge substance, not wording.
6. Write `CD/work/assessment.json` as
   `{"kind": "<immediate or delayed>", "items": [{"concept": "...", "question": "...", "score": 2}]}`,
   with one item per question asked and `concept` copied verbatim from the core ideas the
   tool printed. Then run
   `python3 tools/state.py assess <slug> <n> --record CD/work/assessment.json`. It adds
   today's date, appends the test to `topics/<slug>/assessments.jsonl`, and prints the
   history including this test. If it reports a problem, fix the file and rerun. Never edit
   `assessments.jsonl` by hand.
7. Give the feedback: each question with its score and, for any score below 2, the expected
   answer in one or two sentences and the section to reread. Everything you state must agree
   with the chapter's facts. Then compare with earlier tests from the tool's output, naming
   the core ideas that rose or fell.
8. A test does not tutor, and it changes neither `state.json` nor `learner-profile.md`.
   Suggest `/quiz <n>` for tutoring when a core idea scored below half, and
   `/quiz delayed <n>` about a week after an immediate test or a few weeks after a delayed
   one. Suggest `/errata` when a wrong answer traces back to a wrong or confusing passage.
