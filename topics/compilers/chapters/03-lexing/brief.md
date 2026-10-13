# Chapter 3 — Lexing: regular languages and automata

## 1. Starting point

The reader is Pratham, a 2nd-year CS student whose main language is Go, who also writes C
and Python and is learning Rust. He has built a tree-walking interpreter (so he has
written an ad hoc lexer before), an OCI container runtime and an eBPF tracer. He knows
sets and graphs at an intro discrete-math level. He has **not** studied formal languages
or automata, so "regular language", "NFA" and "DFA" must be built from plain language up.
He prefers guiding questions to finished answers, and dislikes runs of punchy sentences,
stuffed parentheses and heavy semicolons.

From chapter 1 he knows the compiler/interpreter distinction, the front/middle/back-end
split, IR, and the Go compiler's phases, including that `cmd/compile/internal/syntax`
holds Go's lexer, parser and syntax tree. He built `exprc`, whose `lex` function is a
hand-written loop: skip whitespace, read a run of digits as a number token, treat each of
`+-*/()` as its own one-character token, panic on anything else, append an EOF token.
Chapter 1 explicitly deferred lexing and parsing to chapters 3 to 5.

From chapter 2 he knows x86-64, the stack, System V and reading compiler output. That is
not needed here beyond one callback at most.

Glossary terms already defined (do not redefine): interpreter, compiler, front end, IR,
compiler driver, and the chapter 2 machine terms.

Connections to make explicitly:

- `exprc`'s `lex` is the anchor. Open from it: it works because every token is either one
  character or a run of digits. Ask what breaks the moment the language gets `<` and `<=`,
  `=` and `==`, keywords like `if` that look like identifiers, and `//` comments.
- His interpreter's lexer: he probably wrote a `switch` on the current character with a
  lookahead. The chapter should show that this hand-written loop *is* a DFA in disguise,
  and that the theory explains why that loop is correct and when it is not.
- His Go experience: Go's automatic semicolon insertion is a lexer rule, which he has
  relied on every day without knowing where it lives.
- Seeds by name: chapter 4 (grammars; regular languages cannot express nested
  parentheses, which is why the parser exists), chapter 5 (LR parsing, which reuses the
  same subset-construction idea on items), and the lexer lab feeds the parser built in
  chapter 4.

## 2. Crux

**How does a compiler turn a stream of characters into tokens correctly and in linear
time, and why do regular expressions, NFAs and DFAs give exactly the right theory for
that job, so that a hand-written lexer and a generated one are the same machine?**

## 3. Opening situation

Pratham extends `exprc`'s language with variables, comparisons and `if`. He feeds his
lexer the line

```
if x1 <= 10 { y = x1 * 2 } // done
```

and the one-character-per-token trick falls apart in four places at once. `<=` must be
one token, but `<` alone is also a token, so after reading `<` the lexer cannot know what
it has until it peeks at the next character. `if` must be a keyword but `x1` and `iffy`
are identifiers, and both start the same way. `//` starts a comment that swallows the rest
of the line, but `/` alone is division. Spaces separate tokens but carry no meaning. He
could keep adding special cases to the loop, but he wants to know whether there is a rule
that tells him the right answer every time, and a way to be sure his loop implements it.
By the end he can write the token rules as regular expressions, build the automaton by
hand for a small set of them, explain why it runs in time linear in the input, and write
a production-quality lexer in Go for the book's language.

## 4. Sections

Budgets sum to 3200, inside the chapter's 2500 to 3500 range.

1. **Why lexing is its own phase** (~450 words)
   Plain language first: a token is a category plus the text it came from (the lexeme),
   such as identifier `x1` or operator `<=`. Why split it from parsing: the parser then
   sees a short stream of meaningful units without whitespace and comments, the lexer's
   job is simple enough for a faster, simpler technique, and the two can be specified
   separately. Introduce tokens, lexemes and token kinds with the opening line as a table
   of tokens. Ground in S7/S32 (Engineering a Compiler) and scout batch 1.

2. **Two rules every lexer needs: longest match and priority** (~550 words)
   Maximal munch: at each point take the longest prefix that forms a token, which is why
   `<=` beats `<`, and `iffy` is one identifier rather than `if` plus `fy`. Quote the Go
   spec's wording. Priority: when two rules match the same longest text (`if` is both a
   keyword and an identifier), an ordering decides. The C example `x+++++y` (from the C
   standard) shows munch is greedy and can produce a lexing that is legal as tokens but
   fails in the parser; use the `real-lexers` lab's gcc error. Go's semicolon insertion as
   a lexer rule that looks at the previous token. Guiding question before the answer:
   "after reading `<`, what must the lexer do before it can emit anything?" Ground in
   scout batch 1 and S5.

3. **Regular expressions and Thompson's construction** (~650 words)
   A regular expression describes a set of strings using three operations, concatenation,
   alternation and Kleene star, plus the empty string; character classes are shorthand.
   Write the book's token rules this way. An NFA as a graph of states with labelled edges
   and ε-edges, which may be in several states at once. Thompson's construction as a small
   recipe per operator that glues fragments, so the NFA's size grows linearly with the
   regex. History in two sentences: Kleene's regular events, Thompson's 1968 CACM paper
   that compiled regexes to IBM 7094 code (S3). Simulating the NFA by tracking the set of
   current states gives a linear-time scan, and Cox's article (S4) contrasts this with
   backtracking matchers that go exponential; show the `automata` lab's timing table.
   Ground in S3, S4, S7/S32 and scout batch 2.

4. **From NFA to DFA: subset construction and minimization** (~750 words)
   The insight: the set of NFA states you could be in is itself a single state of a new
   machine, so precompute those sets. Walk ε-closure and move on the small running
   automaton (rules for `if`, identifiers `[a-z][a-z0-9]*`, integers, `<` and `<=`), and
   show the `automata` lab's printed DFA table. Point at the DFA state that contains both
   the keyword's accepting NFA state and the identifier's, and show priority resolving it.
   Then the cost: a DFA can need exponentially more states than the NFA, using the lab's
   `(a|b)*a(a|b)^{n-1}` table, and why lexer token sets do not hit this in practice.
   Minimization: merge states no input can tell apart, the idea behind Hopcroft's
   algorithm, the result being unique up to renaming, and the lab's before/after counts.
   Ask the reader to predict which states merge before showing the result. Ground in
   S7/S32 and scout batch 3.

5. **Real lexers: hand-written versus generated** (~600 words)
   Generated: flex takes a list of regex rules with actions and emits a C table-driven
   scanner, applying longest match and earliest-rule priority; show the `real-lexers` lab
   where swapping the keyword and identifier rules changes the output and flex warns.
   re2c in one or two sentences as a generator that emits directly coded DFAs. Hand-written:
   Go's compiler (`cmd/compile/internal/syntax`), `go/scanner` (S5), and others the
   scouts confirm (clang, rustc_lexer). Why production compilers often hand-write lexers:
   error messages, positions, special cases like semicolon insertion, raw strings, speed,
   and keywords recognised by scanning an identifier and looking it up in a table rather
   than by DFA states. Make the "same machine" point: the lab's Go lexer's `switch` on the
   current character is the DFA's transition function written by hand. Show `go/scanner`
   inserting semicolons in the lab output. Ground in S5 and scout batch 4.

6. **Your lexer** (~200 words)
   Walk the `lexer` lab: the book's token set, the opening line's token stream with
   line:column positions, and how each rule from section 2 appears in the code. Close with
   the limit: no regex can describe arbitrarily nested parentheses, so the next chapter
   needs grammars. No new facts beyond the lab.

## 5. Running example

The source line from the opening, `if x1 <= 10 { y = x1 * 2 } // done`, in the book's
small Go-like language. It appears in section 1 as a token table, in section 2 for `<=`,
`if`/`iffy` and `//`, in section 4 as the motivation for the small automaton (whose rules
are exactly the ones this line needs: `if`, identifiers, integers, `<`, `<=`), in
section 5 through flex and `go/scanner`, and in section 6 as the lexer lab's input.
`exprc`'s `lex` from chapter 1 is the secondary example in the opening and section 5.

## 6. New terms

token, lexeme, token kind (token class), lexer (scanner), maximal munch (longest match),
keyword (reserved word), regular expression, regular language, Kleene star, alternation,
nondeterministic finite automaton (NFA), ε-transition, Thompson's construction,
deterministic finite automaton (DFA), ε-closure, subset construction, DFA minimization,
lexer generator, semicolon insertion.

Excluded as already in the glossary or known: interpreter, compiler, front end, IR.

## 7. Misconceptions

1. **"A lexer should try each token rule in order and take the first one that matches."**
   First match gives `<` for `<=` and `if` for `iffy`. The rule is longest match first,
   then priority among rules that tie on length. In flex, rule order only breaks ties.
2. **"Regular expressions in a compiler's lexer are the same thing as Perl or Python
   regexes."** Library regexes add backreferences and use backtracking, which is
   exponential in bad cases and not regular. Lexer regexes are the strict regular subset,
   compiled to an automaton that reads each character once.

## 8. Fact questions

Pitfalls file is empty for this topic, so no pitfall questions.

### Batch 1 — Tokens, maximal munch and Go's rules (suggest S5, S7, S32; search go.dev/ref/spec, C standard draft N1570 or N3220)

1. What exact wording does the Go language specification use for the longest-match rule
   when breaking input into tokens?
2. What is Go's automatic semicolon insertion rule: after which kinds of final token on a
   line does the lexer insert a semicolon?
3. How many keywords does Go reserve, and which are they?
4. What does the C standard (6.4) say about forming the next preprocessing token, and
   what does its `x+++++y` example say about how that sequence is tokenized and whether it
   is valid?
5. How does Engineering a Compiler (Cooper and Torczon) define the scanner's job and
   motivate keeping it separate from the parser (words, syntactic categories)?

### Batch 2 — Regular expressions, Thompson and backtracking (suggest S3, S4, S7, S32)

6. What did Thompson's 1968 CACM paper describe: what did it compile regular expressions
   into, for which machine, and in which program was the technique used?
7. What size bound does Thompson's construction give: how do the number of NFA states and
   the simulation time relate to the regex length m and input length n (per Cox, S4)?
8. What does Cox's article show for backtracking matchers on `a?^n a^n`: which
   implementations, which n, what timings, versus the Thompson NFA?
9. Who introduced regular expressions (Kleene, 1951 report / 1956 paper "regular
   events"), and who introduced nondeterministic finite automata and the subset
   construction (Rabin and Scott, 1959)?
10. Does Go's `regexp` package guarantee linear time in input size, and does it support
    backreferences? (pkg.go.dev/regexp.)

### Batch 3 — Subset construction and minimization (suggest S7, S32; search Hopcroft 1971, standard textbook or lecture notes)

11. How does Engineering a Compiler define ε-closure and the subset construction (its
    names for the operations, e.g. Delta/move and the worklist)?
12. What is the worst-case number of DFA states from subset construction for an n-state
    NFA, and what is the standard family of languages that needs 2^n DFA states (e.g. the
    n-th symbol from the end is `a`)?
13. What is Hopcroft's DFA minimization algorithm's running time, and when was it
    published? Does Engineering a Compiler also present Brzozowski's algorithm?
14. Is the minimal DFA for a regular language unique up to renaming of states
    (Myhill–Nerode theorem)?
15. How does a lexer DFA handle multiple accepting token kinds and longest match at run
    time (remember the last accepting state and position, then roll back), per
    Engineering a Compiler or flex?

### Batch 4 — Production lexers (suggest S5; search go.googlesource.com / github golang/go, flex manual, re2c.org, clang internals manual, rustc_lexer docs)

16. Is Go's compiler lexer, `cmd/compile/internal/syntax/scanner.go`, hand-written, and
    how does it recognize keywords (lookup after scanning an identifier)?
17. What does `go/scanner`'s `Scan` return, and how does it report an automatically
    inserted semicolon (its literal is `"\n"`)?
18. How does flex choose between rules: longest match, then the rule listed first; and
    what warning does flex give for a rule that can never match?
19. What does re2c generate (directly coded DFA rather than tables), and which known
    projects use it?
20. Are clang's lexer (`clang::Lexer`) and rustc's lexer (`rustc_lexer`) hand-written,
    per their own docs?

## 9. Lab plan

Runner `local` for all three. Toolchains: go, python3, gcc, flex (installed at
`/usr/bin/flex`; re2c is not installed, so no re2c lab). Each `run.sh` should print short,
quotable sections with clear headers, print tool versions, and the lab notes must give
line ranges of `run.out` for each section. Labs print observations, never conclusions.

1. **`automata`** — the theory as runnable code (Python 3).
   - Demonstrates: a small regex parser supporting concatenation, `|`, `*`, `+`,
     parentheses and character ranges; Thompson's construction to an NFA; subset
     construction to a DFA; Hopcroft or Moore minimization. Apply it to the running
     token set: `if` (keyword, highest priority), identifier `[a-z][a-z0-9]*`, integer
     `[0-9]+`, `<`, `<=`. Print the NFA state and edge counts, the DFA transition table
     with each DFA state's NFA-state set and which token it accepts (showing the state
     that contains both the keyword and identifier accept states, and that priority
     picks the keyword), then the minimized state count. Use readable character-class
     labels so the table is short enough to quote. Then, a longest-match scan of the
     opening line using the DFA, printing tokens. Then the blowup table: for
     `(a|b)*a(a|b){n-1}` (written out as concatenation), n = 1..10, print NFA states,
     DFA states and minimized DFA states. Then a backtracking-versus-NFA timing table:
     Python's `re.fullmatch` on `a?^n a^n` against `a^n` for n up to the largest value
     that keeps the whole lab well under its timeout (around 20 to 25), next to the
     lab's own NFA simulation time for the same n. Timings are machine-dependent; print
     them as measured.
   - Expected result: `success`.
   - Output should make visible: the DFA table with the keyword/identifier tie, the token
     stream, DFA sizes growing as 2^n (whatever the code actually measures), and
     backtracking time growing far faster than the NFA's.

2. **`lexer`** — the book's lexer in Go, replacing `exprc`'s `lex`.
   - Demonstrates: a hand-written Go lexer (one `main.go`, plus a small driver) for the
     book's language: identifiers, decimal integer literals, keywords `func var if else
     return` (recognized by scanning an identifier and then looking it up in a map),
     operators and punctuation `+ - * / = == != < <= > >= ( ) { } , ;`, `//` line
     comments, whitespace, line:column positions, an error token for an unexpected
     character rather than a panic, and EOF. Code short enough to quote its core
     `switch` (aim under 150 lines). Print the token stream of the opening line with
     kinds, lexemes and positions; then a few maximal-munch edge cases each on its own
     line: `a<=b`, `a< =b`, `iffy if`, `x==y=z`, `10/2//c`, and an input with a bad
     character such as `x @ y`.
   - Expected result: `success`.
   - Output should make visible: `<=` as one token, `iffy` as an identifier, `if` as a
     keyword, the comment skipped, positions, and the error token.

3. **`real-lexers`** — production lexers and a generator.
   - Demonstrates: (a) a short Go program using `go/scanner` on a few lines of Go source
     without semicolons, printing position, token and literal, so the automatically
     inserted semicolons (literal `"\n"`) are visible; (b) a flex specification for the
     running token set with the `if` rule before the identifier rule, built with flex
     and gcc and run on the opening line, then a variant with the two rules swapped,
     showing flex's warning at generation time and `if` now lexed as an identifier;
     (c) `gcc -fsyntax-only` on a tiny C file containing `x+++++y` and on one with
     `x++ + ++y`, printing gcc's diagnostics as produced.
   - Expected result: `success` for the lab as a whole. The C case is expected to make
     gcc report an error; the run script should anticipate it and print gcc's exit
     status and message rather than failing.
   - Output should make visible: the inserted semicolons, flex's tie-breaking and its
     warning text, and gcc's error for `x+++++y` next to the clean compile of
     `x++ + ++y`. Print the flex, gcc and go versions.
