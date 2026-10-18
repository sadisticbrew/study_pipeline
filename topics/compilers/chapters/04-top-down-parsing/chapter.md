---
topic: Compilers
chapter: 4
title: Grammars and top-down parsing
---

Your chapter 3 lexer turns `10 - 4 - 3 * 2` into seven tokens and an EOF, and that is all it gives you: a flat list. To compute the answer or compile it, you need the tree from chapter 1, and the tree is nowhere in the tokens. Group the same seven tokens five different ways and you get five answers. `((10 - 4) - 3) * 2` is 6, `(10 - (4 - 3)) * 2` is 18, `(10 - 4) - (3 * 2)` is 0, `10 - ((4 - 3) * 2)` is 8, and `10 - (4 - (3 * 2))` is 12. Go and C both say 0. C gets there because its grammar writes subtraction in terms of multiplication [@F10; @F19], and Go because its spec ranks `*` above `-` and groups equal operators from the left [@F26; @F27].

Your `exprc` loop from chapter 1 also gets 0, but nobody has yet said why that loop is right, and it only handles arithmetic. The language this book builds needs `if` statements and blocks nested inside blocks to any depth, which chapter 3 showed no regular expression can describe. So we need two things: a way to write down the syntax that pins down one tree per program, and a way to be sure the [parser]{.term def="The compiler phase that reads the token stream and builds the tree that shows how the tokens group into phrases."} you write in Go follows it. Before reading on, think back to the interpreter you built. When its parser saw a `-`, how did it decide what the right operand was?

::: crux
How do we write down a language's syntax precisely enough that every program has exactly one tree, and how does a parser that reads tokens left to right, looking one token ahead, build that tree without ever guessing?
:::

## Rules that can nest: grammars and derivations

A grammar is a set of rewriting rules, and the programs of a language are exactly the token strings you can reach by rewriting, starting from one symbol. That is the whole idea. Everything else in this section is making it precise enough to run by hand.

A [context-free grammar]{.term def="A set of rewriting rules, each replacing one named kind of phrase by a sequence of tokens and phrase names, together with a starting phrase name."} has four parts [@F1; @F2; @F3]. Its [terminals]{.term key="terminal" def="A grammar symbol that stands for a token kind and is never rewritten."} are the words of the language, and these correspond to chapter 3's token kinds: `num` (chapter 3's `INT`), `-`, `(`, `if` and so on. Its [nonterminals]{.term key="nonterminal" def="A grammar symbol that names a kind of phrase and is rewritten by the grammar's rules."} name kinds of phrases, like "expression" or "statement". Its [productions]{.term key="production" def="One grammar rule, saying that the nonterminal on its left may be replaced by the sequence of symbols on its right."} say "this kind of phrase may be written as this sequence". One nonterminal is the [start symbol]{.term def="The nonterminal every derivation of a whole program begins from."}, the kind of phrase a whole input must be. Here is our first grammar, which we will call G1:

$$E \to E - E \mid E * E \mid (\ E\ ) \mid num$$

The bar separates four alternatives, so this is four productions for one nonterminal `E`, which is also the start symbol.

To use it, start with the string `E` and repeat three steps: pick a nonterminal in the string, pick one of its productions, and replace the nonterminal by the production's right side. Stop when only terminals remain [@F4]. This process is a [derivation]{.term def="A sequence of strings that starts with the start symbol and turns each string into the next by rewriting one nonterminal with one of its productions."}. If at every step you rewrite the leftmost nonterminal, it is a [leftmost derivation]{.term def="A derivation that rewrites the leftmost nonterminal at each step."} [@F18]. The `grammar` lab prints one for our running input, one rewrite per line, with the production used on the right:

```{.output include="lab/grammar/run.out" lines="3-11"}
```

Here `num` tokens are shown by their text. Follow it line by line. The first step turns `E` into `E - E`. The second rewrites the leftmost `E` again, into another `E - E`, so the string is now `E - E - E`. The next two steps turn the first two `E`s into `10` and `4`, the fifth step turns the last `E` into `E * E`, and the last two fill in `3` and `2`. Every line is a legal halfway point, and the last is our token string.

A derivation has an order, but the meaning does not care about it. Draw each rewrite as a node whose children are the right side of the production that rewrote it, and you get a [parse tree]{.term def="A tree whose inner nodes are nonterminals, each with the right side of the production that rewrote it as its children, and whose leaves are tokens (or ε for an empty production)."}. The tree records which production rewrote which `E` but forgets the order, so a leftmost and a rightmost derivation that apply the same rules to corresponding nodes give the same tree [@F5]. Here is the tree of the derivation above:

```{.dot include="lab/grammar/out/tree-0.dot" caption="The parse tree worth 0 for 10 - 4 - 3 * 2 under G1."}
```

The root `E` used `E → E - E`, so its children are `E`, `-` and `E`. The left child used `E → E - E` again and holds `10 - 4`. The right child used `E → E * E` and holds `3 * 2`, so the `*` sits low on the right. Now recall chapter 1's two walkers. Each one computes a node's children before the node itself, so the operator under the root is applied last. Here that is the second `-`, which subtracts 6 from 6 and gives 0. The shape of the tree is the meaning.

This also answers chapter 3's closing question. No regular expression matches balanced parentheses, because its automaton has finitely many states and cannot count [@F15; @F16]. The production `E → ( E )` mentions `E` inside its own parentheses, so `((7))` is just `E`, then `( E )`, then `( ( E ) )`, then `( ( 7 ) )`. Each extra pair costs one more rewrite, and no state has to count anything.

The notation you will meet in real specs is a richer version of the same thing. Go's spec writes its syntax in a variant of [EBNF]{.term def="Extended Backus-Naur Form, a grammar notation that adds optional parts and repetition to plain productions."} [@F22], where `|` separates alternatives, `[ ]` means zero or one time, and `{ }` means zero or more times [@F23]. Its block is `Block = "{" StatementList "}"` with `StatementList = { Statement ";" }` [@F25]. Historically, Chomsky separated context-free rules from other kinds of rules in 1956 [@F12], and Backus proposed a notation for ALGOL 58 in 1959 that the ALGOL 60 report formalized and Naur named [@F13; @F14]. That notation is [BNF]{.term def="Backus-Naur Form, the plain notation for context-free productions."}. "Context-free" means that a nonterminal can be rewritten by its rules no matter which symbols surround it [@F20; @F21].

## One list of tokens, five trees: ambiguity

The derivation above began by rewriting `E` with `E - E`. Could it have started with `E * E` instead? Try it before reading on. Put `10 - 4 - 3` under the left `E` and `2` under the right one, and see whether you can finish.

You can. The lab prints that derivation too, and its tree looks like this:

```{.dot include="lab/grammar/out/tree-6.dot" caption="The parse tree worth 6 for 10 - 4 - 3 * 2 under G1."}
```

Compare the roots. In the tree worth 0, the root's operator is the second `-`. Here it is `*`, so multiplication is applied last, to `(10 - 4) - 3`, which is 3, and 2. The result is 6. The same seven tokens, derived by the same grammar, have two trees, and the two trees compute different numbers. The lab searches for every tree and finds all five groupings from the opening:

```{.output include="lab/grammar/run.out" lines="21-27"}
```

A grammar is an [ambiguous grammar]{.term def="A grammar under which some sentence has more than one leftmost derivation, or equivalently more than one parse tree."} when some sentence has more than one leftmost derivation, or equivalently more than one parse tree [@F6]. This is a defect of the grammar, not of the input. A program must have a single meaning, or the compiler cannot know what code to generate [@F7]. G1 accepts exactly the right strings and still fails at its real job.

Ambiguity is not only about arithmetic. The classic statement-level case is the [dangling else]{.term def="The ambiguity in which an else after two nested ifs could belong to either one."}. In C, `if (a) if (b) s1; else s2;` could attach the `else` to either `if`, and the textbook's straightforward if-then-else grammar gives such a sentence two distinct derivations [@F8]. The C standard does not fix its grammar. It adds a rule in the meaning of the `if` statement: an `else` belongs to the nearest preceding `if` the syntax allows [@F9]. Go avoids the problem in the grammar itself. Its `IfStmt` production requires a `Block`, with braces, after the condition, and an `else` takes either another `IfStmt` or a `Block` [@F24]. Once the inner `if` must close its brace, there is nowhere for a dangling `else` to hang.

## Writing precedence and associativity into the grammar

We can fix G1 by giving each level of operator strength its own nonterminal, and by putting the recursion on the side the operators should group toward. Two words name what we are encoding. [Precedence]{.term def="The rule that decides which of two different operators takes its operands first, as when multiplication groups before subtraction."} decides that `3 * 2` groups before the `-` beside it, and [associativity]{.term def="The rule that decides how a run of operators of equal precedence groups, from the left or from the right."} decides that `10 - 4 - 3` means `(10 - 4) - 3`. The layered grammar G2 is:

$$\begin{aligned} Expr &\to Expr - Term \mid Term \\ Term &\to Term * Factor \mid Factor \\ Factor &\to (\ Expr\ ) \mid num \end{aligned}$$

Engineering a Compiler builds its expression grammar this way, with one level for parentheses, one for multiplication and division, and one for addition and subtraction [@F32]. Why does it work? Look at where each operator can appear. A `*` is only ever introduced by a `Term` production, and a `Term` can only produce a `-` by going through `Factor → ( Expr )`. So without parentheses, every `*` sits inside a `Term`, below any `-`. Now look at `Expr → Expr - Term`. The left operand of `-` is an `Expr`, which may itself be a subtraction, but the right operand is a `Term`, which cannot contain a bare `-`. So in `10 - 4 - 3` the only possible split puts `10 - 4` on the left, and that is left associativity. With parentheses the rules change, and a `-` can sit below a `*`, as in `(10 - 4) * 3`, which is exactly what parentheses are for.

The lab confirms that G2 leaves no choice for our input:

```{.output include="lab/grammar/run.out" lines="28-30"}
```

Here is that one tree:

```{.dot include="lab/grammar/out/layered.dot" caption="The parse tree of 10 - 4 - 3 * 2 under the layered grammar."}
```

Three things to notice. The spine of `Expr` nodes down the left side is the left grouping of the two `-`, with the first subtraction deepest. The `Term` that is the root's right child holds `3 * 2`, so multiplication sits under the second `-`. And the chains like `Term → Factor → 10` carry no operator at all. They are the price of layering, since every number has to pass through every level on its way to the top.

Real languages split on this choice. C writes exactly this layering, with additive expressions built from multiplicative ones [@F10; @F19], and its standard says the syntax itself specifies the precedence of operators [@F11]. Go's spec writes the ambiguous `Expression = UnaryExpr | Expression binary_op Expression` [@F28] and settles it with a separate table of five precedence levels [@F29], plus the rule that equal levels group from the left [@F27]. The last section of this chapter shows how a parser implements that table directly.

::: {.misconception title="Higher precedence means that operation is computed first"}
Precedence decides the shape of the tree, meaning which operands belong to which operator. When the operands are evaluated is a separate rule. In Go, `f() - g() * h()` groups `g() * h()` under the `-`, yet Go evaluates function calls in an expression in lexical left-to-right order [@F30]. The `eval-order` lab's `f`, `g` and `h` print their names and return 10, 3 and 2:

```{.output include="lab/eval-order/run.out" lines="3-7"}
```

`f` runs first even though its subtraction happens last.
:::

## The rule that calls itself first: left recursion

A [top-down parser]{.term def="A parser that builds the tree from the root downward, choosing each node's production before reading the tokens that production covers."} starts at the root and decides which production to use before it has read the tokens that production covers [@F62]. The obvious way to write one in Go is a function per nonterminal that follows its production. So turn `Expr → Expr - Term | Term` straight into a function. The production starts with `Expr`, so the function starts by calling itself. This is [left recursion]{.term def="A nonterminal deriving, in one or more steps, a sequence beginning with itself, directly or through other rules."} [@F63], and the `left-recursion` lab writes it out next to the version that works:

```{.go include="lab/left-recursion/main.go" lines="15-30"}
```

What does `naiveExpr` do on `10 - 4 - 3 * 2`? Its first act is to call `naiveExpr`, having read nothing. That call does the same, and so does the next. No call ever looks at a token, so the input does not matter. Each call pushes a frame, exactly as `fact(5)` did in chapter 2, and nothing ever pops one:

```{.output include="lab/left-recursion/run.out" lines="3-6"}
```

The limit in that message is the default maximum stack for one goroutine, 1 GB on 64-bit systems, and the runtime crashes the program when a goroutine's stack would grow past it [@F59; @F60]. The textbook states the general problem: with a left-recursive grammar, a top-down parser can expand forever without producing a leading terminal it could match or reject [@F34].

The fix is a mechanical rewrite that defines the same language [@F35]. A rule of the form `A → A α | β`, where β does not start with `A`, becomes `A → β A'` and `A' → α A' | ε`. Here ε means the empty string, so `A' → ε` says that `A'` may produce nothing. Read it in plain words: an `A` is one β followed by any number of αs. Applied to `Expr` and `Term`, the lab produces the grammar G3, which the next two sections use:

```{.output include="lab/grammar/run.out" lines="32-36"}
```

The strings are the same, but the trees are not. To see this on a small case, take the subtraction-only grammar `E → num E'`, `E' → - num E' | ε` and the input `10 - 4 - 3`. On the left below is its parse tree, and on the right the tree that `parseExpr`'s loop builds:

```{.dot include="lab/grammar/out/rewritten.dot" caption="For 10 - 4 - 3, the right-leaning parse tree under the rewritten grammar and the left-leaning tree the loop builds."}
```

In the parse tree, the first `-` hangs from the top `E'` with only `4` beside it, and the rest of the input nests deeper to the right. Nothing there says that `10 - 4` is a unit. The loop puts that back. `parseExpr` reads a `Term`, then for each `-` it reads one more `Term` and makes a new node with the tree so far as its left child. That folds to the left, so the first `-` ends up deepest, as on the right. In EBNF the loop is `Expr = Term { "-" Term }`. On our running input the fixed parser prints:

```{.output include="lab/left-recursion/run.out" lines="7-9"}
```

This is the same shape as `exprc`'s loop from chapter 1, which also reads an operand and then absorbs operators while it can. A bottom-up parser generator, the subject of chapter 5, can use left recursion as written [@F33].

::: {.misconception title="If my grammar accepts exactly the right programs, it is a correct grammar"}
The tree is the meaning, and two grammars can accept the same token strings with different trees. G1 and G2 accept the same expressions, but only G2 forces `10 - 4 - 3 * 2` to be worth 0. Removing left recursion also keeps the strings and changes the tree's shape, which is why the parser's loop has to rebuild the left grouping.
:::

## What can come first: FIRST sets

Our predictive top-down parser chooses a production by looking at one token [@F44], and it can do that only if it knows which tokens can begin each alternative. That token it peeks at without consuming is the [lookahead]{.term def="The next unread token, which the parser examines to choose a production."}.

Sometimes the choice is obvious. In our statement language, the five kinds of statement begin with `var`, an identifier, `if`, `return` and `{`. Each alternative starts with a different terminal, so one look at the next token decides at once. In G3 the choice is harder. When the parser is about to expand `Expr'`, it must pick between `- Term Expr'` and nothing at all. If the lookahead is `-`, the first is clearly right. But what can begin a `Term`? `Term` starts with `Factor`, which starts with `(` or `num`. For a bigger grammar we want that bookkeeping done systematically.

The [FIRST set]{.term def="For a grammar symbol or sequence, the set of terminals that can begin a string derived from it, plus ε if it can derive the empty string."} of a symbol holds the terminals that can appear first in something derived from it [@F36]. Following the textbook, we also put ε into it as a marker meaning "this can be empty". To compute FIRST of a production's right side, take FIRST of its first symbol without ε. If that symbol can be empty, add FIRST of the next symbol without ε too, and so on. Add ε only if every symbol can be empty [@F40; @F64]. Then add the result to FIRST of the production's left side [@F41].

Let us do it by hand. Start every nonterminal's set empty, with each terminal's FIRST set containing itself [@F65], and walk G3's productions in order, updating sets in place as we go.

In pass 1, `Expr → Term Expr'` adds FIRST(`Term`), which is still empty, so `Expr` stays {}. Next, `Expr' → - Term Expr'` adds `-` and `Expr' → ε` adds ε, while `Term → Factor Term'` adds nothing because FIRST(`Factor`) is still empty too. `Term'` gets `*` and ε in the same way, and finally the two `Factor` productions add `(` and `num`.

In pass 2, `Expr` still sees an empty `Term`, because `Term` is updated after `Expr` in the order we walk. But `Term` now sees `Factor`'s {`num`, `(`} and takes it. In pass 3, `Expr` finally sees `Term`'s set and takes {`num`, `(`}. Pass 4 changes nothing.

| Pass | Expr | Expr' | Term | Term' | Factor |
|---|---|---|---|---|---|
| 1 | {} | {-, ε} | {} | {*, ε} | {num, (} |
| 2 | {} | {-, ε} | {num, (} | {*, ε} | {num, (} |
| 3 | {num, (} | {-, ε} | {num, (} | {*, ε} | {num, (} |
| 4 | no change | | | | |

One pass is not enough because the information flows backwards against our walking order, from `Factor` up through `Term` to `Expr`, one level per pass. The lab computes the same thing:

```{.output include="lab/grammar/run.out" lines="38-42"}
```

Why must this stop? Look at what a pass can do. It only ever adds members to sets, never removes them. There are five sets, and each can hold at most the seven symbols `num - * ( ) eof ε`. So at most 35 additions can ever happen. Every pass except the last adds at least one, so after at most 35 passes that change something, a pass must change nothing. The state we stop in, where one more pass changes nothing, is a [fixed point]{.term def="A state that one more round of a repeated update leaves unchanged."}. The textbook's loop likewise repeats while the sets change and halts when it reaches a fixed point [@F40; @F41]. You will see this repeat-until-nothing-changes pattern again in chapter 11, where dataflow analysis computes facts about a program the same way.

## What can come next: FOLLOW sets, START sets and the LL(1) table

FIRST answers the question for `Expr' → - Term Expr'`, but not for `Expr' → ε`. The empty alternative starts with no token at all. The parser should pick it when the lookahead is something that may come right after an `Expr'`. That is the [FOLLOW set]{.term def="For a nonterminal, the set of terminals, plus eof, that can appear immediately after a string derived from it."}, the tokens that can appear immediately to the right of a string derived from a nonterminal, with `eof` standing for the end of the input [@F37].

We compute it with the same repeated passes. FOLLOW(`Expr`) starts with `eof`, because a whole input is an `Expr` followed by the end. Then, for every place a nonterminal B appears in a right side `A → … B rest`, add FIRST(rest) without ε to FOLLOW(B), and if `rest` can be empty, also add FOLLOW(A) [@F66]. In pass 1, `Expr → Term Expr'` gives `Term` the `-` from FIRST(`Expr'`), and since `Expr'` can be empty, also `eof` from FOLLOW(`Expr`). `Expr'` is at the end, so it inherits `eof`. Further down, `Factor` gets `*` and inherits `Term`'s set, and `Factor → ( Expr )` finally gives `Expr` a `)`. That `)` arrived after `Expr'`, `Term` and `Factor` had already copied from `Expr`, so pass 2 carries it down to them, and pass 3 changes nothing:

```{.output include="lab/grammar/run.out" lines="43-46"}
```

Now combine the two. The [START set]{.term def="For a production, the FIRST set of its right side without ε, plus the FOLLOW set of its left side if the right side can be empty."} of a production `A → β` is FIRST(β) if β cannot be empty, and otherwise FIRST(β) without ε, together with FOLLOW(A) [@F38]. The second edition of the textbook called the corresponding set FIRST+, retaining ε in the nullable case [@F39]. A grammar is a [backtrack-free grammar]{.term def="A grammar in which, for every nonterminal, the START sets of its alternatives do not overlap."} when, for every nonterminal with several alternatives, their START sets are pairwise disjoint [@F43]. Then one lookahead token names at most one production. Such grammars are [LL(1)]{.term def="Parsed by scanning the input Left to right, building a Leftmost derivation, with 1 token of lookahead."}, from scanning Left to right, building a Leftmost derivation, with 1 token of lookahead [@F44].

Put the START sets in a table, with a row per nonterminal and a column per lookahead, and the cell `Table[A, w]` says which production expands `A` when the lookahead is `w` [@F46]. Here are G3's eight numbered productions and its table, where `.` marks an empty cell:

```{.output include="lab/grammar/run.out" lines="47-62"}
```

Every cell holds at most one production, so G3 is LL(1). An empty cell is a syntax error. Now feed G2, the left-recursive grammar, through the same machine:

```{.output include="lab/grammar/run.out" lines="63-67"}
```

Both `Expr` alternatives start with whatever a `Term` starts with, so they collide in every column where a `Term` can begin. Here the recursive alternative's START set contains everything the base alternative's does. Left recursion is not an option for LL(1) [@F33].

The table can drive a parser with no recursion at all. Keep an explicit stack of symbols, starting with `Expr` above `eof`. If the top is a nonterminal, pop it and push the right side of the production the table names, with its first symbol on top. If it is a terminal, it must match the lookahead, and both are consumed. The lab's first ten steps on our input, with the stack top on the left, look like this:

```{.output include="lab/grammar/run.out" lines="68-78"}
```

The stack holds what the parser still expects to see, which is the job chapter 2's machine stack is about to take over.

## Recursive descent: the table as Go code

The table's rows can become functions. [Recursive descent]{.term def="A parsing method built from one procedure per nonterminal, each recognising its nonterminal and calling the others for the nonterminals in its productions."} writes one procedure per nonterminal, and the procedure for A calls the procedure for B to recognise each B on A's right side [@F45]. Each function then chooses its production with a `switch` on the lookahead token, and that `switch` is its row of the LL(1) table. This is the twin of chapter 3's point that a hand-written lexer's `switch` is the DFA's transition function written as code. Here is the `parser` lab's statement function, running on chapter 3's lexer unchanged:

```{.go include="lab/parser/parser.go" lines="44-65"}
```

The five `case` labels are the START sets of the five `Stmt` productions. Run on `if x1 <= 10 { y = x1 * 2; }`, which is chapter 3's line with the `;` our language needs because its lexer inserts no semicolons, the parser makes these choices:

```{.output include="lab/parser/run.out" lines="22-29"}
```

Each choice corresponds to a table lookup. The last choice is the empty production for the missing `else`, picked because `EOF` is in what may follow an `if` statement.

The default branch gives something for free. When the lookahead is in no START set, the parser knows exactly which tokens would have been acceptable, so it can say so with a position:

```{.output include="lab/parser/run.out" lines="33-34"}
```

There is a deeper link to chapter 3 as well. In this kind of parser, every open `(` or `{` is a function call that has not yet returned, a frame on the machine stack waiting for its closer. That stack grows with the input's nesting, unlike chapter 3's fixed-state DFA, though Go still imposes the runtime stack limit [@F59].

In Go's own compiler, the `Expression` grammar production appears as the doc comment of the `syntax` package's `binaryExpr` method [@F53]. Chapter 5 takes up why production compilers hand-write their parsers, and how they recover after an error instead of stopping at the first one, as ours does.

## Pratt parsing: one loop for every precedence level

Layering works, but it does not scale gracefully. Go has five binary precedence levels [@F29], so the layered approach needs a function per level, and parsing a lone `x` walks through every one of them on its way down to a primary. Instead, we can give each operator a number and parse every level with one loop.

Vaughan Pratt presented this idea in "Top Down Operator Precedence" at the first Principles of Programming Languages symposium in 1973 [@F61]. In [Pratt parsing]{.term def="Parsing expressions with one loop that compares the binding power of each operator it meets against a minimum passed down by its caller."}, parsing behaviour is attached to tokens. Pratt calls the code a token runs when it starts an expression its null denotation, or nud, and the code it runs when an expression is already in hand on its left its left denotation, or led [@F47]. A number's nud just returns the number. A `-`'s led takes the left operand it is handed and parses a right one.

What decides how far a right operand reaches is each operator's [binding power]{.term def="A number saying how tightly an operator holds its operands, so that a higher number groups first."}. The lab uses Go's levels: `-` is 4, `*` is 5, and anything that is not an operator, such as EOF, is 0. `parseExpr(min)` reads one operand, then looks at the next token. If its binding power is at least `min`, the loop absorbs the operator and parses its right operand with `parseExpr(power + 1)`. Otherwise it returns what it has. The outer call uses minimum 1.

Trace `10 - 4 - 3 * 2` by hand. Call 1 has minimum 1 and reads `10`. It sees `-` with power 4, and 4 ≥ 1, so it absorbs it and starts call 2 with minimum 5. Call 2 reads `4` and sees the second `-`. Its power 4 is below 5, so call 2 returns just `4`, and call 1 now holds `10 - 4`. Call 1 sees that same `-`, 4 ≥ 1, absorbs it and starts call 3 with minimum 5. Call 3 reads `3`, sees `*` with power 5, and 5 ≥ 5, so it absorbs it and starts call 4 with minimum 6. Call 4 reads `2`, sees EOF with power 0, and returns. Call 3 now holds `3 * 2`, sees EOF and returns, and call 1 builds `(10 - 4) - (3 * 2)`. The lab prints the same decisions:

```{.output include="lab/parser/run.out" lines="4-14"}
```

Precedence comes from the powers themselves, and left grouping comes from the `+ 1`: the right operand of `-` is parsed with minimum 5, so the next `-`, at 4, stops it and the outer loop takes that `-` instead. And `*` joins the right operand because 5 ≥ 5. The result is the tree worth 0 that we drew first in this chapter. Here is the whole core:

```{.go include="lab/parser/parser.go" lines="67-86"}
```

Prefix `-` lives in `primary`, which parses the operand with minimum 6, above every binary level, because Go gives unary operators the highest precedence [@F26]. So `-2 * 3` stops the operand at `*` and gives `(* (neg 2) 3)`. To make an operator group to the right instead, parse its right operand with the operator's own power rather than one more, so the next equal operator is absorbed by the inner call. The lab's other trees show the same parser handling comparisons, calls and parentheses:

```{.output include="lab/parser/run.out" lines="16-20"}
```

Now look back at chapter 1. `exprc`'s `expression(min)` keeps absorbing operators while `precedence(op) >= min` and parses each right operand with `precedence(op) + 1`. That is this loop exactly. Its usual name is [precedence climbing]{.term def="Parsing expressions by a loop that absorbs operators whose precedence is at least a minimum and parses each right operand with a minimum chosen for its associativity."}. Norvell says Keith Clarke proved it correct in a 1985 report and that Martin Richards appears to have invented it first for the CPL and BCPL compilers [@F51]. Andy Chu, after implementing both, concluded that precedence climbing and Pratt parsing are the same algorithm [@F52].

Crockford writes the test differently. Each call holds a fixed right binding power `rbp` and continues while `rbp < lbp`, where `lbp` is the binding power of the current token [@F48; @F68], and an ordinary left-associative operator parses its right operand with its own power as the new `rbp` [@F49; @F69]. Set `min = rbp + 1`. For whole numbers, `bp >= rbp + 1` holds exactly when `rbp < bp`, so the two loop tests agree, and passing `bp` as the new `rbp` is the same as passing `bp + 1` as the new `min`. It is bookkeeping, not a different algorithm. Go's compiler uses the strict form: its `binaryExpr` loops while the operator's precedence is greater than its `prec` argument and recurses with the operator's own precedence [@F54]. The standard library's `go/parser` uses ours, returning when the precedence is below its minimum and recursing with `oprec+1` [@F56]. Clang's `ParseRHSOfBinaryExpression` likewise takes a minimum precedence [@F58]. On our input, `go/parser` builds the same tree as the lab:

```{.output include="lab/parser/run.out" lines="36-37"}
```

So the answer to the crux comes in two parts. For these expressions, a layered grammar, or a precedence table together with associativity, pins down one tree per program. A parser that chooses each step from one lookahead token, with a `switch` per nonterminal and one loop for expressions, builds that tree without guessing. Chapter 6 turns that tree into an abstract syntax tree with scopes.

::: tryit
First by hand, trace the Pratt loop on `1 - 2 * 3 - 4`, writing one line per event in the lab's format: call number, minimum, operand, and each operator seen with absorb or return. Then predict the tree. Now add `"1 - 2 * 3 - 4"` to the expression list in `lab/parser/main.go`, rerun the lab, and compare the line it prints with your prediction. If you also want the full trace, change `running` instead and look at the trace section. Every token here is one chapter 3's lexer already knows.
:::

## Check yourself

::: selftest
1. Take the C-style grammar `Stmt → if ( E ) Stmt Else | other` with `Else → else Stmt | ε`. Compute the START sets of `Else`'s two productions. Which cell of the LL(1) table holds two productions, and which choice gives C's rule that an `else` belongs to the nearest `if`?
2. Suppose statements may also be calls, `f(x);`, alongside assignments `x = e;`. Both `Stmt` alternatives now start with IDENT. What happens to the table, and how would you rewrite the rules so one token of lookahead suffices again?
3. Trace the Pratt loop on `-2 * 3`. Which call returns at `*`, and why?
4. Suppose the lab parsed the right operand of `-` with minimum 4 instead of 5. What tree and value would `10 - 4 - 3` give?
5. Why does `naiveExpr` crash even on the input `7`?
6. In the G3 table, which cell does the parser consult when the input is `10 )`, and what does it find there?
:::

::: answers
1. START(`Else → else Stmt`) is {`else`}. For `Else → ε` it is FOLLOW(`Else`), which equals FOLLOW(`Stmt`), because `Else` ends a `Stmt` production. A `Stmt` can be followed by an `Else`, so FOLLOW(`Stmt`) contains `else` as well as `eof`. Both productions are therefore in cell [`Else`, `else`]. Always choosing `Else → else Stmt` attaches the `else` to the innermost open `if`, which is C's rule.
2. Both productions land in cell [`Stmt`, IDENT], so the grammar is not LL(1). Factor out the shared start: `Stmt → IDENT Rest`, `Rest → = Expr ; | ( Args ) ;`. Now the choice is made after the IDENT, on `=` or `(`. This rewrite is called left factoring [@F67].
3. Call 1, minimum 1, sees prefix `-` and starts call 2 with minimum 6. Call 2 reads `2`, sees `*` with power 5, and returns because 5 is below 6. Call 1 now holds `(neg 2)`, sees `*`, absorbs it since 5 ≥ 1, and parses `3` in call 3 with minimum 6. The tree is `(* (neg 2) 3)`.
4. Call 2 would have minimum 4, so it would absorb the second `-` itself. The tree is `10 - (4 - 3)`, worth 9, which is right association.
5. Its first statement calls `naiveExpr` before reading any token, so no input is ever examined. The recursion never ends, frames pile up, and the goroutine hits its stack limit whatever the input.
6. After matching `10`, the parser expands `Term'` with lookahead `)`, which gives production 6, `Term' → ε`, and then `Expr'` with `)`, which gives production 3. With `Expr'` gone the top of the stack is `eof`, which does not match `)`, so the parser reports a syntax error there. The table entries were fine. It is the stray `)` that cannot be matched.
:::
