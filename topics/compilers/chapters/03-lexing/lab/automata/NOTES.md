# Automata lab

Run from the repository root with `python3 tools/lab.py run topics/compilers/chapters/03-lexing --only automata`.

The regex parser handles concatenation, alternation, grouping, ranges, `*`, `+`, and `?`; the last operator supports the timing example. Empty concatenation denotes epsilon. Thompson edges carry either a character set or epsilon. Subset construction includes the empty subset whenever reachable. Moore refinement distinguishes accepting token kinds, preserving rule priority.

## Source excerpts

All paths below are relative to this lab directory. Each suggested excerpt is at most 25 lines.

- `automata.py:87-111`: Thompson fragments, including concatenation, alternation and repetition.
- `automata.py:113-125`: epsilon closure and character move.
- `automata.py:138-156`: subset construction and accepting-rule priority.
- `automata.py:159-174`: Moore partition refinement.
- `automata.py:177-194`: longest match, retaining the last accepting position.
- `automata.py:197-205`: NFA simulation and the five running rules.
- `automata.py:232-249`: blowup family and measured timing setup.

## Output excerpts

- `run.out:1-2`: Python version.
- `run.out:4-17`: 21 NFA states, 23 edges, 9 complete DFA states and 8 minimized states. State 3 is the empty rejecting sink. State 8 contains NFA accepting states 4 (IF) and 8 (IDENT); priority chooses IF. States 4 and 7 merge in minimization. The `other a-z` column represents lowercase letters except `f` and `i`; all have identical transitions.
- `run.out:19-30`: the opening line's 11 nontrivia tokens. The table's five rules cannot recognize the entire opening line; this scan constructs another DFA with explicit punctuation, whitespace and comment rules added. It does not silently skip unmatched input.
- `run.out:32-43`: n=1..10, NFA sizes 11..65 in steps of 6, unminimized DFA sizes 3..1025, and minimized sizes exactly 2^n (2..1024). The unminimized family has 2^n+1 reachable states, not exactly 2^n.
- `run.out:45-51`: single measured full matches at n=8,12,16,20,24; milliseconds and match booleans. Both engines return True for every row. Regex compilation and NFA construction are outside the timed regions. Timings are machine-dependent, not reproducible constants or complexity proofs.
