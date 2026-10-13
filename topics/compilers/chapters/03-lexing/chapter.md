---
topic: Compilers
chapter: 3
title: "Lexing: regular languages and automata"
---

The `lex` function in `exprc` was a short loop, and it worked for a simple reason. Every piece of the input was either a single character like `+` or `(`, or a run of digits, so the loop could look at one character and know at once what it had found. Now suppose you grow the language a little, with variables, comparisons and an `if` statement, and you feed the same kind of loop this line:

```{.text .sketch}
if x1 <= 10 { y = x1 * 2 } // done
```

The one-character trick falls apart in four places at once. `<=` has to come out as one piece, but `<` on its own is also legal, so after reading `<` the loop cannot know what it holds until it peeks at the next character. `if` must be recognised as a [keyword]{.term def="A word the language reserves for its own syntax, which therefore cannot be used as a name."}, while `x1` and `iffy` are names, and all of them start with a letter. `//` starts a comment that swallows the rest of the line, yet `/` alone is division. And the spaces separate things without meaning anything themselves. You could keep adding special cases until this line works, but you would never be sure the next line works too. What you want is a rule that gives the right answer every time, and a way to check that your loop follows it.

::: crux
How does a compiler turn a stream of characters into meaningful units correctly and, for these rules, in time linear in the input, and why does one small theory of patterns and state machines describe that job so exactly that a hand-written loop and a generated one turn out to be the same machine?
:::

## Why lexing is its own phase

The first job of a compiler's front end is to group characters into words. A [token]{.term def="One meaningful unit of source text, represented here by its category together with the text it came from."} is such a word, and our representation has two main parts. Its [token kind]{.term def="The category a token belongs to, such as identifier, integer literal or less-or-equal operator."} says what sort of thing it is, and its [lexeme]{.term def="The exact characters from the source that make up one token."} is the text it was made from. The identifier `x1` and the identifier `y` share a kind and differ in lexeme, while `<=` is the only possible lexeme of its kind. The part of the compiler that produces tokens is the [lexer]{.term def="The compiler phase that reads source characters and produces a stream of tokens, also called a scanner."}, and textbooks also call it the scanner.

Engineering a Compiler describes the job this way. The scanner reads a stream of characters, groups them into words, checks each word against the rules of the language, and gives every valid word a syntactic category [@F6]. "Syntactic category" is the book's name for token kind. Run on our line, the job looks like this:

| Lexeme | Token kind |
|---|---|
| `if` | keyword `if` |
| `x1` | identifier |
| `<=` | less-or-equal |
| `10` | integer |
| `{` | left brace |
| `y` | identifier |
| `=` | assign |
| `x1` | identifier |
| `*` | star |
| `2` | integer |
| `}` | right brace |

Thirty-four characters became eleven tokens. The spaces and the comment are gone, because our parser does not need them.

Why not let the parser read characters directly? In principle it could, since anything a lexer does could be folded into a grammar. The reason the split survives is less about speed than about keeping two kinds of question apart. Cooper and Torczon note that the old efficiency argument for a separate scanner weakened once fast parsing techniques arrived, and that scanners are still built separately because it cleanly divides lexical structure from syntactic structure [@F7]. Lexical structure asks what a number or a name looks like. Syntactic structure asks how those pieces nest into expressions and statements. The first kind of question has a simpler answer, and as we will see, a much cheaper machine can answer it. The second needs the grammars of chapter 4.

So the parser gets a short stream of meaningful units with the noise removed, and the lexer gets a job small enough to be specified precisely. The rest of this chapter is about that precise specification.

## Two rules every lexer needs: longest match and priority

Go back to the moment the lexer has just read `<`. What must it do before it can emit anything? It cannot emit "less than" yet, because the next character might be `=`. It has to look ahead, and if the `=` is there, take both characters. The general rule behind this is [maximal munch]{.term def="The lexing rule that the next token is always the longest prefix of the remaining input that forms a valid token, also called longest match."}, and the Go specification states it in one sentence: "the next token is the longest sequence of characters that form a valid token" [@F1]. The C standard says the same thing about its preprocessing tokens [@F4].

Longest match also settles `iffy`. The lexer could stop after `if` and call it a keyword, but `iffy` is a longer valid token, an identifier, so it wins. Then what about `if` itself? Two rules match exactly the same two characters. One says identifier, and the other says keyword. Go reserves twenty-five keywords, counted from the list in its specification, and none of them may be used as an identifier [@F3]. Longest match cannot break this tie, because both candidates have the same length, so a second rule is needed. Lexers give the token rules a priority, and when several rules match the same longest text the highest-priority rule wins [@F26]. Keywords are placed above identifiers.

These two rules together specify how to choose among matching token rules. Longest match picks how much text, and priority picks which kind.

Longest match is greedy, and it never asks whether its choice will make sense later. The C standard's own example shows the cost. The fragment `x+++++y` is lexed as `x ++ ++ + y`, which breaks a rule about the increment operator, even though `x ++ + ++ y` might have been a correct expression [@F5]. The lexer takes `++` twice because each time that is the longest token available, and the error only shows up later. The `real-lexers` lab gives both versions to gcc:

```{.output include="lab/real-lexers/run.out" lines="29-37"}
```

gcc's message does not list tokens, but it fits the standard's account. With the tokens `x ++ ++`, the second `++` is applied to `x++`, which is a value rather than a modifiable lvalue, so there is nothing to increment [@F44; @F45]. Adding spaces, as in `x++ + ++y`, ends the tokens where you want them, and the file compiles.

Go adds a third rule you have relied on every day. You rarely type semicolons, yet Go's grammar uses them to end statements. The lexer supplies them through [semicolon insertion]{.term def="Go's lexer rule that adds a semicolon token at the end of a line when the line's last token is one of the kinds listed by the specification."}. When a line's final token is an identifier, a literal, one of the keywords `break`, `continue`, `fallthrough` or `return`, or one of `++`, `--`, `)`, `]` or `}`, a semicolon is inserted right after it [@F2]. Notice what this rule needs. It looks back at the previous token, not just ahead at characters, so the lexer must keep track of that token. We will see it in action in the section on real lexers.

## Regular expressions and Thompson's construction

We now know what the lexer must decide. The next question is how to write the token rules down so precisely that a program could build the lexer from them. The answer is a [regular expression]{.term def="A pattern that describes a set of strings using concatenation, alternation and repetition."}, built from single characters, the empty string and the empty language with three operations. Concatenation, written by putting patterns side by side, means one followed by the other. [Alternation]{.term def="The regular expression operation that matches anything either of two patterns matches."}, written `a|b`, means either one [@F41]. The [Kleene star]{.term def="The regular expression operation that matches zero or more repetitions of a pattern."}, written `a*`, means zero or more repetitions. A character class like `[a-z]` is shorthand for a long alternation, and `a+` is shorthand for `aa*`. The set of strings a regular expression describes is a [regular language]{.term def="A set of strings that some regular expression describes, equivalently one that some finite automaton recognises."} [@F15].

For now, take five rules from our running example, in priority order:

| Kind | Regular expression |
|---|---|
| `IF` | `if` |
| `IDENT` | `[a-z][a-z0-9]*` |
| `INT` | `[0-9]+` |
| `LT` | `<` |
| `LE` | `<=` |

A regular expression is a description, not a procedure. To run one we turn it into a graph. A [nondeterministic finite automaton]{.term key="NFA" def="A graph of states with character-labelled or ε-edges that accepts a string if some path from the start state, reading the string, ends in an accepting state."}, or NFA, is a set of states joined by edges labelled with characters. It may also have an [ε-transition]{.term def="An edge in an automaton that can be followed without reading any input character."}, an edge you can cross for free. Because a state may have several ways forward on the same character, or a free edge besides, an NFA is best pictured as being in several states at once. It accepts a string if any of those states is accepting when the input runs out [@F42].

[Thompson's construction]{.term def="A method that builds an NFA from a regular expression by combining one small NFA fragment per operator."} turns a regex into an NFA with one small recipe per operator. Each fragment has one entry and one exit. A character becomes two states joined by that character. Concatenation joins the first fragment's exit to the second's entry with an ε-edge. Alternation adds a new entry with ε-edges into both fragments and a new exit that both fragments reach by ε-edges. A star adds a loop back from the fragment's exit to its entry, plus a bypass edge for zero repetitions. Here is the lab's version, about twenty lines:

```{.python include="lab/automata/automata.py" lines="87-111"}
```

Because each operator adds only a constant number of states, the NFA grows linearly with the regex. Cox's counting of his variant gives at most one state per character or operator [@F10]. The lab joins all five rules under one start state with ε-edges and labels each rule's exit with its kind, which gives 21 states and 23 edges.

The idea is old. Kleene introduced regular expressions in a 1956 paper and proved that they describe exactly the languages finite automata recognise, according to a secondary course page [@F15]. Rabin and Scott introduced nondeterministic automata in 1959, as Cox's history reports [@F14]. In 1968 Ken Thompson published a compiler that took a regular expression and produced an IBM 7094 program [@F8], and he used it for searching in a text editor he had written [@F9].

How do we run an NFA? Keep the set of states it could be in, and for each input character replace the set with every state reachable by that character and then by free edges. Each character costs work bounded by the NFA's size, so a regex of length $m$ on text of length $n$ takes $O(mn)$ time [@F11]. That is linear in the input for a fixed regex. Many library regex engines work differently. In Cox's 2007 measurements, Perl, Python, Ruby and the Perl Compatible Regular Expressions (PCRE) library tried one path at a time and backed up on failure [@F13], and on the pattern `a?` repeated $n$ times followed by `a` repeated $n$ times, Perl needed over sixty seconds at $n = 29$ where the set simulation needed twenty microseconds [@F12]. The lab measured Python's `re` against its own set simulation on this machine:

```{.output include="lab/automata/run.out" lines="45-51"}
```

At $n = 8$ Python's engine is faster in this run. But each step of four in $n$ multiplies Python's time by roughly four to sixteen, while the simulation stays well under a millisecond. These timings depend on the machine and the run.

::: {.misconception title="The regexes in a lexer are the same as the ones in Python or Perl"}
Many library regex engines add features such as backreferences, which match a repeat of earlier text and can describe nonregular languages [@F43], and use backtracking, which can go exponential [@F13]. Go's `regexp` package is one counterexample: it does not support backreferences [@F17] and is guaranteed to run in time linear in its input [@F16]. Lexer regexes are the strict regular subset, compiled to an automaton that takes one transition per character during recognition; longest-match scanning may reread characters after backing up [@F25].
:::

## From NFA to DFA: subset construction and minimization

The set simulation is linear, but it does real work per character, computing a new set each time. Look at what it computes, though. The set of NFA states you could be in after some input depends only on the input, never on run-time data. So why not compute every set you could ever reach ahead of time and give each one a number? Then running the machine means looking up one table entry per character.

That precomputed machine is a [deterministic finite automaton]{.term key="DFA" def="An automaton with exactly one next state for each state and input character, and no ε-transitions."}, or DFA. Building it takes two operations. The [ε-closure]{.term def="The set of NFA states reachable from a given set by ε-transitions alone, including the set itself."} of a set of states is everything reachable from it by free edges, including the set itself [@F19]. Move takes a set and a character and returns the states reachable by an edge with that character, followed by ε-closure. The [subset construction]{.term def="The algorithm that builds a DFA whose states are the sets of NFA states reachable on some input."} starts from the ε-closure of the NFA's start state, then repeatedly takes an unprocessed set from a worklist, applies move on every character, and adds any new set it finds. Engineering a Compiler names the move step Delta [@F18]. The lab's version is `closure`, `move` and `subset`, lines 113 to 156 of `automata.py`.

Here is the DFA the lab built for our five rules. The column `other a-z` stands for every lowercase letter except `f` and `i`, and the transition columns give the next DFA state:

```{.output include="lab/automata/run.out" lines="5-17"}
```

Trace `if` by hand. The start state is 0, whose set holds the start state and the entry of every rule. On `i` the table says state 5, whose set contains states from both the `if` rule and the identifier rule. On `f` it says state 8, holding NFA states 4, 8, 9 and 10. NFA state 4 is the exit of the `IF` rule and state 8 is the exit of `IDENT`, so this DFA state accepts two kinds at once. This is the keyword tie from earlier, now sitting in one table row. The lab resolves it the way scanner generators do, by taking the highest-priority kind [@F26], so state 8 reports `IF`. State 3, with the empty set, is the dead state that every impossible character leads to.

A DFA by itself only says whether a whole string is accepted. A lexer needs longest match too, so the scanning loop keeps running past accepting states and remembers the last one it saw. When it reaches the dead state or the end of input it backs up to that last accepting position, which yields the longest valid prefix [@F25]. This can reread input: with rules `a` and `a*b`, scanning a run of `a`s with no final `b` repeatedly scans the remaining suffix, then backs up to emit one `a`, taking quadratic time. The lab's `scan`, at lines 177 to 194, uses the same last-accepting-position strategy. With rules for punctuation, spaces and comments added to the five above, it lexes the opening line into `IF IDENT LE INT LBRACE IDENT ASSIGN IDENT STAR INT RBRACE`.

The precomputation has a price. Each DFA state stands for a set of NFA states, and an $n$-state NFA has $2^n$ subsets, so the DFA may have exponentially more states than the NFA [@F20]. The classic witness is the language of strings whose $n$-th symbol from the end is a particular letter. An NFA with $n+1$ states recognises it, and no DFA with fewer than $2^n$ states does [@F21]. Intuitively, the DFA has to remember the last $n$ characters, because any of them might turn out to be the important one. The lab built `(a|b)*a` followed by $n-1$ copies of `(a|b)`:

```{.output include="lab/automata/run.out" lines="32-43"}
```

The NFA column grows by six per step, because Thompson's construction adds a few ε-states per operator, while the minimized DFA doubles. Our five token rules do not show this blowup: they became a 9-state DFA from a 21-state NFA.

Subset construction can produce more states than needed. [DFA minimization]{.term def="Merging the states of a DFA that no input string can tell apart, giving the smallest equivalent DFA."} merges states that behave the same on every possible future input; for a lexer, this must preserve token kinds as well as acceptance. The lab starts by grouping states by the token kind they accept, then splits any group whose members go to different groups on some character, and repeats until nothing changes. Before reading on, look at the table again. Which two states have the same accepting kind and identical rows?

They are states 4 and 7. Both accept `IDENT`, and both go to state 7 on any letter or digit and to the dead state otherwise. State 5 also accepts `IDENT`, but on `f` it goes to state 8, which accepts `IF`, so it stays separate. The lab reports 8 states after minimization. Hopcroft's algorithm does this splitting cleverly enough to run in $O(n \log n)$ time for $n$ states and a fixed alphabet [@F22], and Engineering a Compiler also presents Brzozowski's algorithm, which builds the minimal DFA directly from an NFA [@F23]. For language recognition, whichever method you use, the answer is the same, because every regular language has one minimal DFA, unique up to renaming its states [@F24]; our lexer additionally preserves the chosen token kind.

## Real lexers: hand-written versus generated

You can stop at the regular expressions and let a program do the rest. A [lexer generator]{.term def="A tool that reads token rules written as regular expressions with actions and writes the source code of a lexer."} takes the rules and emits a lexer. flex is the classic one, and by default its output is a C scanner driven by tables [@F37; @F38]. Its matching rule is the pair we derived: it takes the match covering the most text, and among matches of equal length it chooses the rule listed first in the file [@F31]. The lab's spec puts `if` on line 6 and the identifier rule on line 7, and its output begins `IF(if)`. Swap those two lines and this happens:

```{.output include="lab/real-lexers/run.out" lines="25-27"}
```

The identifier rule now comes first, and it matches everything `if` matches, so flex reports that the keyword rule cannot be matched [@F32], and `if` comes out as an identifier. Rule order in flex only breaks ties. It never makes a shorter match beat a longer one. Another generator, re2c, also compiles regular expressions to DFAs but emits them as directly coded lexers rather than tables [@F33], and php and ninja are among its users [@F34].

Some production compilers write the lexer by hand instead. The rustc development guide says so directly, noting that rustc_lexer is hand-written even though generated state machines are popular [@F35]. The Go compiler's lexer is implemented in `cmd/compile/internal/syntax/scanner.go`, whose scanner advances one token per call to `next` [@F27]. Clang's internals manual describes its `Lexer` class as doing the mechanics of lexing tokens out of a buffer and deciding what they mean [@F36]. Production lexers also need positions and contextual rules: GCC's lexer records each token's line and column, and some of its diagnostics depend on lexer state [@F39; @F40]. Go's semicolon insertion is another token-dependent rule, and `go/scanner`, the library version of Go's lexer, shows it. Its `Scan` returns a position, a token and a literal when applicable [@F29], and an inserted semicolon gets the literal `"\n"` instead of `";"` [@F30]:

```{.output include="lab/real-lexers/run.out" lines="7-20"}
```

Each line ends in an identifier, a literal, `++` or `)`, so each gets a semicolon, exactly as the rule from section two predicts.

Hand-written lexers can also handle keywords differently from our DFA. Rather than giving `if` its own states, they can scan a whole identifier and then look it up in a table. The Go compiler hashes the identifier and checks a keyword map, and only does so for identifiers of two or more bytes [@F28]. This is the same priority rule, applied after the fact.

Here is the claim from the crux made concrete. Look at the core of the lab's Go lexer:

```{.go include="lab/lexer/main.go" lines="61-83"}
```

The `switch` on the first character corresponds to the start state's row of a DFA. The `for` loop over letters and digits corresponds to an ordinary identifier continuation state looping to itself. The keyword check happens afterward. The case for `=`, `!`, `<` and `>` includes the path through state 2 to state 6 in our table: after `<`, take `=` if it is there, otherwise stop and accept. Your interpreter's lexer almost certainly had this shape. For these rules, each branch must take the longest match and resolve ties the way the rules say, and the automaton gives you a way to check that branch by branch.

## Your lexer

The `lexer` lab is the book's lexer in Go, replacing `exprc`'s `lex`. It knows identifiers, decimal integers, the keywords `func`, `var`, `if`, `else` and `return`, the operators and punctuation the language needs, and `//` comments. Each token carries its line and column, and an unexpected character becomes an `ERROR` token rather than a panic. On the opening line it produces the eleven tokens of our table, starting `if` at 1:1 and `<=` at 1:7, with no token for the comment and `EOF` at 1:35.

```{.output include="lab/lexer/run.out" lines="17-23"}
```

Each rule from section two shows up here. `a<=b` gives one `<=`, while `a< =b` gives `<` then `=`, since the space ends the token. `iffy` is an identifier and `if` is a keyword, both by scanning the word and then consulting the map. `10/2//c` drops the comment, and `@` becomes an error token while lexing continues with `y`. This lexer feeds the parser you build in chapter 4.

::: tryit
Add the operators `&&` and `||` to the lab's lexer, then run it on `a&&b||c` and `a& &b`. Before you run it, write down the token stream you expect for each, and decide what a lone `&` should produce. Then draw the part of the DFA your change added.
:::

There is one thing no regular expression can do. Try writing one that matches exactly the strings of balanced parentheses, nested to any depth. You will find that a finite automaton has to remember how many parentheses are open, and with finitely many states it can only count so high. That limit is why the parser exists, and chapter 4 brings in grammars to handle it. Chapter 5 will reuse the subset construction from this chapter, this time on sets of parser items rather than NFA states.

## Check yourself

::: selftest
1. A lexer tries its rules in order and takes the first one that matches. What does it produce for `<=` and for `iffy`, given the rules in this chapter's table?
2. Using the DFA table in this chapter, trace the input `ifx`. Which states does the lexer pass through, and what token does it emit?
3. In C, how is `a---b` split into tokens, and is the result a valid expression?
4. A Go source line ends with `x +`. Does the lexer insert a semicolon after it? What does that mean for writing a long expression across several lines?
5. In flex, you put the rule `[a-z]+` above the rule `if`. Predict the warning and the token kind of `if`. Then predict what happens to `iffy` if the order is the other way around.
:::

::: answers
1. First match gives `<` for `<=` and keyword `if` followed by an identifier `fy` for `iffy`. Both are wrong. Longest match says `<=` and a single identifier `iffy`, and priority only decides between rules that match the same length.
2. From state 0, `i` leads to state 5, `f` to state 8, and `x` falls in the `other a-z` column, leading to state 7. State 7 accepts `IDENT`, and the input ends, so the lexer emits one identifier `ifx`. The pass through state 8, where `IF` was the chosen kind, does not matter because a longer match came after it.
3. Longest match takes `a`, then `--`, then `-`, then `b`, giving `a -- - b` [@F4]. For an ordinary modifiable integer variable `a` and integer `b`, that is valid: it subtracts `b` from the old value of `a`, while decrementing `a` as a side effect [@F44; @F45; @F46].
4. No. `+` is not on the list of final tokens that trigger insertion, so the expression continues onto the next line. This is why Go style breaks long expressions after an operator rather than before it.
5. flex warns that the `if` rule cannot be matched, because the identifier rule above it matches the same text, and `if` comes out as an identifier. With `if` first, `iffy` is still a single identifier, because four characters beat two and order only breaks ties of equal length.
:::
