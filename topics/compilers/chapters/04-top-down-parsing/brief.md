# Chapter 4 — Grammars and top-down parsing

## 1. Starting point

The reader is Pratham, a 2nd-year CS student whose main language is Go, who also writes C
and Python and is learning Rust. He has built a tree-walking interpreter, so he has
written some parser by feel, but we do not know which technique, and the chapter must not
assume one. He is comfortable with set notation, big-O and recursion in code. His
self-check of 2026-10-16 (profile) says he does **not** know context-free grammars,
ambiguity, left recursion, FIRST/FOLLOW, pushdown automata or the Chomsky hierarchy. He
has no graph theory beyond the states and arrows chapter 3 built by hand, no proof by
induction, and has never seen "propagating values until nothing changes", which is
exactly how FIRST and FOLLOW sets are computed. Each of these is either taught here from
plain language with a hand trace, or avoided. Trees he knows as a data structure, from his
interpreter and from chapter 1's drawn tree, so root, child and leaf can be used in that
sense with at most a passing gloss. He prefers plain language first, then step-by-step
depth, and guiding questions over finished answers. He dislikes runs of short punchy
sentences, stuffed parentheses and heavy semicolons.

From chapter 1 he knows the front/middle/back-end split and built `exprc`, which has a
lexer, a parser and a code generator. Its parser is **precedence climbing**: `precedence`
returns 1 for `+ -` and 2 for `* /` (0 for anything else), and `expression(min)` reads one
operand, then keeps absorbing operators while `precedence(op) >= min`, parsing each right
operand with `expression(precedence(op) + 1)` (`01-what-a-compiler-does/lab/exprc/main.go`
lines 59–92). Chapter 1 said only that this makes `*` bind tighter than `-` and makes
operators group left to right, and that chapters 3 to 5 treat parsing properly. Chapter 1
drew the tree for `(7 + 5) * 3 - 6` with `-` at the root, said the evaluator and the
compiler both walk that same tree, and its tryit asked for the tree of `8 - 2 - 1`.

From chapter 2 he knows the machine stack, stack frames, and that `call` pushes a return
address. He traced `fact(5)` and saw five frames 32 bytes apart, so he can picture a
recursive function's frames piling up until something stops them.

From chapter 3 he knows tokens, token kinds and lexemes, and has the book's Go lexer
(`03-lexing/lab/lexer/main.go`): IDENT, INT, keywords `func var if else return`, operators
and punctuation `+ - * / = == != < <= > >= ( ) { } , ;`, `//` comments, line:column
positions, ERROR and EOF tokens, and no semicolon insertion. He knows maximal munch,
regular expressions, finite automata with states, transitions and accepting states built
by hand, NFAs, DFAs and the subset construction, and that a hand-written lexer's `switch`
is the DFA's transition function written as code. Chapter 3 ended on its limit: no regular
expression matches balanced parentheses nested to any depth, because a finite automaton
has to count the open parentheses and can only count so high, "and chapter 4 brings in
grammars to handle it". It also said chapter 5 reuses the subset construction on parser
items.

Glossary terms already defined (do not re-mark): compiler, front end, intermediate
representation, stack-machine code generation, machine stack, stack frame, return address,
token, token kind, lexeme, lexer, keyword, maximal munch, regular expression, regular
language, finite automaton, state, transition, accepting state, NFA, DFA, ε-transition,
subset construction. Note that **parser** is not in the glossary yet.

Connections to make explicitly:

- Chapter 3's closing question. A grammar rule may mention itself inside parentheses
  (`Factor → ( Expr )`), so it nests to any depth. Answer the question in the grammar
  section.
- Chapter 3's tokens are the grammar's terminals, and chapter 3's lexer feeds this
  chapter's parser lab unchanged.
- Chapter 1's tree and its two walkers. The operator at the root is applied last, so the
  shape of the tree is the meaning, and two trees for one input are two meanings.
- Chapter 1's `exprc` loop is precedence climbing, the same algorithm as Pratt parsing.
  Section 8 explains at last why `precedence(op) + 1` makes `-` group to the left.
- Chapter 2's stack. A recursive-descent function written straight from a left-recursive
  rule calls itself before reading a token, and its frames pile up until the goroutine's
  stack limit kills it. In a recursive-descent parser, each open `(` or `{` is a frame
  still waiting for its `)` or `}`. Say this about recursive descent only, not about all
  parsers.
- Chapter 3's "the lexer's `switch` is the DFA written by hand" has a twin here: the
  parser's `switch` on the lookahead token is one row of the LL(1) table.
- Seeds by name, one sentence each: chapter 5 (bottom-up LR parsing, which accepts
  left-recursive grammars as written, plus error recovery and why production compilers
  hand-write parsers), chapter 6 (the tree becomes an AST with scopes), and chapter 11
  (dataflow analysis uses the same repeat-until-nothing-changes computation as FIRST and
  FOLLOW).

Pitfalls that shape this chapter (`pitfalls.md`):

- 2026-10-14, chapter 4: an earlier version talked about parse trees and never drew one.
  Draw the parse trees for `10 - 4 - 3 * 2`, at least the tree worth 0 (second `-` at the
  root, `*` low on the right) and the tree worth 6 (`*` at the root), with small node
  `width`/`height` so the SVG fits the column. Each `E` node's children are the right side
  of the production that rewrote it, and leaves are tokens. The diagram plans below cover
  this.
- 2026-10-16, chapter 3: never assume a mental model because its terms were defined.
  Establish each mechanism (rewriting, derivations, choosing a rule by lookahead, the
  repeated passes that compute FIRST and FOLLOW, the Pratt loop) with a hand trace on the
  running example before any algorithm or code, and make the later algorithm and lab
  output reuse the same example and numbers.
- 2026-10-13, chapter 2: say in plain words what a thing does before naming it.

## 2. Crux

**How do we write down a language's syntax precisely enough that every program has
exactly one tree, and how does a parser that reads tokens left to right, looking one token
ahead, build that tree without ever guessing?**

## 3. Opening situation

Pratham's chapter 3 lexer turns `10 - 4 - 3 * 2` into seven tokens and EOF, a flat list.
To compute or compile it, as chapter 1 showed, he needs a tree, and the tree is not in the
tokens. Grouped five different ways the same seven tokens give five answers:
`((10 - 4) - 3) * 2` is 6, `(10 - (4 - 3)) * 2` is 18, `(10 - 4) - (3 * 2)` is 0,
`10 - ((4 - 3) * 2)` is 8, and `10 - (4 - (3 * 2))` is 12. Go and C both say 0. `exprc`'s
precedence loop also gets 0, but nobody has said why that loop is right, and it only
handles arithmetic. The book's language needs `if` statements and blocks nested inside
blocks to any depth, which chapter 3 showed no regular expression can describe. He wants a
way to write down the syntax that pins down one tree per program, and a way to be sure the
parser he writes in Go follows it. By the end he can write a grammar, see ambiguity, layer
precedence and associativity into rules, remove left recursion, compute FIRST and FOLLOW
by hand, build an LL(1) table, write a recursive-descent parser, and parse expressions
with a Pratt loop.

## 4. Sections

Budgets sum to 4550, inside the chapter's 3600 to 4800 range (raised from 2500 to 3500,
because the reader starts with no grammar background and the repeated-pass computation
must be taught from scratch). Already cut as lower value: the full table-driven LL(1) parse
trace (an optional short excerpt only), left factoring (a self-test question only), the
Chomsky hierarchy, pushdown automata, undecidability results, and production parser
history and error recovery (chapter 5).

0. **Opening and crux** (~250 words)
   The opening situation above. Ask, as a guiding question, how his interpreter's parser
   decided. Ground the "Go and C both say 0" claim in batch 2 (Go precedence and left
   associativity) and batch 1 (C's expression grammar).

1. **Rules that can nest: grammars and derivations** (~650 words)
   Point: a grammar is a set of rewriting rules, and repeatedly rewriting from a start
   symbol produces exactly the programs of the language. Plain words first: a
   production says "this kind of phrase may be written as this sequence", terminals are
   chapter 3's token kinds, nonterminals name kinds of phrases, and one is the start
   symbol. Teach rewriting by doing it. Use `E → E - E | E * E | ( E ) | num`, and trace a
   leftmost derivation of `10 - 4 - 3 * 2` one rewrite per line (from the `grammar` lab's
   printout of the derivation that yields the tree worth 0). Then the parse tree as the
   record of which production rewrote which `E`, which forgets the order of the rewrites.
   Answer chapter 3's question here: the `( E )` alternative mentions `E` inside
   parentheses, so `((7))` is just two more rewrites, and nesting needs no counting
   states. Then the notation he already reads: Go's spec writes its grammar in EBNF; show
   one real production, `Block` or `IfStmt`, and say what `[ ]`, `{ }`, `|` mean. History
   in at most two sentences: Chomsky's context-free grammars, and Backus and Naur's
   notation for ALGOL 60. Say in one plain sentence why "context-free".
   Builds on: tokens and token kinds (chapter 3), the drawn expression tree (chapter 1),
   the balanced-parentheses limit (chapter 3). All grammar mechanics are new and taught
   here.
   Diagram plan: **Figure A**, the parse tree worth 0 for `10 - 4 - 3 * 2` under this
   grammar, generated by the `grammar` lab as `lab/grammar/out/tree-0.dot` and included
   with `include=`. It shows the root `E` with children `E - E`, the left `E` holding
   `10 - 4` and the right `E` holding `3 * 2`, leaves labelled by token. The prose must
   still say which production each `E` used, point at the right subtree where `*` sits
   low, and say that the operator under the root is applied last.
   Sources: S7 (EaC §3.2), S72, batch 1 and batch 2.

2. **One list of tokens, five trees: ambiguity** (~450 words)
   Point: when one token string has two trees, the grammar gives it two meanings, and
   that is a defect of the grammar. Ask the reader to find a second derivation that
   starts by rewriting `E` with `E * E`, then show **Figure B**, the tree worth 6, and the
   lab's list of all five trees with their values (6, 18, 0, 8, 12 in whatever order the
   lab prints). Define an ambiguous grammar (more than one leftmost derivation, or
   parse tree, for some sentence). Then the classic statement-level case, the dangling
   `else` in C's `if (a) if (b) s1; else s2;`, how the C standard settles it by a rule
   outside the grammar, and how Go's grammar avoids it by requiring a block with braces
   after `if`.
   Builds on: section 1's derivations and parse trees; chapter 1's point that walkers
   give meaning by walking the tree.
   Diagram plan: **Figure B**, the tree worth 6, generated as
   `lab/grammar/out/tree-6.dot`, drawn the same way as Figure A so the two compare at a
   glance. The prose points at the root, `*` in Figure B and the second `-` in Figure A,
   and connects it to the values.
   Sources: S7, S91, S72, batch 1, the `grammar` lab.

3. **Writing precedence and associativity into the grammar** (~450 words)
   Point: give each precedence level its own nonterminal, and put the recursion on the
   side the operators should group toward. Layered grammar:
   `Expr → Expr - Term | Term`, `Term → Term * Factor | Factor`,
   `Factor → ( Expr ) | num`. Walk through why, without parentheses, a `*` can only
   appear inside a `Term`, below any `-`, and why only the left operand of `-` can itself
   be a `-` expression without parentheses, which is left associativity. Be exact: with
   parentheses, a `-` can sit below a `*`, as in `(10 - 4) * 3`. Show the lab's count of
   one tree for the running example. Then the real-world contrast: the C standard writes
   exactly this layering for its additive and multiplicative expressions, while Go's spec
   writes the ambiguous `Expression binary_op Expression` and settles it with a separate
   precedence table of five levels, the approach section 8 implements. Place
   misconception 2 here, using the `eval-order` lab.
   Builds on: sections 1 and 2.
   Diagram plan: **Figure C**, the parse tree of `10 - 4 - 3 * 2` under the layered
   grammar, generated as `lab/grammar/out/layered.dot`. The prose points at the left
   spine of `Expr` nodes, which is the left grouping of the two `-`, at the `Term` under
   the root's right side that holds `3 * 2`, and at the chains like
   `Term → Factor → num` that carry no operator.
   Sources: S7 (§3.2.4), S91, S72, batch 1 and batch 2, the `grammar` and `eval-order` labs.

4. **The rule that calls itself first: left recursion** (~450 words)
   Point: a top-down parser cannot use a left-recursive rule as written, and the fix
   keeps the strings but changes the tree's shape, which the code must put back.
   Plain words for "top-down" first: the parser starts at the root and decides which
   rule to use before reading the tokens the rule covers. Turn `Expr → Expr - Term`
   straight into a Go function. Its first act is to call itself, having read nothing,
   so the call repeats forever and each call pushes a frame (chapter 2) until the
   goroutine's stack limit stops the program. Show the `left-recursion` lab's runtime
   error and exit status. Then the transformation `A → A α | β` into `A → β A'`,
   `A' → α A' | ε`, defining the same language, applied to `Expr` and `Term`, giving the
   five-nonterminal grammar the next two sections use. Show that the `Expr'` tail builds a
   right-leaning parse tree, and that in code the tail becomes a `for` loop that folds to
   the left, which is the EBNF `Expr = Term { "-" Term }`. Show the lab's fixed function
   and its tree and value 0, and connect it to `exprc`'s loop. One sentence seeds
   chapter 5: an LR parser generator can use left recursion directly. Place
   misconception 1 here.
   Builds on: section 3's grammar, chapter 2's frames.
   Diagram plan: **Figure D** (optional, drop it if the prose is clearer alone), two
   clusters for `10 - 4 - 3`: the parse tree under the subtraction-only grammar
   `E → num E'`, `E' → - num E' | ε`, leaning right, and the tree the loop builds,
   `(10 - 4) - 3`, leaning left. Generated as `lab/grammar/out/rewritten.dot`. The prose
   must state that this figure uses the subtraction-only grammar, and point at where the
   first `-` sits in each.
   Sources: S7 (§3.3.1, §5.7.1), batch 3, batch 5 (Go stack limit), the
   `left-recursion` and `grammar` labs.

5. **What can come first: FIRST sets** (~500 words)
   Point: a top-down parser picks a rule by looking at one token, and the tokens that
   can start each alternative tell it which. Mechanism first. In the statement grammar
   (`Stmt` alternatives starting with `var`, `if`, `return`, `{` and IDENT) each
   alternative begins with a different token, so one token of lookahead decides at once.
   In the rewritten expression grammar the choice for `Expr'` is between `- Term Expr'`
   and nothing at all, so the parser needs to know which tokens can begin a phrase.
   Define FIRST in plain words, with ε as a marker meaning "can be empty", which is EaC's
   convention. Then compute FIRST for the five nonterminals by hand, pass by pass,
   exactly as the lab prints it (in-place updates in grammar order, below). Show why one
   pass is not enough (`Expr` depends on `Term`, which is filled in later), why it
   stops (sets only grow, and there are only six tokens to add), and only then name this
   repeat-until-nothing-changes pattern, with the seed for chapter 11.
   Expected pass table, a cross-check for the writer (the lab output is authoritative):
   pass 1 gives Expr {}, Expr' {-, ε}, Term {}, Term' {*, ε}, Factor {(, num}. Pass 2
   gives Term {(, num}. Pass 3 gives Expr {(, num}. Pass 4 changes nothing.
   Builds on: section 4's rewritten grammar; set notation (profile). The iteration is new
   and traced here.
   No diagram: a pass table carries it.
   Sources: S7 (§3.3.1, Fig. 3.7), batch 3, the `grammar` lab.

6. **What can come next: FOLLOW sets, START sets and the LL(1) table** (~500 words)
   Point: when an alternative can be empty, the parser chooses it by looking at what may
   follow, and a grammar is LL(1) when these choices never overlap. FOLLOW in plain words,
   with `eof`, computed with the same repeated passes (a shorter trace, ending at
   FOLLOW(Expr) = {eof, )}, FOLLOW(Expr') = {eof, )}, FOLLOW(Term) = FOLLOW(Term') =
   {-, eof, )}, FOLLOW(Factor) = {*, -, eof, )}). Then EaC's START set per production
   (FIRST of the right side, plus FOLLOW of the left side when the right side can be
   empty), the backtrack-free condition (each nonterminal's START sets are disjoint), and
   what LL(1) stands for. Show the LL(1) table from the lab, rows nonterminals and
   columns `num - * ( ) eof`, with every cell holding at most one production. Then the
   left-recursive grammar of section 3 through the same machine: the lab reports cells
   with two productions, which is what left recursion always does to this table. An
   optional excerpt of the lab's table-driven parse, if budget allows, connecting the
   explicit stack to chapter 2.
   Builds on: section 5. Use the course textbook's names (EaC 3rd ed.: FIRST, FOLLOW,
   START, backtrack-free) and say that the 2nd edition called START sets FIRST+ only if
   batch 3 confirms it.
   No diagram: tables.
   Sources: S7 (§3.3.1), batch 3, the `grammar` lab.

7. **Recursive descent: the table as Go code** (~400 words)
   Point: write one function per nonterminal, and each function's `switch` on the
   lookahead token is its row of the LL(1) table. Show the `parser` lab's `parseStmt`
   (include) and its decisions on `if x1 <= 10 { y = x1 * 2; }`, the chapter 3 line with
   the `;` our language needs because it has no semicolon insertion. Make the twin of
   chapter 3's point explicit. When the lookahead is in no START set, the parser knows
   exactly what it expected, which gives positioned error messages; show the lab's two
   error lines. Each open `{` or `(` is a frame on the machine stack waiting for its
   closer, which is the unbounded memory chapter 3's DFA lacked. Go's own compiler
   parses this way: its parser in `cmd/compile/internal/syntax` is hand-written
   recursive descent. Leave the reasons production compilers hand-write parsers, and
   error recovery, to chapter 5 in one sentence.
   Builds on: sections 5 and 6, chapter 2's frames, chapter 3's lexer.
   No diagram: the code and the table already show the correspondence.
   Sources: S7 (§3.3.2), batch 3, batch 5, the `parser` lab.

8. **Pratt parsing: one loop for every precedence level** (~650 words)
   Point: instead of one function per precedence level, give each operator a binding
   power and parse every level with one loop. Motivate it with Go's five binary levels
   (section 3): the layered approach needs a function per level, and parsing a lone `x`
   passes through every one. Pratt's 1973 idea in plain words, then his names: a
   token that starts an expression (nud) and one that continues an expression with a
   left operand already in hand (led). Trace the loop by hand on `10 - 4 - 3 * 2` with the
   lab's binding powers, Go's levels (`-` is 4, `*` is 5, non-operators 0, outer call
   with minimum 1), using the lab's printed trace (four calls, minimums 1, 5, 5, 6). Show
   why left grouping falls out (the right operand of `-` is parsed with minimum 5, so the
   next `-` at 4 stops it and the outer loop takes it), and why `*` joins the right
   operand (5 ≥ 5). Then prefix `-` (operand parsed with minimum 6, above every binary
   level, since Go gives unary operators the highest precedence) with the lab's
   `(* (neg 2) 3)`, and right associativity in one sentence: parse the right operand with
   the operator's own power instead of one more. Show the lab's Pratt core (include).
   Then the reveal: chapter 1's `exprc` loop is the same algorithm, called precedence
   climbing, and Andy Chu's post argues the two are the same algorithm. Pratt and
   Crockford write the test as a strict `<` against a right binding power; the lab uses
   `exprc`'s `>=` against a minimum. Say that this is bookkeeping, not a different
   algorithm, only if batch 4 supports it. Production use: Go's parser handles binary
   expressions with a function that takes a precedence (batch 5), and `go/parser` in
   the lab gives the same tree as ours. Optionally clang's `ParseRHSOfBinaryExpression`.
   Builds on: sections 3 and 7, chapter 1's `exprc`.
   No diagram: the lab's trace table is the step-by-step view. Refer back to Figure A
   for the result.
   Sources: S6 (via its readable transcription), batch 4, batch 5, the `parser` lab.

9. **Check yourself** (~250 words of questions)
   Questions that need thinking, at least one predicting an unshown case. Suggested: (a)
   the C-style dangling-else grammar `Stmt → if ( E ) Stmt Else | other`,
   `Else → else Stmt | ε`: compute START for `Else`'s two productions, find the
   conflicting cell, and say which choice gives C's rule; (b) adding call statements
   `f(x);` next to `x = e;` makes two `Stmt` alternatives start with IDENT: what goes
   wrong in the table, and how would you rewrite the rules (left factoring, answered in
   the answers only); (c) hand-trace the Pratt loop on `1 - 2 * 3 - 4` and on `-2 * 3`;
   (d) if `-` were made right-associative by changing one number in the lab, what tree
   and value would `10 - 4 - 3` give; (e) why does the naive left-recursive parser crash
   even on input `7`? Tryit blocks should ask for hand work first, then a lab run, and
   must not require lexer changes the reader is not told about (the lexer has no `%`,
   `&&` or `||`).

## 5. Running example

`10 - 4 - 3 * 2`. It has two `-`, which exposes associativity, and a `*`, which exposes
precedence, and its five groupings evaluate to 6, 18, 0, 8 and 12, so ambiguity shows up
as wrong answers rather than abstract shapes. It is derived in section 1 (Figure A),
shown as competing trees in section 2 (Figure B and the lab's list), fixed by layering in
section 3 (Figure C), parsed by the naive and fixed functions in section 4, used for the
FIRST, FOLLOW and table work in sections 5 and 6, and traced through the Pratt loop and
compared with `go/parser` in section 8. The statement `if x1 <= 10 { y = x1 * 2; }`,
chapter 3's line with a `;` added, is the secondary example for statements, LL(1) choices
and recursive descent in sections 5 and 7.

## 6. New terms

parser, context-free grammar, terminal, nonterminal, production, start symbol,
derivation, sentential form (optional, "each line of a derivation" may do), leftmost
derivation, parse tree, ambiguous grammar, dangling else, precedence, associativity, BNF,
EBNF, top-down parser, left recursion, recursive descent, lookahead, FIRST set, FOLLOW
set, START set, backtrack-free grammar, LL(1), fixed point (optional, named only after
the hand trace), binding power, Pratt parsing, precedence climbing.

Excluded as already in the glossary or known: token, token kind, lexeme, lexer, regular
language, finite automaton, state, DFA, machine stack, stack frame, return address, set
notation.

## 7. Misconceptions

1. **"If my grammar accepts exactly the right programs, it is a correct grammar."** The
   tree is the meaning, and two grammars can accept the same token strings with different
   trees. The ambiguous and the layered grammars accept the same expressions, but only
   one tree makes `10 - 4 - 3 * 2` worth 0. Removing left recursion keeps the strings and
   changes the tree's shape, which is why the parser's loop must rebuild left grouping.
2. **"Higher precedence means that operation is computed first."** Precedence decides
   the shape of the tree, which operands belong to which operator. The order in which
   operands are evaluated is a separate rule. In Go, `f() - g() * h()` groups `g() * h()`
   under the `-`, yet the calls run in the order f, g, h, because the spec evaluates
   function calls in lexical left-to-right order. The `eval-order` lab shows it.

## 8. Fact questions

The pitfalls entry for chapter 4 concerns drawing trees and needs no fact (its values are
arithmetic and lab output). The others shape the writing (section 1 of this brief).

### Batch 1 — Grammars, derivations, ambiguity, C's grammar, history (suggest S7 via its library copy, fetch `S7`; S91 for C11; a readable secondary account for history, such as the Wikipedia pages "Context-free grammar" and "Backus–Naur form", or the Revised Report on ALGOL 60 at masswerk.at)

1. How does Engineering a Compiler, 3rd ed. (S7), define a context-free grammar (its
   parts: terminals, nonterminals, productions, start symbol) and the BNF notation it
   uses? Does it state that regular expressions cannot describe balanced parentheses, or
   otherwise motivate grammars by a limit of regular languages?
2. How does S7 define a derivation, a sentential form, a leftmost derivation and a parse
   tree, and how does it relate a parse tree to derivations?
3. How does S7 define an ambiguous grammar?
4. How does S7 present the if-then-else (dangling else) ambiguity, and what exactly does
   C11 §6.8.4.1 say about which `if` an `else` belongs to?
5. How does C11 (N1570 §6.5.5 and §6.5.6) write the productions for
   multiplicative-expression and additive-expression, and what does the §6.5 footnote
   say about how the syntax specifies operator precedence?
6. History: who introduced context-free grammars and when (Chomsky, 1956), and how did
   BNF arise (Backus's notation, Naur's use of it in the ALGOL 60 report)? Why are these
   grammars called context-free (the left side of each rule is a single nonterminal that
   can be rewritten regardless of what surrounds it)?

### Batch 2 — The Go specification (suggest S72, https://go.dev/ref/spec, language version go1.27)

7. Which notation does the Go spec use for its grammar, and what do `|`, `()`, `[]` and
   `{}` mean in it? Quote the Notation section.
8. How does the spec write the `Block` and `IfStmt` productions, showing that an `if`
   body must be a block with braces?
9. How many precedence levels do Go's binary operators have, which operators sit at
   each level, what does the spec say about the precedence of unary operators, and what
   does it say about the associativity of binary operators of the same precedence
   (including its example, if it gives one)?
10. How does the spec write the `Expression` production (`Expression = UnaryExpr |
    Expression binary_op Expression .`), so that precedence comes from the separate
    table rather than from the productions?
11. What does the spec say about the order in which the operands of an expression are
    evaluated: are function calls evaluated in lexical left-to-right order?

### Batch 3 — Top-down parsing in Engineering a Compiler (suggest S7 via its library copy, fetch `S7`, §3.2.4, §3.3, §5.7.1; S32 for the 2nd edition's FIRST+ name)

12. How does S7 show that the classic expression grammar encodes precedence (§3.2.4,
    "Encoding Meaning into Structure"), and what does it say about recursion and
    associativity (§5.7.1), including that an LR(1) parser generator can use either left
    or right recursion?
13. What does S7 say happens when a top-down parser uses a left-recursive grammar, what
    transformation does it give for direct left recursion (`Fee → Fee α | β` into
    `Fee → β Fee'`, `Fee' → α Fee' | ε`), and does it say the new grammar defines the
    same language?
14. How does S7 define FIRST (including how ε is handled), FOLLOW (including `eof`) and
    START, giving START's exact formula? Did the 2nd edition (S32) call the same set
    FIRST+?
15. How does S7's algorithm compute FIRST sets (Fig. 3.7): does it repeat until the
    sets stop changing, and does the book say why it terminates?
16. What is S7's condition for a backtrack-free grammar in terms of START sets, and how
    does it explain the name LL(1)?
17. How does S7 describe a recursive-descent parser (one procedure per nonterminal)
    and the table-driven LL(1) skeleton parser (an explicit stack and a table indexed by
    nonterminal and lookahead word)?

### Batch 4 — Pratt parsing and precedence climbing (S6 is not readable at dl.acm.org; suggest the transcription of Pratt's paper at https://tdop.github.io/, Crockford's "Top Down Operator Precedence" at https://crockford.com/javascript/tdop/tdop.html, Kladov's https://matklad.github.io/2020/04/13/simple-but-powerful-pratt-parsing.html, Andy Chu's https://www.oilshell.org/blog/2016/11/01.html, Norvell's https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm)

18. Where and when did Vaughan Pratt publish "Top Down Operator Precedence", and what do
    his terms nud (null denotation), led (left denotation) and binding power mean? Does
    the method attach parsing behavior to tokens rather than to grammar rules?
19. How does a Pratt parser get left versus right associativity from binding powers
    (for example Crockford's `expression(bp)` for left-associative infix operators and
    `expression(bp - 1)` for right-associative ones with a `while (rbp < token.lbp)`
    loop, or Kladov's pairs of left and right binding powers)?
20. What is precedence climbing, who first described it (Norvell credits Keith Clarke,
    1986, and Martin Richards), and does Andy Chu's post say precedence climbing and Pratt
    parsing are the same algorithm? Quote his wording.

### Batch 5 — Production parsers and the Go runtime (suggest raw.githubusercontent.com at tag go1.27.1 for `src/cmd/compile/internal/syntax/parser.go`, `src/go/parser/parser.go` and `src/runtime/stack.go`; https://pkg.go.dev/runtime/debug and https://pkg.go.dev/go/parser; clang at llvmorg-18.1.8 `clang/lib/Parse/ParseExpr.cpp`)

21. Is the Go compiler's parser (`cmd/compile/internal/syntax/parser.go`, go1.27.1)
    hand-written recursive descent? Quote a comment or function that shows a grammar
    production implemented by a function, and quote how it parses binary expressions (a
    function such as `binaryExpr(x Expr, prec int)` that takes a precedence).
22. What does `go/parser.ParseExpr` do and return, and how does `go/parser` parse
    binary expressions (for example `parseBinaryExpr` with a precedence argument)?
23. Does clang's `ParseExpr.cpp` (llvmorg-18.1.8) describe parsing binary expressions
    by operator precedence, for example `ParseRHSOfBinaryExpression` with a minimum
    precedence? Quote the comment.
24. What is the default maximum goroutine stack size on 64-bit systems (per
    `runtime/debug.SetMaxStack`), and what message does the Go runtime print when a
    goroutine exceeds it (`runtime/stack.go`)?

## 9. Lab plan

Topic lab profile: runner `local`; labs grow one Go compiler across the book; theory
chapters use small Python or Go programs that compute and print the structures. All four
labs below use runner `local`, no network. Each `run.sh` prints the tool version, then
short sections with clear `==` headers. Labs print observations, never conclusions, and
`NOTES.md` gives the `run.out` line range and the source line ranges for each section.
Generated `.dot` files must set no colors or fonts (the renderer themes them), should use
small nodes (for example `node [width=0.3, height=0.3, fontsize=11]`), and need
`ordering=out` so children keep their left-to-right order.

1. **`grammar`** — grammar theory as runnable code (Python 3, expect `success`).
   - Grammars. G1 is `E → E - E | E * E | ( E ) | num`. G2 is the layered left-recursive
     `Expr → Expr - Term | Term`, `Term → Term * Factor | Factor`,
     `Factor → ( Expr ) | num`. G3 is G2 after left-recursion elimination:
     `Expr → Term Expr'`, `Expr' → - Term Expr' | ε`, `Term → Factor Term'`,
     `Term' → * Factor Term' | ε`, `Factor → ( Expr ) | num`, with productions numbered
     1 to 8 in that order. Input: the tokens of `10 - 4 - 3 * 2`.
   - (a) Two leftmost derivations under G1, the one whose tree is worth 0 and the one
     whose tree is worth 6, one sentential form per line with the production applied,
     exactly one nonterminal rewritten per step.
   - (b) Every parse tree of the input under G1, each printed fully parenthesized with
     its value, then the count (expected 5). Write `out/tree-0.dot` and
     `out/tree-6.dot`: full parse trees with `E` nodes and token leaves labelled `10`,
     `-`, `4`, `*` and so on.
   - (c) The count of parse trees under G2 (expected 1), the tree fully parenthesized,
     and `out/layered.dot` with all `Expr`, `Term` and `Factor` nodes.
   - (d) G3 printed as produced by the elimination step.
   - (e) FIRST sets of G3 computed EaC style (ε as a member meaning "can derive the empty
     string"), updating sets in place while processing productions in grammar order,
     printing every nonterminal's set after each pass until a pass changes nothing, with
     the pass count. The brief's expected result is four passes; print what the code
     computes. Then FOLLOW sets the same way (with `eof`, start symbol `Expr`). Then the
     START set of each production by EaC 3rd edition's rule: FIRST(β) if ε is not in it,
     otherwise (FIRST(β) − ε) ∪ FOLLOW(A). Then the LL(1) table, rows `Expr Expr' Term
     Term' Factor` and columns `num - * ( ) eof`, cells holding production numbers.
   - (f) The same START and table construction for G2, printing only the cells that hold
     more than one production.
   - (g) A table-driven predictive parse of the input with G3, one line per step: stack,
     remaining input, action. Keep it compact so a writer can quote the first 8 to 10
     steps.
   - (h) `out/rewritten.dot`: two clusters for `10 - 4 - 3`, the right-leaning parse tree
     under `E → num E'`, `E' → - num E' | ε`, and the left-leaning tree `(10 - 4) - 3`
     that folding the tail in a loop builds.
   - Output should make visible: one-rewrite-per-line derivations, five trees with
     different values including 0, one tree under G2, the FIRST and FOLLOW passes, a
     conflict-free table for G3 and the conflicting cells for G2.

2. **`left-recursion`** — the trap in Go (expect `success` for the lab as a whole).
   - A naive recursive-descent function written straight from `Expr → Expr - Term |
     Term` (its first statement calls itself), run on the tokens of `10 - 4 - 3 * 2`. It
     is expected to crash with the Go runtime's stack overflow. `run.sh` anticipates the
     crash, prints only the deterministic lines of the runtime error (the "goroutine
     stack exceeds ...-byte limit" line and "fatal error: stack overflow", no addresses)
     and the exit status. Prefer the default stack limit. If memory or the timeout
     forbid it, lower it with `debug.SetMaxStack` and make the output show the limit
     used.
   - Then the fixed version: `parseExpr` and `parseTerm` as loops (`Expr = Term { "-"
     Term }`, `Term = Factor { "*" Factor }`) that fold to the left, printing the tree
     `((10 - 4) - (3 * 2))` and its value.
   - Keep the naive and the fixed functions short enough to quote together within about
     25 lines.
   - Output should make visible: the runtime's stack-overflow lines and exit status,
     then the fixed parser's tree and value 0.

3. **`parser`** — the book's parser in Go, on chapter 3's lexer (expect `success`).
   - Copy `topics/compilers/chapters/03-lexing/lab/lexer/main.go` unchanged as
     `lexer.go`. Add a parser that stops at the first syntax error (no recovery, which is
     chapter 5). Statements by recursive descent:
     `Program = { FuncDecl | Stmt }`,
     `FuncDecl = "func" IDENT "(" [ IDENT { "," IDENT } ] ")" Block`,
     `Block = "{" { Stmt } "}"`,
     `Stmt = "var" IDENT "=" Expr ";" | IDENT "=" Expr ";" | "if" Expr Block [ "else" (
     Block | IfStmt ) ] | "return" Expr ";" | Block`.
     Expressions by a Pratt loop in `exprc`'s convention: the loop continues while
     `bp(op) >= min`, left-associative operators parse their right operand with
     `bp + 1`, and the outer call uses minimum 1. Binding powers are Go's precedence
     levels for the operators the lexer has: `== != < <= > >=` 3, `+ -` 4, `* /` 5, and
     any other token 0. Prefix `-` parses its operand with minimum 6. Primaries are INT,
     IDENT, calls `f(a, b)` and `( Expr )`.
   - Output, in this order:
     (a) a Pratt trace of `10 - 4 - 3 * 2`, one line per event (call number, its
     minimum, the operand read, each operator seen with its binding power, and
     absorb or return), under 20 lines;
     (b) S-expression trees for `10 - 4 - 3 * 2`, `-2 * 3`, `a < b == c`,
     `f(1, 2 + 3) * 4` and `10 - (4 - 3) * 2`;
     (c) the recursive-descent decisions for `if x1 <= 10 { y = x1 * 2; }`, one line per
     choice point (function, lookahead token, production chosen), then its tree, then the
     tree of a short function with `if`/`else` and `return`, such as
     `func max(a, b) { if a > b { return a; } else { return b; } }`;
     (d) syntax errors for `x = (1 + 2;` and `if x { y = ; }`, each one line with
     `line:col`, the tokens that were expected (from the START sets at that point) and
     the token found;
     (e) `go/parser.ParseExpr` on `10 - 4 - 3 * 2`, printed in the same S-expression form.
   - Keep `parseStmt` and the Pratt core (binding-power table plus loop) each within 25
     lines, and keep tracing to a one-line hook so the quoted code stays clean.
   - Output should make visible: the binding-power decisions, the left-leaning `-` tree
     with `*` below it, prefix minus binding tighter than `*`, the statement decisions
     and trees, positioned errors, and `go/parser`'s tree beside ours.

4. **`eval-order`** — precedence is not evaluation order (Go, expect `success`).
   - A tiny Go program whose functions `f`, `g`, `h` print their names and return 10, 3
     and 2, and which prints `f() - g() * h()`.
   - Output should make visible: the call order and the value 4.
