---
topic: Compilers
chapter: 4
title: Grammars and top-down parsing
---

Your chapter 3 lexer now hands you a clean stream of tokens, and the next job is to turn that flat stream into a tree. Say you write down the rule for expressions the way a textbook sentence reads it: an expression is a number, or a name, or an expression followed by an operator and another expression. Then you feed it this line.

```{.text .sketch}
10 - 4 - 3 * 2
```

Nothing in your rule says which tree to build. Grouped as `(10 - 4) - (3 * 2)` the line is 0, which is what Go and C compute [@F13; @F14; @F51]. Grouped as `10 - (4 - (3 * 2))` it is 12, and as `((10 - 4) - 3) * 2` it is 6. The rule accepts the line under every one of these groupings, so it cannot be the whole specification of the language. You try the obvious repair, a rule that says an expression is an expression, then a minus, then a term, and you translate it into a Go function whose first act is to call itself. The program dies with a stack overflow before it has read a single token.

So two things went wrong, and they pull in different directions. The first rule was too loose to pin down a tree, and the tightened rule produced code that cannot run. This chapter untangles both, and along the way it explains why the little `expression(min)` loop in `exprc` from chapter 1 always got the right answer.

::: crux
How does a parser recover the tree structure of a token stream, and how can you tell from the grammar alone whether a simple parser that reads left to right and looks one token ahead will build the right tree without ever backtracking?
:::

## A rule that mentions itself

Chapter 3 ended on a limit. No regular expression matches parentheses nested to any depth, because a finite automaton has a fixed number of states and so cannot count without bound [@F48]. The way out is to let a rule refer to itself. "A parenthesized expression is an open parenthesis, then an expression, then a close parenthesis" is a rule whose middle part can be another parenthesized expression, and that one can contain another. Each time the rule is used inside itself, the matching close parenthesis has to wait, and keeping track of everything that is waiting is exactly the unbounded memory a DFA lacks. In the hand-written parsers later in this chapter, that memory will turn out to be the call stack.

A [context-free grammar]{.term def="A set of rewriting rules, each replacing one named syntactic category by a sequence of tokens and categories, that together describe a language."} writes such rules down precisely. Engineering a Compiler defines it as four pieces [@F1]. The [terminals]{.term key="terminal" def="The symbols a grammar cannot rewrite further, which for a parser are token kinds."} are the words of the language, and for us they are simply the token kinds the lexer returns. The [nonterminals]{.term key="nonterminal" def="A named syntactic category in a grammar, such as Expr, that rules rewrite into other symbols."} are made-up names like `Expr` and `Term` that give the rules structure [@F1]. Then there is a set of [productions]{.term key="production" def="One grammar rule, written A → β, saying that the nonterminal A may be replaced by the sequence β."} [@F2], and one [start symbol]{.term def="The nonterminal that every derivation of a whole program begins from."}, the nonterminal that stands for a whole program [@F49].

Here is a small grammar for our expressions. It has one nonterminal, `E`, and one production per line.

```{.text .sketch}
E → E - E
E → E * E
E → num
```

How does a grammar say that `10 - 4 - 3 * 2` is an expression? In plain words, you start with the start symbol and keep replacing some nonterminal with the right side of one of its rules until only tokens are left. That process is a [derivation]{.term def="A sequence of rewriting steps that begins with the start symbol and ends with a string of terminals."} [@F2], and each intermediate string along the way is called a sentential form [@F5]. If at every step you rewrite the leftmost remaining nonterminal, you get a [leftmost derivation]{.term def="A derivation that rewrites the leftmost nonterminal at every step."}, and the mirror image is a rightmost derivation [@F3]. Writing `num` for each number, one leftmost derivation of our line is:

```{.text .sketch}
E
⇒ E - E
⇒ E - E - E
⇒ num - E - E
⇒ num - num - E
⇒ num - num - E * E
⇒ num - num - num * E
⇒ num - num - num * num
```

Now record which nonterminal was replaced by which right side, as a tree with `E` at the root and each rewrite hanging its symbols underneath. That tree is the [parse tree]{.term def="A tree that records which production rewrote each nonterminal in a derivation, with the order of the steps forgotten."} [@F4]. The tree throws away the order of the steps and keeps only the structure, and the structure is what the rest of the compiler walks to give the program its meaning.

The idea has two parents. Noam Chomsky distinguished context-free generative rules from transformation rules in 1956 while studying natural language [@F10]. In 1959 John Backus proposed a notation for the syntax of the International Algebraic Language (IAL), now known as [ALGOL]{.term def="Short for ALGOrithmic Language."} 58, and it was formalized in the ALGOL 60 report, where Peter Naur gave it the name [BNF]{.term def="Backus normal form, later Backus-Naur form, a text notation for writing context-free grammars."} in the 1963 report [@F9]. You have read a grammar in this tradition already without noticing. The Go specification is written in [EBNF]{.term def="Extended BNF, which adds grouping, optional parts and repetition to plain BNF."}, where `|` separates alternatives, `()` groups, `[]` marks something optional and `{}` marks something repeated zero or more times [@F11]. Its rule for expressions is

```{.text .sketch}
Expression = UnaryExpr | Expression binary_op Expression .
```

and it should look familiar, because it has the same shape as our three-line grammar [@F12].

## One sentence, several trees

Before reading on, take a pencil and draw two different parse trees for `10 - 4 - 3 * 2` under our grammar. Then ask how many there are in total.

The `grammar-lab` answers by brute force. It tries every way of splitting the token list at an operator, recursively, and prints each tree fully parenthesized together with its value.

```{.output include="lab/grammar-lab/run.out" lines="3-9"}
```

There are five trees, and they produce five different numbers. Only the third one, `((10 - 4) - (3 * 2)) = 0`, is what a Go or C programmer means [@F13; @F14; @F51]. A grammar like this is an [ambiguous grammar]{.term def="A grammar under which some sentence has more than one parse tree, or equivalently more than one leftmost derivation."}: some sentence in its language has more than one parse tree, which is the same as having more than one leftmost derivation [@F6]. Here the trees give different meanings, and the grammar alone does not tell a compiler which one to pick.

Drawing two of them makes the difference visible. Each `E` hangs underneath it the symbols of the production that rewrote it, and each leaf is a `num` token, written as its value. The left tree is the one the leftmost derivation above records. A tree is evaluated from the leaves up, so the operator at the root is the one applied last. In the tree worth 0 that is the second `-`, and in the tree worth 6 it is the `*`.

```{.dot caption="Two parse trees for 10 - 4 - 3 * 2 under the ambiguous grammar. Left, the third tree, worth 0. Right, the fifth tree, worth 6."}
digraph {
  node [shape=plaintext, width=0.2, height=0.2]; edge [arrowhead=none]; ordering=out; nodesep=0.12; ranksep=0.2;
  a [label="E"]; a1 [label="E"]; a2 [label="-"]; a3 [label="E"];
  a -> a1; a -> a2; a -> a3;
  a11 [label="E"]; a12 [label="-"]; a13 [label="E"];
  a1 -> a11; a1 -> a12; a1 -> a13;
  a11n [label="10"]; a11 -> a11n; a13n [label="4"]; a13 -> a13n;
  a31 [label="E"]; a32 [label="*"]; a33 [label="E"];
  a3 -> a31; a3 -> a32; a3 -> a33;
  a31n [label="3"]; a31 -> a31n; a33n [label="2"]; a33 -> a33n;
  b [label="E"]; b1 [label="E"]; b2 [label="*"]; b3 [label="E"];
  b -> b1; b -> b2; b -> b3; b3n [label="2"]; b3 -> b3n;
  b11 [label="E"]; b12 [label="-"]; b13 [label="E"];
  b1 -> b11; b1 -> b12; b1 -> b13; b13n [label="3"]; b13 -> b13n;
  b111 [label="E"]; b112 [label="-"]; b113 [label="E"];
  b11 -> b111; b11 -> b112; b11 -> b113;
  b111n [label="10"]; b111 -> b111n; b113n [label="4"]; b113 -> b113n;
}
```

Notice that the problem lives in the grammar and not in the set of strings it accepts. Usually an unambiguous grammar exists for the same language, although a few languages are inherently ambiguous and admit no such grammar [@F8]. You might hope a tool could check a grammar and warn you, but no general check exists. Deciding whether an arbitrary context-free grammar is ambiguous is undecidable, because an algorithm for it would also solve the Post correspondence problem [@F7]. Language designers therefore avoid ambiguity by construction, using grammar shapes they know to be safe.

The classic statement-level example is the [dangling else]{.term def="The ambiguity in if c1 if c2 s1 else s2 about which if the else belongs to."}. In C, `if (a) if (b) s1; else s2;` could attach the `else` to either `if`. C settles it with a sentence in the standard rather than in the grammar: an `else` belongs to the lexically nearest preceding `if` that the syntax allows [@F15]. Engineering a Compiler shows that you can also push this rule into the grammar itself, rewriting it so that it accepts the same sentences but forces each `else` onto the innermost unmatched `if` [@F16]. Go sidesteps the whole question. Its `if` body is a `Block` [@F17], and a block is written between matching braces [@F18], so in the chapter 3 line `if x1 <= 10 { y = x1 * 2 }` the closing brace already says where the inner statement ends, and an `else` that follows it has only one `if` to belong to.

## Building precedence into the grammar, and the trap it sets

How do we write a grammar for which the third tree is the only tree? Two separate decisions are hiding in that tree. [Precedence]{.term def="The rule that decides which of two different operators groups first, such as multiplication before subtraction."} decides between different operators, so that `3 * 2` groups before the `-` next to it. [Associativity]{.term def="The rule that decides how repeated operators of equal precedence group, either from the left or from the right."} decides between repeats of operators at the same level, so that `10 - 4 - 3` means `(10 - 4) - 3`. Go's specification, for example, has five precedence levels for binary operators and says operators of equal precedence associate left to right [@F13; @F14].

Precedence comes from layering, with one nonterminal per level.

```{.text .sketch}
E → E + T | E - T | T
T → T * F | T / F | F
F → ( E ) | num | id
```

An `E` is a chain of `T`s joined by `+` or `-`, and a `T` is a chain of `F`s joined by `*` or `/`. A `*` can only be produced inside a `T`, and below a `T` the only way back to an `E` is through the parentheses in `F → ( E )`. So without parentheses a multiplication can never end up above a subtraction in the tree, and with them, as in `(10 - 4) * 3`, the subtraction sits inside the multiplication, which is exactly what the parentheses ask for. Associativity comes from which side the recursion is on. In `E → E - T` the recursive `E` is on the left, so a chain of subtractions grows down the left side and `10 - 4 - 3` groups as `(10 - 4) - 3`. Putting the recursive `E` on the right instead, as in `E → T - E`, groups subtractions from the right.

The rule `E → E - T` has [left recursion]{.term def="A grammar rule whose right side begins with the same nonterminal it defines, directly or through other rules."}, and that is the trap from the opening. A naive [recursive-descent]{.term key="recursive descent" def="A top-down parser with one function per nonterminal, calling the functions for the symbols in its productions."} parser turns each nonterminal into a function, so `E` becomes a function whose first step is to parse an `E`. The `left-recursion` lab writes that function literally, next to the version that works.

```{.go include="lab/left-recursion/main.go" lines="20-38"}
```

The naive function calls itself before `p.pos` ever moves, so the recursion has no way to stop. To make the crash quick, the lab lowers the stack limit to 32768 bytes itself. Go's own default maximum on a 64-bit machine is 1 GB [@F46], which would take longer to fill and fail the same way.

```{.output include="lab/left-recursion/run.out" lines="4-14"}
```

The runtime reports the exceeded limit and throws "stack overflow" [@F47], with zero tokens consumed. The second half of the output is the fixed parser.

The general repair is mechanical. A directly left-recursive nonterminal `A → A α | β` becomes `A → β A'` and `A' → α A' | ε`, where ε means the empty sequence, and the new grammar defines the same language [@F19]. Engineering a Compiler also gives an algorithm for grammars without cycles or ε-productions that removes indirect left recursion, which runs through several rules, by first substituting it into direct form [@F20]. For our grammar the rewrite gives:

```{.output include="lab/grammar-lab/run.out" lines="24-28"}
```

There is a catch, though. The same strings are accepted, but the parse tree of `E'` has a right-recursive tail rather than the original left grouping. The parser has to rebuild the left grouping itself, and in hand-written code that is exactly the `for` loop in `expr` above. `E'` says "zero or more of `+ T` or `- T`"; the subtraction-only loop reads `- T`s one at a time, and each pass folds the previous result into the left child. That is why the fixed parser prints `((10 - 4) - (3 * 2))` and the value 0.

## LL(1): knowing which rule to pick

A top-down parser builds the tree from the root down, and at every step it is standing at some nonterminal with several productions to choose from. The question of [predictive parsing]{.term def="Top-down parsing that chooses each production by looking at upcoming tokens, without ever backtracking."} is whether one token of lookahead is always enough to make that choice correctly. To answer it from the grammar alone we need three small sets.

In plain words, the first question is "which tokens can this thing start with?". The [FIRST set]{.term def="The set of terminals that can appear as the first token of some string derived from a symbol or sequence of symbols."} of a symbol is the set of terminals that can begin something derived from it [@F21]. Some nonterminals can also vanish entirely. A nonterminal is [nullable]{.term def="Able to derive the empty sequence, so that it can match no tokens at all."} if it can derive nothing at all, as `E'` can through `E' → ε`. We keep ε separately in the nullable set, as the lab does. When a nonterminal can vanish, the token that decides things comes from whatever follows it. The [FOLLOW set]{.term def="The set of terminals, plus end of input, that can appear immediately after a string derived from a nonterminal."} of a nonterminal is the set of tokens that can appear right after it, including the end-of-input marker, written `$` in the lab [@F22].

Before looking at the output, try a few by hand for the rewritten grammar. FIRST(`F`) is easy, because `F` starts with `(`, `num` or `id`. `T` and `E` both begin with an `F`, so they share that set. What can follow `E'`? Every `E'` sits at the end of an `E`, and an `E` is followed either by `)` inside parentheses or by the end of input. Now check yourself against the lab.

```{.output include="lab/grammar-lab/run.out" lines="31-36"}
```

Combining the sets gives one lookahead set per production. If the right side β cannot vanish, the set is FIRST(β). If it can, the set is FIRST(β) together with FOLLOW of the left side, because then the deciding token belongs to whatever comes next. The second edition of Engineering a Compiler calls its augmented set FIRST+ [@F24], and the third edition calls the lookahead set START(A → β) [@F52]. The lab uses the older name but leaves ε out.

```{.output include="lab/grammar-lab/run.out" lines="37-44"}
```

The rule for choosing becomes clean. With one-token lookahead, a grammar is backtrack free exactly when, for every nonterminal with several productions, the lookahead sets of those productions are pairwise disjoint [@F23]. Such a grammar is called [LL(1)]{.term def="A grammar that a parser can handle predictively, reading left to right, building a leftmost derivation, with one token of lookahead."}, and each part of the name means something: the input is scanned Left to right, the parser discovers a Leftmost derivation, and it uses 1 symbol of lookahead [@F25]. Look at `T'`. Its three productions have the sets `{*}`, `{/}` and `{$, ), +, -}`, which share nothing, so a `-` after a `T` can only mean "this term is finished".

Turning the sets into a table is now mechanical. Each nonterminal gets a row, each lookahead token a column, and each production goes into the cells of its lookahead set. The lab finds no cell with two entries.

```{.output include="lab/grammar-lab/run.out" lines="49-55"}
```

The left-recursive grammar fails this test badly. Every production of `E` starts with something from `{(, id, num}`, so all three land in the same cells.

```{.output include="lab/grammar-lab/run.out" lines="16-21"}
```

That is not specific to our grammar. A left-recursive rule like `E → E + T | T` is not LL(k) for any amount of lookahead k [@F28]. The reverse direction gives a useful guarantee: every LL(k) grammar is unambiguous [@F29], so passing the test also rules out the five-tree problem. A different kind of conflict appears when two productions share a common prefix, as in `A → α β1 | α β2`. [Left factoring]{.term def="Rewriting productions that share a common prefix so the prefix is matched once and a new nonterminal chooses among the different endings."} moves the shared prefix in front of a new nonterminal that chooses among the endings once the prefix has been read [@F26].

With the table in hand, a parser needs only an explicit stack of symbols still to be matched. Engineering a Compiler's skeleton parser looks at the symbol on top and indexes the table by that nonterminal and the lookahead token [@F27]. Here is the start of the lab's trace on our line, with the stack top on the left.

```{.output include="lab/grammar-lab/run.out" lines="57-64"}
```

A nonterminal on top is replaced by the production the table names, and a terminal on top must match the next input token. The trace runs on until both the stack and the input are down to `$` and the parser accepts.

Now look at your interpreter's parser with this in mind. You probably wrote recursive descent [@F50], one function per nonterminal, each starting with a `switch` or `if` on the current token. That `switch` is one row of the LL(1) table, and the machine stack of nested calls is the explicit stack from the trace. It is the same point chapter 3 made about hand-written lexers: the hand-written code is the automaton in disguise.

## Pratt parsing for expressions

Layered grammars work, but they get heavy. Go's specification has five binary precedence levels [@F13], and a layered grammar needs a nonterminal for each one. Parsing the single number `7` then walks down through every level, one nested call each, just to find out that nothing follows. Is there a way to keep precedence in a table instead of in the shape of the grammar?

Pratt's answer gives each operator a number, its [binding power]{.term def="A number attached to an operator saying how tightly it holds its operands, with higher numbers grouping first."}. Think of how strongly the operator pulls on the operands next to it. Then one loop parses a whole expression: read an operand, and keep absorbing the following operator as long as it binds at least as tightly as a current minimum. This is [Pratt parsing]{.term def="Expression parsing guided by binding powers, with token-specific behavior for starting and continuing expressions."}. Pratt presented it as "Top Down Operator Precedence" at the first Principles of Programming Languages symposium in 1973 [@F30]. In his vocabulary a token that starts an expression, like a number or a prefix minus, has a nud, short for null denotation, and a token that continues an expression from its left, like an infix operator, has a led, short for left denotation [@F31; @F53].

Here is the binding-power table from the `parser` lab and its loop.

```{.go include="lab/parser/parser.go" lines="56-60"}
```

```{.go include="lab/parser/parser.go" lines="63-80"}
```

```{.go include="lab/parser/parser.go" lines="81-89"}
```

`p.prefix()` plays the nud role. It handles numbers, names, parentheses and prefix minus, which parses its operand with minimum 40 so that `-2 * 3` becomes `(* (neg 2) 3)`. The loop body plays the led role. The important detail is the minimum passed to the right operand, `power + 1`. An operator's own binding power is compared against the current minimum, and a possibly different number becomes the minimum for the recursive call [@F35]. Raising it by one means a following operator of the same power fails the test and is left for the caller, which makes the operator group to the left. Passing `power` instead makes an operator right associative; Crockford's strict-comparison variant instead reduces the right binding power [@F34].

Now walk the trace on `10 - 4 - 3 * 2`, and predict each line before reading it.

```{.output include="lab/parser/run.out" lines="3-8"}
```

The outer call starts with minimum 0, reads `10` and absorbs the first `-`, then recurses for the right operand with minimum 21. That inner call reads `4`, sees the second `-` with power 20, finds 20 below 21 and returns, so the right operand is just `4`. Back in the outer loop the left side is now `(- 10 4)`, and the second `-` is absorbed at minimum 0. Its right operand is parsed at minimum 21 again, which reads `3` and absorbs `*` because 30 clears 21. The result is the third tree from the lab, the one worth 0.

This should look familiar. Chapter 1's `exprc` had a `precedence(op)` function and an `expression(min int)` loop, and that is this algorithm. The name [precedence climbing]{.term def="Theodore Norvell's name for an expression-parsing loop driven by operator precedence and a minimum, later shown to be Pratt parsing."} comes from Theodore Norvell, who wrote that neither of its earlier describers, Keith Clarke and Martin Richards, had given it a name [@F37]. Andy Chu implemented both and concluded that precedence climbing and Pratt parsing are the same algorithm [@F36]. So `exprc` worked because its minimum did the job that the grammar layers do: it stopped the recursion at exactly the operators that belong to an outer level.

Douglas Crockford wrote about the technique in a chapter of *Beautiful Code* [@F32], and Bob Nystrom notes that Crockford's JSLint uses a Pratt parser and that his treatment was one of very few remotely modern articles on it [@F33]. Production compilers also use these techniques. The Go compiler's `binaryExpr` takes a precedence argument and loops while the current operator's precedence exceeds it [@F38], and its scanner keeps an operator precedence field [@F39]. GCC replaced its generated C++ parser with a hand-written recursive-descent one in 3.4 [@F40] and did the same for C in 4.1 [@F41]. Clang's parser is recursive descent [@F42] with a precedence-based parser for binary operators [@F43], and rustc parses by recursive descent as well [@F44; @F45].

::: {.misconception title="Precedence and associativity are the same idea"}
They answer different questions. Precedence decides between different operators, `-` against `*`, while associativity decides between repeats of one level, as in `10 - 4 - 3`. In a grammar, layering settles the first and the side of the recursion settles the second. In a Pratt parser the table settles the first, and the choice of `power + 1` or a lower minimum for the right operand settles the second. Get the powers right but pass `power` instead of `power + 1`, and the parser still puts `3 * 2` together but groups the subtractions from the right, computing `10 - (4 - 6)`, which is 12.
:::

## Your parser

The `parser` lab puts the two techniques together on top of chapter 3's lexer, copied unchanged. Statements are recursive descent and expressions are the Pratt loop, and every tree prints as an S-expression, operator first. Here is the case for `if`.

```{.go include="lab/parser/parser.go" lines="172-181"}
```

It reads like the grammar rule. After `if` comes an expression, then a braced block, and then, only if the lookahead token is `else`, a second block. The single `if` on `p.token.Kind` is that rule's row of the LL(1) table. Because both bodies must be blocks, the dangling else cannot arise. Here are the running example, the chapter 3 statement, and a function with an `if`/`else`.

```{.output include="lab/parser/run.out" lines="11-18"}
```

Read `a < b == c` as `(== (< a b) c)`. The comparison operators share one binding power, so they fold left like subtraction. The parser checks syntax only, so it raises no complaint about comparing a boolean with `c`.

A parser also has to fail well. This one stops at the first error and reports a line and column instead of panicking.

```{.output include="lab/parser/run.out" lines="24-26"}
```

In the first line the input ends where a `)` was required, and in the second the parser reached `}` while expecting the start of an expression.

Finally, does our parser agree with the real thing? The lab's `compare.go` runs the standard library's `go/parser` on the running example and prints its tree in the same form.

```{.output include="lab/parser/run.out" lines="28-29"}
```

It builds the same tree that our parser printed for the running example.

::: tryit
Run the lab with `python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only parser`. Then change the right-hand minimum in `expression` from `power + 1` to `power`, and before rerunning, predict the tree for `10 - 4 - 3 * 2` and its value. Afterwards, teach the lexer to accept `%`, add it at power 30, and check that `7 - 5 % 3` groups the way Go would.
:::

Several threads stay open. This parser gives up at the first error, while production parsers can recover and report more [@F57]. Chapter 5 takes that up, along with bottom-up parsing, which can handle left recursion without rewriting it [@F54; @F55] and is what bison generates [@F56]. And the trees here are bare S-expressions. Chapter 6 turns them into a proper syntax tree with positions, scopes and name resolution.

## Check yourself

::: selftest
1. Restricted to numbers and the operators `-` and `*`, without parentheses, the layered grammar and the three-line ambiguous grammar accept exactly the same token strings. In what sense, then, is one of them right and the other wrong?
2. Rewrite `S → S , x | x` to remove its left recursion, and describe the shape of the new parse tree for `x , x , x`.
3. Using the lab's sets, which production does the LL(1) table choose at `T'` when the lookahead is `)`, and why is that the right choice?
4. Suppose you add a right-associative power operator `^` at binding power 40. What minimum should its right operand use, and what tree should `2 ^ 3 ^ 2` produce?
5. A friend adds `E → id ( Args ) | id` to an LL(1) grammar and reports a table conflict. What is the conflict, and how do you fix it?
:::

::: answers
1. A grammar is a specification of trees, not only of strings. The ambiguous grammar gives `10 - 4 - 3 * 2` five trees with five values, and only the layered one gives the single tree worth 0, so the layered one encodes the intended grouping without extra rules.
2. `S → x S'` and `S' → , x S' | ε`. Its tree has a right-recursive tail, not a binary comma tree. A parser that wants left grouping must fold in a loop.
3. `T' → ε`, because `)` is in FOLLOW(`T'`) and so in that production's lookahead set. Seeing `)` means the current term has ended and the token belongs to an enclosing rule.
4. A minimum equal to its own power, 40, rather than 41, so that a following `^` passes the test and is absorbed by the inner call. The tree is `(^ 2 (^ 3 2))`.
5. Both productions start with `id`, so their lookahead sets overlap at `id`. Left factor them into `E → id E'` with `E' → ( Args ) | ε`; then check that `(` is not in FOLLOW(`E`) to avoid a new conflict.
:::
