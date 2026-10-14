# Chapter 4 — Grammars and top-down parsing

## 1. Starting point

The reader is Pratham, a 2nd-year CS student whose main language is Go, who also writes C
and Python and is learning Rust. He has built a tree-walking interpreter, so he has
almost certainly written a recursive-descent parser by feel, probably with one function
per precedence level, without knowing the theory that says when that works. He knows sets
and graphs at an intro discrete-math level. He has **not** studied formal grammars, so
"context-free grammar", "derivation", "FIRST" and "FOLLOW" must be built from plain
language up. He prefers guiding questions to finished answers, and dislikes runs of
punchy sentences, stuffed parentheses and heavy semicolons.

From chapter 1 he knows the front/middle/back-end split and built `exprc`, whose parser
used **precedence climbing** (a `precedence(op)` function and an `expression(min int)`
loop) so that `*` binds tighter than `-` and operators group left to right. Chapter 1
explicitly said chapters 3 to 5 "treat both properly", and its self-test asked him to
decide the tree for `8 - 2 - 1`. He has used that algorithm without an explanation of why
it works.

From chapter 3 he knows tokens, token kinds, lexemes, the lexer, maximal munch, regular
expressions, regular languages, NFAs, DFAs, subset construction and lexer generators. He
has the book's Go lexer (`lab/lexer` in chapter 3): identifiers, decimal integers,
keywords `func var if else return`, operators `+ - * / = == != < <= > >= ( ) { } , ;`,
`//` comments, line:column positions, an `ERROR` token. Chapter 3 ended on the limit: no
regular expression matches balanced parentheses nested to any depth, because a finite
automaton cannot count without bound, "and chapter 4 brings in grammars to handle it".
Chapter 3 also said chapter 5 reuses subset construction on parser items.

Glossary terms already defined (do not redefine): compiler, front end, IR, token, token
kind, lexeme, lexer, maximal munch, keyword, regular expression, regular language, NFA,
DFA, ε-transition, subset construction, lexer generator, machine stack, stack frame.

Connections to make explicitly:

- Chapter 3's closing: balanced parentheses are not regular. Open the grammar section by
  answering it: a grammar can refer to itself, and recursion is exactly the unbounded
  memory a DFA lacks.
- `exprc`'s precedence climbing: section 5 shows it is the same algorithm as Pratt
  parsing, now explained.
- His interpreter's parser: the "one function per nonterminal" recursive-descent shape
  he probably wrote is the LL(1) table written as code, the same "hand-written code is the
  automaton in disguise" point chapter 3 made about lexers.
- The chapter 3 lexer feeds this chapter's parser lab.
- Seeds by name: chapter 5 (LR parsing handles left-recursive grammars directly and is
  what bison generates), chapter 6 (the AST this parser builds gets positions, scopes and
  name resolution).

Pitfall to respect (from chapter 2's `pitfalls.md` entry): never use jargon before saying
in plain words what it means. FIRST, FOLLOW, nullable, derivation and binding power each
need a plain-language sentence before the formal definition.

## 2. Crux

**How does a parser recover the tree structure of a token stream, and how can you tell
from the grammar alone whether a simple, left-to-right, one-token-lookahead parser
(recursive descent, or Pratt parsing for expressions) will build the right tree with no
backtracking?**

## 3. Opening situation

Pratham's chapter 3 lexer now hands him tokens, and he wants a parser for the book's
language. He writes the grammar for expressions the way a textbook definition reads:
an expression is a number, a name, or an expression, an operator, and another expression.
Then he feeds it

```
10 - 4 - 3 * 2
```

and notices the grammar does not say which tree to build. Grouped as
`(10 - 4) - (3 * 2)` it is 0, which is what Go and C compute. Grouped as
`10 - (4 - (3 * 2))` it is 12, and as `((10 - 4) - 3) * 2` it is 6. The grammar accepts
the line under every grouping, so the grammar alone cannot be the specification. He fixes
it the obvious way, writing `Expr → Expr - Term`, turns that rule into a Go function whose
first act is to call itself, and the program dies with a stack overflow before reading a
single token. He wants to know how to write a grammar that pins down exactly one tree, how
to tell whether a straightforward recursive-descent parser for it will work, and why the
precedence loop in `exprc` gets the right answer.

## 4. Sections

Budgets sum to 3200, inside the chapter's 2500 to 3500 range.

1. **Why tokens need a grammar** (~500 words)
   Answer chapter 3's balanced-parentheses question: a rule that mentions itself can
   nest without bound. Plain language first, then the formal pieces: terminals (token
   kinds), nonterminals, productions, a start symbol. A derivation as repeatedly
   replacing a nonterminal by one of its right-hand sides, leftmost and rightmost
   derivations, and the parse tree as the derivation with the order forgotten. Write a
   tiny grammar for the book's expressions and derive `10 - 4 - 3 * 2`. History in two
   sentences: Chomsky's context-free grammars, Backus and Naur's notation for ALGOL. Show
   the Go spec's own EBNF notation as a real grammar he has read without knowing it.
   Ground in S7, S72 and scout batch 1.

2. **Ambiguity** (~450 words)
   Ask the reader to draw two trees for `10 - 4 - 3 * 2` before showing them. A grammar
   is ambiguous when one sentence has two parse trees (equivalently two leftmost
   derivations), and since the compiler gives meaning by walking the tree, two trees mean
   two meanings. Use the `grammar-lab` count of trees and their values. The dangling
   `else` as the classic statement-level case, how C resolves it by rule and how Go's
   mandatory braces sidestep it. Ambiguity cannot be detected by an algorithm in general,
   so grammar designers avoid it by construction. Ground in S7, S72, S91 and scout batch 1.

3. **Encoding precedence and associativity, and the left-recursion trap** (~500 words)
   Precedence by layering one nonterminal per level (`Expr`, `Term`, `Factor`), so a
   lower-precedence operator can only appear above a higher one in the tree.
   Associativity by which side the recursion is on: left recursion groups left, right
   recursion groups right. Then the trap from the opening: a top-down parser for
   `Expr → Expr - Term` calls itself without consuming input; show the `left-recursion`
   lab's crash output. The fix: rewrite `A → A α | β` as `A → β A'`, `A' → α A' | ε`,
   which accepts the same strings, and note that it builds a right-leaning tree, so the
   parser must rebuild left associativity, which in hand code is simply a `for` loop.
   Show the lab's fixed version. Ground in S7 and scout batch 2.

4. **LL(1): knowing which rule to pick** (~750 words)
   The predictive-parsing question: standing at a nonterminal with one token of
   lookahead, which production do I expand? Plain language, then FIRST (the tokens a
   string of symbols can start with), nullable (can derive nothing), FOLLOW (the tokens
   that can come right after a nonterminal), and the LL(1) condition built from them
   (EaC's FIRST+). Spell out what LL(1) stands for. Compute the sets for the rewritten
   expression grammar with the reader, predicting entries before showing the
   `grammar-lab` output, then the parse table and a short excerpt of the table-driven
   trace on `10 - 4 - 3 * 2`. Show the conflicts the lab reports for the left-recursive
   grammar, and left factoring for common prefixes. Then recursive descent: one function
   per nonterminal, a `switch` on the lookahead token as that nonterminal's table row, the
   machine stack replacing the explicit stack. Ground in S7 and scout batch 2.

5. **Pratt parsing for expressions** (~600 words)
   Why a separate technique: a grammar with ten precedence levels needs ten nonterminals
   and ten nested calls per number. Pratt's idea: give each operator a binding power, and
   parse with one loop that keeps absorbing operators while they bind more tightly than
   the current minimum. Pratt's terms (nud for a token that starts an expression, led for
   one that continues it), prefix minus, and how the left/right binding powers choose
   associativity. Walk the `parser` lab's trace on `10 - 4 - 3 * 2`. Then the reveal:
   `exprc`'s `expression(min)` loop from chapter 1 is this algorithm, which is why it
   worked (precedence climbing and Pratt parsing being the same algorithm). History in
   two sentences: Pratt 1973, rediscovered and popularized decades later. Production
   compilers: hand-written recursive descent with precedence-driven expression parsing
   in Go's compiler, GCC, clang and rustc, as the scouts confirm. Ground in S6 and scout
   batches 3 and 4.

6. **Your parser** (~400 words)
   Walk the `parser` lab: recursive descent for statements and Pratt for expressions, on
   top of chapter 3's lexer, printing trees as S-expressions for the running example and
   the chapter 3 line `if x1 <= 10 { y = x1 * 2 }`, plus its error message with a
   position. Compare its tree for the running example with `go/parser`'s. Close with the
   open threads: what a parser does after the first error (chapter 5), why bottom-up LR
   parsers accept left-recursive grammars as written (chapter 5), and what the tree
   needs to become a useful AST (chapter 6). No new facts beyond the lab.

## 5. Running example

The expression `10 - 4 - 3 * 2`. Its three readings evaluate to 0, 12 and 6, which makes
ambiguity, precedence and associativity concrete as wrong answers rather than as tree
shapes. It is derived in section 1, drawn as competing trees in section 2, fixed by
layering in section 3, parsed by the LL(1) table in section 4, traced through the Pratt
loop in section 5, and printed by the lab's parser and by `go/parser` in section 6. The
chapter 3 line `if x1 <= 10 { y = x1 * 2 }` is the secondary example for statements and
the dangling-else discussion.

## 6. New terms

grammar (context-free grammar), terminal, nonterminal, production, start symbol,
derivation, leftmost derivation, parse tree, ambiguous grammar, dangling else, precedence,
associativity, left recursion, left factoring, predictive parsing, FIRST set, nullable,
FOLLOW set, LL(1), recursive descent, binding power, Pratt parsing, precedence climbing,
BNF / EBNF.

Excluded as already in the glossary or known: token, token kind, lexeme, lexer, regular
language, DFA, machine stack, stack frame.

## 7. Misconceptions

1. **"If the grammar accepts exactly the right programs, it is correct."** Two grammars
   can accept the same token strings and give different trees, and the tree is the
   meaning. The ambiguous and the layered expression grammars accept the same strings,
   but only one tree evaluates `10 - 4 - 3 * 2` to 0. Likewise, removing left recursion
   keeps the language but changes the tree shape, so associativity must be restored.
2. **"Precedence and associativity are the same idea."** Precedence decides between
   different operators (`-` versus `*`), associativity between repeats of operators at
   the same level (`10 - 4 - 3`). Layering fixes the first and the direction of
   recursion fixes the second, and a Pratt parser needs both a precedence and a rule for
   equal binding powers.

## 8. Fact questions

Pitfalls file has one entry, about explaining jargon in plain words first; it shapes the
writing (see section 1 of this brief) but needs no fact question.

### Batch 1 — Grammars, notation, ambiguity and history (suggest S7 from `library/S7.pdf`, S72, S91; for history search a readable secondary account, e.g. a university course page or encyclopedia entry on BNF and the Chomsky hierarchy)

1. How does Engineering a Compiler (3rd ed., S7) define a context-free grammar (its
   components and notation), a derivation, a sentential form, leftmost and rightmost
   derivations, and a parse tree?
2. How does Engineering a Compiler define an ambiguous grammar, and does it state that
   ambiguity is a property of the grammar rather than the language? Does any reliable
   source state that determining whether an arbitrary context-free grammar is ambiguous
   is undecidable?
3. Who introduced context-free grammars and when (Chomsky, 1956), and how did BNF arise
   (Backus's notation for the ALGOL 58 proposal, Naur's use of it in the ALGOL 60
   report)? Use a readable secondary account.
4. What grammar notation does the Go spec use (EBNF), and what do its `|`, `()`, `[]` and
   `{}` mean there? How does the spec write the `Expression` and `binary_op` productions,
   and does it express precedence in the productions or in a separate table?
5. In the Go spec, how many precedence levels do binary operators have, which operators
   sit at each level, and what does the spec say about the associativity of binary
   operators of equal precedence?
6. The dangling else: how does C resolve it (C11 6.8.4.1, "lexically nearest preceding
   if"), how does Engineering a Compiler present and rewrite the ambiguous if-then-else
   grammar, and does Go's spec require braces around an `if` statement's body?

### Batch 2 — Left recursion and LL(1) (suggest S7 from `library/S7.pdf`; a university lecture page as backup)

7. What transformation does Engineering a Compiler give for eliminating direct left
   recursion (`A → A α | β` into `A → β A'`, `A' → α A' | ε`), and does it also give an
   algorithm for indirect left recursion?
8. How does Engineering a Compiler define FIRST, FOLLOW and FIRST+ (its name for the
   per-production lookahead set), including how ε is handled?
9. What exact condition does Engineering a Compiler give for a grammar to be LL(1)
   (backtrack free), stated with FIRST+ sets?
10. What does each part of the name LL(1) mean (scan direction, kind of derivation,
    lookahead count)?
11. How does Engineering a Compiler define left factoring, and how does it describe the
    table-driven LL(1) skeleton parser (explicit stack, table indexed by nonterminal and
    lookahead)?
12. Can a left-recursive grammar be LL(1) or LL(k), and is every LL(1) grammar
    unambiguous?

### Batch 3 — Pratt parsing and precedence climbing (S6 is not readable online; suggest readable secondary accounts: Bob Nystrom, "Pratt Parsers: Expression Parsing Made Easy" (journal.stuffwithstuff.com, 2011); Alex Kladov, "Simple but Powerful Pratt Parsing" (matklad.github.io, 2020); Andy Chu, "Pratt Parsing and Precedence Climbing Are the Same Algorithm" (oilshell.org, 2016); Theodore Norvell, "Parsing Expressions by Recursive Descent")

13. Where and when did Vaughan Pratt publish "Top Down Operator Precedence", and what
    do his terms nud, led and left binding power mean?
14. Who later popularized Pratt parsing (for example Douglas Crockford's 2007 chapter in
    *Beautiful Code* and JSLint, Nystrom's 2011 post)?
15. How do Pratt parsers achieve left versus right associativity with binding powers
    (for example right-associative operators recursing with a lower minimum, or
    Kladov's pairs of left and right binding powers)?
16. What is precedence climbing, who named or described it (Norvell, Keith Clarke 1986),
    and is it the same algorithm as Pratt parsing per Andy Chu's post?

### Batch 4 — Production parsers and the Go runtime (suggest S30, S81's sibling `src/cmd/compile/internal/syntax/parser.go` at go1.27.1 on raw.githubusercontent.com, S86, S87, GCC release notes on gcc.gnu.org, `runtime/debug` docs on pkg.go.dev)

17. Is the Go compiler's parser (`cmd/compile/internal/syntax/parser.go`) a hand-written
    recursive-descent parser, and how does it parse binary expressions (a function such
    as `binaryExpr` taking a precedence argument, and each operator token carrying its
    precedence)? Quote the relevant comment or code.
18. Which GCC releases replaced the bison-generated C++ and C parsers with hand-written
    recursive-descent parsers (3.4 for C++, 4.1 for C), per the GCC release notes?
19. Is clang's parser hand-written recursive descent, and does its expression parser use
    operator-precedence parsing for binary operators (per the Clang Internals Manual,
    S87, or `clang/lib/Parse/ParseExpr.cpp` comments)?
20. Is rustc's parser (`rustc_parse`) a hand-written recursive-descent parser, per the
    rustc dev guide (S86)?
21. What is the default maximum goroutine stack size on 64-bit systems (per
    `runtime/debug.SetMaxStack`), and what fatal error does the Go runtime print when a
    goroutine exceeds it?

## 9. Lab plan

Runner `local` for all three. Toolchains: go, python3. Each `run.sh` should print short,
quotable sections with clear headers, print tool versions, and the lab notes must give
line ranges of `run.out` for each section. Labs print observations, never conclusions.

1. **`grammar-lab`** — grammar theory as runnable code (Python 3).
   - Demonstrates: (a) ambiguity: for the grammar `E → E + E | E - E | E * E | num`,
     enumerate every parse tree of `10 - 4 - 3 * 2`, printing each tree as a fully
     parenthesized expression and its value, then the number of trees. (b) For the
     left-recursive layered grammar `E → E + T | E - T | T`, `T → T * F | T / F | F`,
     `F → ( E ) | num | id`: compute nullable, FIRST and FOLLOW, build the LL(1) table and
     print the cells with more than one production (the conflicts). (c) Mechanically
     eliminate left recursion, print the rewritten grammar, its nullable, FIRST, FOLLOW
     and FIRST+ sets, and the full LL(1) table (no conflicts). (d) A table-driven
     predictive parse of `10 - 4 - 3 * 2` printing stack, remaining input and action per
     step, compact enough to quote an excerpt.
   - Expected result: `success`.
   - Output should make visible: several trees with different values (0 among them), the
     conflicts caused by left recursion, the clean table after rewriting, and the trace
     ending in accept.

2. **`left-recursion`** — the trap from the opening, in Go.
   - Demonstrates: a naive recursive-descent function written directly from
     `Expr → Expr - Term`, run on `10 - 4 - 3 * 2`, and the fixed version that uses a
     loop and builds a left-leaning tree, printing the tree and its value (0). The naive
     run is expected to crash with the Go runtime's stack overflow; `run.sh` must
     anticipate it, print only the first few lines of the runtime error and the exit
     status, and then run the fixed version. Keep both functions short enough to quote.
   - Expected result: `success` for the lab as a whole (the crash is captured, as the
     chapter 3 `real-lexers` lab captured gcc's error).
   - Output should make visible: the runtime's stack-overflow message and the depth or
     limit it reports, then the fixed parser's tree `((10 - 4) - (3 * 2))` and value 0.

3. **`parser`** — the book's parser in Go, on top of chapter 3's lexer.
   - Demonstrates: copy chapter 3's `lab/lexer/main.go` lexer unchanged (it lives at
     `topics/compilers/chapters/03-lexing/lab/lexer/main.go`) and add a parser: recursive
     descent for statements (`func` declarations with parameters, `var`, assignment,
     `if`/`else` with mandatory braces, `return`, blocks, expression statements, `;`
     separators as the lexer provides them) and a Pratt loop for expressions with a
     binding-power table covering `==`, `!=`, `<`, `<=`, `>`, `>=`, `+`, `-`, `*`, `/`,
     prefix `-`, parentheses and calls `f(a, b)`. Parse errors report `line:col` and what
     was expected, without panicking. Keep the Pratt core short enough to quote (aim
     under 40 lines for the expression parser). Print: (a) a trace of the Pratt loop on
     `10 - 4 - 3 * 2` showing, at each operator, its binding power, the current minimum,
     and whether the loop absorbs it or returns; (b) the S-expression trees for
     `10 - 4 - 3 * 2`, `-2 * 3`, `a < b == c`, `f(1, 2 + 3) * 4`, and for the statement
     `if x1 <= 10 { y = x1 * 2 }`, plus a short `func` with `if`/`else` and `return`;
     (c) the error message for `x = (1 + 2` and for `if x { y = }`; (d) a small Go
     program that parses `10 - 4 - 3 * 2` with `go/parser.ParseExpr` and prints the tree
     in the same S-expression form, so the two parsers can be compared.
   - Expected result: `success`.
   - Output should make visible: the binding-power decisions in the trace, the
     left-leaning `-` tree with `*` nested below it, prefix minus binding tighter than
     `*`, the statement tree, positioned error messages, and `go/parser` agreeing with
     the lab parser.
