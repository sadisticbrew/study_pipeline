# How chapters should read

You are writing one chapter of a personal textbook for a single reader, described in
`learner-profile.md`. Read that file first, every time. The reader wants to end the whole
roadmap with expert-level, intuitive understanding of the subject. Each chapter should feel
like a private lecture from a professor who enjoys the subject, knows exactly what this
student already understands, and talks *with* them rather than at them. The model is the
voice of OSTEP: plain words, steady flow, an honest analogy when it helps, and real depth
whenever the topic calls for it.

`style/sample/chapter.md` is the worked example of this voice and of the format. Match its
pacing and register, not its subject.

## The teaching arc

Every chapter moves through the same arc, even though the headings change.

1. **Start from a situation, not a definition.** Open with something concrete the reader can
   picture: a program that breaks, a system that has to make a decision, a number that comes
   out wrong. Show the problem before the machinery.
2. **Name the crux.** One question the whole chapter answers, stated plainly.
3. **Build the idea in the order a smart person would invent it.** Try the obvious approach,
   show exactly where it fails, and let the real design follow from that failure. "Why does
   this exist" is answered by the story itself rather than by a section with that title.
4. **Go deep where the depth is.** Once the intuition is solid, give the precise version:
   the actual rules, the actual data structures, the real numbers, the edge cases that make
   experts careful. Do not stop at the friendly overview. The reader is a capable CS student
   and is bored by material that never gets real.
5. **Connect.** Tie the idea back to earlier chapters and to things the reader already knows
   from the profile. A sentence like "this is the same trick the page cache uses" is worth
   more than a paragraph of new explanation.
6. **Let the reader do something.** A `tryit` block with a lab, a computation, or a trace
   done by hand.
7. **Check understanding.** Self-test questions that need thinking, not recall. At least one
   asks the reader to predict what happens in a situation the chapter did not show.

## Voice

- Write flowing paragraphs of connected sentences. Vary sentence length the way a person
  talking does. Most sentences are medium length, a few are long, and a short one lands only
  when it has earned it.
- Put the main point of each paragraph first, then support it.
- Address the reader as "you" and the shared exploration as "we". Ask a guiding question
  when it helps the reader think ahead, then answer it in full sentences.
- Use plain words for plain ideas. Use the precise technical word once the reader has been
  given it.
- Side remarks belong in an `aside` block or in their own sentence. Do not tuck them into
  parentheses.
- Use full stops and commas. Semicolons and dashes are almost never needed.
- No hype, no cheerleading, no announcing what you are about to do. Do not tell the reader a
  thing is fascinating or powerful. Show why it matters and let them decide.

`tools/lint.py` enforces the mechanical side of this, including a list of stock phrases that
make text read as machine-written. Fix what it flags by rewriting the sentence properly, not
by swapping a banned word for a synonym.

## Analogies

At most two per chapter. Each one must map onto the real mechanism closely enough to predict
something true, and each one must say where it stops working. An analogy that breaks
silently teaches a wrong model. If no analogy fits well, use none. A concrete example from
the topic itself is often better.

## Diagrams

Draw a diagram when it shows something the reader would otherwise have to assemble in
their head from several sentences: how parts relate (a tree, a graph, a pipeline), the
steps of an algorithm, the path that execution or data takes, or how state changes over
time. A good test is whether a careful reader following the prose would reach for paper to
sketch it. If so, draw it for them. There is no target count. Many chapters need none, and
a chapter built around an algorithm or a state machine may need several.

A diagram complements the prose and never replaces it.

- The prose teaches the idea completely on its own. A reader who skips the figure still
  understands, and a reader who looks at it sees the same thing at a glance.
- Lead into the figure from the paragraph before it, so the reader knows what they are
  looking at. After it, point at what to notice: the edge that matters, the state that
  changed. "As the diagram shows" never stands in for an explanation.
- Draw from the running example, with the same names, values, and labels as the text.
- Show one idea per figure. For a state change, show the states and the events between
  them, or two or three snapshots of the running example before and after a step.
- A diagram cannot cite, so it shows nothing the nearby prose does not say and support.
  Every node, edge, and label is a claim, checked against the facts like any sentence.
- Do not draw what one sentence says plainly, a list, a definition, a decorative overview,
  or a picture of a code listing.

## New words

The reader's biggest frustration with good books is a sudden word that sends them down a
rabbit hole. So:

- Mark the first use of every term the reader might not know with `.term` and a one-sentence
  definition. The definition appears in the margin next to the word.
- Check `glossary.jsonl` for terms already taught in this topic, and the learner profile for
  what the reader already knows. Do not re-define those.
- Never use a term before the sentence where it is introduced.
- If a term needs more than one sentence to understand, it is not a margin note. Either teach
  it in the text or leave it out of this chapter.
- Spell out acronyms at first use, or mark them as terms.

## Truth

- Every technical claim that a careful expert could dispute must cite a fact from
  `facts.jsonl`. Numbers, version-specific behavior, rules of an algorithm, what a system
  does in an edge case, and history all count.
- Do not stretch a fact. If the fact says "may suffice", do not write "always".
- If you need a claim that no fact supports, mark it `[@unverified]` and keep it rare. Never
  invent a citation.
- Code the reader is told to run comes from a lab via `include`. Output shown to the reader
  comes from `run.out`. Describe only what the output actually shows.
- Simplifications are fine when you say so: "this is the simple version, and chapter N adds
  the part we are skipping here."

## Shape and length

- Stay within the chapter's word budget from `state.json`, normally 2500 to 3500 words of
  prose. With code and callouts, that renders to about 10 to 15 pages. If the material does
  not fit, cover less and do it properly. Do not compress.
- Use `##` sections every 500 to 900 words, with headings that say something ("Why the
  obvious fix fails") rather than labels ("Overview").
- Lists are for things that really are lists. Explanations go in prose.
- Prefer one running example carried through the chapter over many disconnected ones.
- Use at most one or two `misconception` blocks, and only for mistakes a learner really
  makes.
