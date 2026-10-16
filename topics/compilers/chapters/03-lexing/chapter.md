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
How does a compiler turn a stream of characters into meaningful units correctly and, for these rules, in time linear in the input, and why does one small theory of patterns and the machines that recognise them describe that job so exactly that a hand-written loop and a generated one turn out to be the same machine?
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

Go back to the moment the lexer has just read `<`. What must it do before it can emit anything? It cannot emit "less than" yet, because the next character might be `=`. It has to look ahead, and if the `=` is there, take both characters. The general rule behind this is [maximal munch]{.term def="The lexing rule that the next token is always the longest prefix of the remaining input that forms a valid token, also called longest match."}, and the Go specification puts it in one sentence: "the next token is the longest sequence of characters that form a valid token" [@F1]. The C standard says the same thing about its preprocessing tokens [@F4].

Longest match also settles `iffy`. The lexer could stop after `if` and call it a keyword, but `iffy` is a longer valid token, an identifier, so it wins. Then what about `if` itself? Two rules match exactly the same two characters. One says identifier, and the other says keyword. Go reserves twenty-five keywords, counted from the list in its specification, and none of them may be used as an identifier [@F3]. Longest match cannot break this tie, because both candidates have the same length, so a second rule is needed. Lexers give the token rules a priority, and when several rules match the same longest text the highest-priority rule wins [@F26]. Keywords are placed above identifiers.

These two rules together specify how to choose among matching token rules. Longest match picks how much text, and priority picks which kind.

Longest match is greedy, and it never asks whether its choice will make sense later. The C standard's own example shows the cost. The fragment `x+++++y` is lexed as `x ++ ++ + y`, which breaks a rule about the increment operator, even though `x ++ + ++ y` might have been a correct expression [@F5]. The lexer takes `++` twice because each time that is the longest token available, and the error only shows up later. The `real-lexers` lab gives both versions to gcc:

```{.output include="lab/real-lexers/run.out" lines="29-37"}
```

gcc's message does not list tokens, but it fits the standard's account. With the tokens `x ++ ++`, the second `++` is applied to `x++`, which is a value rather than a modifiable lvalue, so there is nothing to increment [@F44; @F45]. Adding spaces, as in `x++ + ++y`, ends the tokens where you want them, and the file compiles.

Go adds a third rule you have relied on every day. You rarely type semicolons, yet Go's grammar uses them to end statements. The lexer supplies them through [semicolon insertion]{.term def="Go's lexer rule that adds a semicolon token at the end of a line when the line's last token is one of the kinds listed by the specification."}. When a line's final token is an identifier, a literal, one of the keywords `break`, `continue`, `fallthrough` or `return`, or one of `++`, `--`, `)`, `]` or `}`, a semicolon is inserted right after it [@F2]. Notice what this rule needs. It looks back at the previous token, not just ahead at characters, so the lexer must keep track of that token. We will see it in action in the section on real lexers.

## Regular expressions: writing the rules down

We now know what the lexer must decide. The next question is how to write the token rules down so precisely that a program could build the lexer from them. The answer is a [regular expression]{.term def="A pattern that describes a set of strings using concatenation, alternation and repetition."}, built from single characters, the empty string and the empty language with three operations. Concatenation, written by putting patterns side by side, means one followed by the other. [Alternation]{.term def="The regular expression operation that matches anything either of two patterns matches."}, written `a|b`, means either one [@F41]. The [Kleene star]{.term def="The regular expression operation that matches zero or more repetitions of a pattern."}, written `a*`, means zero or more repetitions. A character class like `[a-z]` is shorthand for a long alternation, and `a+` is shorthand for `aa*`. The set of strings a regular expression describes is a [regular language]{.term def="A set of strings that some regular expression describes."} [@F15].

For now, take five rules from our running example, in priority order:

| Kind | Regular expression |
|---|---|
| `IF` | `if` |
| `IDENT` | `[a-z][a-z0-9]*` |
| `INT` | `[0-9]+` |
| `LT` | `<` |
| `LE` | `<=` |

A regular expression says which strings belong to a token kind, but not how to check them one character at a time, which is the only way a lexer ever sees its input. For that we need a precise picture of what a lexer knows partway through a token, and the next two sections build it with small machines drawn by hand.

## What a lexer remembers between characters

Go back once more to the lexer that has just read `<`, and picture the loop in your interpreter's lexer at that moment. The code is inside the branch for `<`, and being in that branch is everything it knows about the past. It has seen `<`, nothing earlier matters to this token, and the next character will decide what happens. Each such situation is a [state]{.term def="One situation a machine can be in, standing for everything it needs to remember about the characters read so far."}. Before reading anything, the lexer is in a start state. Reading `<` moves it to a state we can call "seen `<`", and reading `=` from there moves it to "seen `<=`". Each move is a [transition]{.term def="A rule that moves a machine from one state to another when the next input character is a given one, drawn as a labelled arrow."}, a rule of the form "in this state, if the next character is this one, go to that state".

We draw states as circles and transitions as arrows between them [@F47]. If you have met graphs whose arrows carry distances or costs, set that picture aside. The label on an arrow is not a cost, and nothing is ever added up along a path. It is a condition. The machine may cross the arrow only when the next input character is the one written on it, and crossing it uses that character up [@F49]. A label like `a-z` is shorthand for one arrow per letter. Some states mean that the characters read so far form a complete token. These are [accepting states]{.term key="accepting state" def="A state meaning that the characters read so far form a complete string the machine recognises, drawn as a double circle."}, drawn as double circles, and the start state is marked by an arrow that comes from nowhere [@F48]. Here is a machine for three of our rules, with the token kind of each accepting state written inside it:

```{.dot caption="A hand-drawn machine for the IDENT, LT and LE rules, where each label is the character that must come next to cross that arrow."}
digraph {
  rankdir=LR; nodesep=0.3; ranksep=0.45;
  node [shape=circle, fontsize=10, width=0.45, height=0.45, margin=0.02];
  edge [fontsize=10];
  entry [shape=point, width=0.06, label=""];
  start [label="start"];
  lt [shape=doublecircle, label="seen <\nLT"];
  le [shape=doublecircle, label="seen <=\nLE"];
  name [shape=doublecircle, label="in a name\nIDENT"];
  entry -> start;
  start -> lt [label="<"];
  lt -> le [label="="];
  start -> name [label="a-z"];
  name -> name [label="a-z, 0-9"];
}
```

Look at the arrow that leaves "in a name" and comes back to it. It is how a fixed number of circles handles names of any length. Reading one more letter or digit leaves the lexer in the same situation, still inside a name, so one state with a loop covers `x`, `x1` and `x1234567` alike. A machine like this is a [finite automaton]{.term def="A machine with a fixed set of states, a start state, accepting states and labelled transitions, which reads its input one character at a time."}, and finite means that its number of states is fixed before any input arrives. Programs and papers also call the arrows edges, which is why the lab later counts edges.

Running the machine is mechanical. It reads the input one character at a time and follows the arrow labelled with that character [@F49], and if no arrow matches, it stops [@F50]. A lexer adds one step of its own. When the machine stops, the lexer emits a token of the kind of the last accepting state it reached, then starts again from the start state with the character that stopped it. Here is the input `x1<=y`, one row per character the machine looks at:

| Character | State before | State after | What it means |
|---|---|---|---|
| `x` | start | in a name | accepting, an `IDENT` so far |
| `1` | in a name | in a name | round the loop, still an `IDENT` |
| `<` | in a name | none | no arrow, so emit `IDENT` `x1` |
| `<` | start | seen `<` | the same `<` again, an `LT` so far |
| `=` | seen `<` | seen `<=` | an `LE` so far |
| `y` | seen `<=` | none | no arrow, so emit `LE` `<=` |
| `y` | start | in a name | an `IDENT` so far |
| end | in a name | none | input over, so emit `IDENT` `y` |

Two rows deserve a second look. After the first `<` the machine is already accepting, yet it keeps reading because an arrow for `=` exists, and it emits a token only when it gets stuck. That is longest match turned into a mechanism. The character that got it stuck is not lost, because it starts the next token. Here the state where the machine gets stuck always accepts, but in general the lexer must remember the last accepting state and back up to it, as the lab's machine will show.

Notice also that every state has at most one arrow for any character, so the next state is never in doubt. A machine with that property is a [deterministic finite automaton]{.term key="DFA" def="A finite automaton in which every state has at most one transition for each input character, so the next state is never in doubt."}, or DFA [@F51]. You could turn this one straight into a `switch` inside a loop, and the section on real lexers shows that hand-written lexers do exactly that. Drawing it for three rules was easy. The fourth rule is where drawing by hand gets hard.

## Machines that keep several options open

Try adding the keyword rule `IF` to the figure. From the start state, where should `i` lead? Toward the keyword if the input is `if`, and into a name if it is `iffy` or `i2`. A DFA must pick one state, so you would have to invent states meaning "seen `i`, could be either" and "seen `if`, could be either", and keep both rules' futures straight by hand, for every one of Go's twenty-five keywords [@F3].

The way out is to stop forcing a single choice. Draw each rule's machine on its own, which is easy, and let the two share a start state:

```{.dot caption="Separate machines for IF and IDENT sharing one start state, so that on the letter i there are two arrows to choose from."}
digraph {
  rankdir=LR; nodesep=0.3; ranksep=0.45;
  node [shape=circle, fontsize=10, width=0.45, height=0.45, margin=0.02];
  edge [fontsize=10];
  entry [shape=point, width=0.06, label=""];
  start [label="start"];
  si [label="seen i"];
  sif [shape=doublecircle, label="seen if\nIF"];
  name [shape=doublecircle, label="in a name\nIDENT"];
  entry -> start;
  start -> si [label="i"];
  si -> sif [label="f"];
  start -> name [label="a-z"];
  name -> name [label="a-z, 0-9"];
}
```

The letter `i` is one of `a-z`, so on `i` the start state now has two arrows. A machine that may have more than one way forward on the same character is a [nondeterministic finite automaton]{.term key="NFA" def="A finite automaton that may have several transitions for the same character from one state, and that accepts a string if some way of following its arrows while reading it ends in an accepting state."}, or NFA. Cox describes it as a machine that cannot peek ahead and is therefore allowed to always guess correctly [@F52], and it accepts a string if some way of reading the string and following arrows ends in an accepting state [@F42].

A computer cannot guess, and it does not need to. It can follow every choice at once by keeping the set of all states the machine could be in, and on each character moving every state in the set along every arrow that matches that character [@F55]. A state with no matching arrow simply drops out of the set. Here is `iffy` followed by a space:

| Read so far | Set of possible states | Accepting kinds in the set |
|---|---|---|
| nothing | {start} | none |
| `i` | {seen `i`, in a name} | `IDENT` |
| `if` | {seen `if`, in a name} | `IF` and `IDENT` |
| `iff` | {in a name} | `IDENT` |
| `iffy` | {in a name} | `IDENT` |
| `iffy` and a space | empty | none |

After `if` the set holds two accepting states at once. That is the keyword tie from section two, now visible inside the machine, and priority settles it in favour of `IF`. On the next `f`, "seen `if`" has no arrow and drops out. When the space arrives the set is empty, so the machine is stuck, and longest match makes the token `iffy`, the longest input after which the set still held an accepting state. Nothing was guessed and no character was read twice. The set carried both possibilities forward until the input settled the question.

Sharing a start state does not always work. Suppose a rule's start state has an arrow looping back to itself, as a machine for `a*b` does, with `a` looping on the start state and `b` leading to an accepting state. Merge that start state with the start of a rule for `c`, and the combined machine accepts `ac` as a `c` token, because the loop now belongs to both rules.

The fix is an [ε-transition]{.term def="A transition that a machine may follow at any time without reading an input character."}, an arrow labelled with the Greek letter ε, epsilon, that the machine may follow at any time without reading a character [@F53; @F42]. Give the combined machine a new start state with an ε-arrow to each rule's start, and every rule's machine stays exactly as it was drawn. ε-arrows are never strictly needed, since an NFA can always be built without them, but they make machines much easier to build and to read [@F54]. Here are `LT` and `LE` joined this way, numbered as the `automata` lab numbers them:

```{.dot caption="The lab's NFA for the LT and LE rules, joined under start state 0 by ε-arrows."}
digraph {
  rankdir=LR; nodesep=0.25; ranksep=0.4;
  node [shape=circle, fontsize=10, width=0.4, height=0.4, margin=0.02];
  edge [fontsize=10];
  entry [shape=point, width=0.06, label=""];
  s16 [shape=doublecircle, label="16\nLT"];
  s20 [shape=doublecircle, label="20\nLE"];
  entry -> s0;
  s0 [label="0"]; s15 [label="15"]; s17 [label="17"]; s18 [label="18"]; s19 [label="19"];
  s0 -> s15 [label="ε"];
  s15 -> s16 [label="<"];
  s0 -> s17 [label="ε"];
  s17 -> s18 [label="<"];
  s18 -> s19 [label="ε"];
  s19 -> s20 [label="="];
}
```

The `LE` machine uses one more ε-arrow, from 18 to 19. It joins a machine for `<` to a machine for `=`, which is how the lab puts one pattern after another. Tracing sets now needs one extra step. At the start, and again after every character, add every state reachable by ε-arrows [@F56]. Here is `<=`:

| Read so far | Reached by the character | After following ε-arrows | Accepting kinds |
|---|---|---|---|
| nothing | start state 0 | {0, 15, 17} | none |
| `<` | {16, 18} | {16, 18, 19} | `LT` |
| `<=` | {20} | {20} | `LE` |

Set this beside the first figure. The set {16, 18, 19} behaves exactly like the single state "seen `<`". It accepts `LT`, and its only way forward is on `=`, to a set that accepts `LE`. A set of NFA states is acting as one DFA state, and that is how the lexer gets its speed back two sections from now.

## Thompson's construction: from regular expression to NFA

Both NFAs so far were assembled from small pieces that followed the shape of the regular expressions. [Thompson's construction]{.term def="A method that builds an NFA from a regular expression by combining one small NFA fragment per operator."} makes that a recipe, with one piece, or fragment, per regex operator. Each fragment has one entry and one exit. A character becomes two states joined by that character, like 15 and 16. Concatenation joins the first fragment's exit to the second's entry with an ε-arrow, like 18 to 19. Alternation adds a new entry with ε-arrows into both fragments and a new exit that both reach by ε-arrows. A star adds an ε-arrow from the fragment's exit back to its entry, allowing another repetition, and one that bypasses the fragment, allowing none. Here is the result for `IF` and `IDENT`:

```{.dot caption="The lab's NFA for the IF and IDENT rules, leaving out the ε-arrows from state 0 to the other three rules."}
digraph {
  rankdir=LR; nodesep=0.25; ranksep=0.35;
  node [shape=circle, fontsize=10, width=0.4, height=0.4, margin=0.02];
  edge [fontsize=10];
  entry [shape=point, width=0.06, label=""];
  s0 [label="0"]; s1 [label="1"]; s2 [label="2"]; s3 [label="3"];
  s4 [shape=doublecircle, label="4\nIF"];
  s5 [label="5"]; s6 [label="6"]; s7 [label="7"];
  s8 [shape=doublecircle, label="8\nIDENT"];
  s9 [label="9"]; s10 [label="10"];
  entry -> s0;
  s0 -> s1 [label="ε"];
  s1 -> s2 [label="i"];
  s2 -> s3 [label="ε"];
  s3 -> s4 [label="f"];
  s0 -> s5 [label="ε"];
  s5 -> s6 [label="a-z"];
  s6 -> s7 [label="ε"];
  s7 -> s9 [label="ε"];
  s9 -> s10 [label="a-z, 0-9"];
  s10 -> s9 [label="ε"];
  s10 -> s8 [label="ε"];
  s7 -> s8 [label="ε"];
}
```

Find the star of `[a-z0-9]*`. States 9 and 10 are the fragment for one letter or digit, the ε-arrow from 10 back to 9 allows another, and the ε-arrow from 7 to 8 allows none. Trace `x1` within this figure. The start set, 0 and everything its ε-arrows reach, is {0, 1, 5}. On `x`, only state 5 has an arrow, to 6, and the ε-arrows from 6 give {6, 7, 8, 9}, which holds the `IDENT` exit 8. On `1`, state 9 moves to 10, giving {8, 9, 10}. The hand-drawn "in a name" state has become several states, because the recipe never stops to tidy up. Here is the lab's version of the recipe, about twenty lines:

```{.python include="lab/automata/automata.py" lines="87-111"}
```

Because each operator adds only a constant number of states, the NFA grows linearly with the regex. Cox's counting of his variant gives at most one state per character or operator [@F10]. The lab joins all five rules under one start state with ε-arrows and labels each rule's exit with its kind, which gives 21 states and 23 edges.

The idea is old. Kleene introduced regular expressions in a 1956 paper and proved that they describe exactly the languages finite automata recognise, according to a secondary course page [@F15]. Rabin and Scott introduced nondeterministic automata in 1959, as Cox's history reports [@F14]. In 1968 Ken Thompson published a compiler that took a regular expression and produced an IBM 7094 program [@F8], and he used it for searching in a text editor he had written [@F9].

Running an NFA is the set tracing we have been doing by hand. For each input character, replace the set with every state reachable by that character and then by ε-arrows. Each character costs work bounded by the NFA's size, so a regex of length $m$ on text of length $n$ takes $O(mn)$ time [@F11]. That is linear in the input for a fixed regex. Many library regex engines work differently. In Cox's 2007 measurements, Perl, Python, Ruby and the Perl Compatible Regular Expressions (PCRE) library tried one path at a time and backed up on failure [@F13], and on the pattern `a?` repeated $n$ times followed by `a` repeated $n$ times, Perl needed over sixty seconds at $n = 29$ where the set simulation needed twenty microseconds [@F12]. The lab measured Python's `re` against its own set simulation on this machine:

```{.output include="lab/automata/run.out" lines="45-51"}
```

At $n = 8$ Python's engine is faster in this run. But each step of four in $n$ multiplies Python's time by roughly four to sixteen, while the simulation stays well under a millisecond. These timings depend on the machine and the run.

::: {.misconception title="The regexes in a lexer are the same as the ones in Python or Perl"}
Many library regex engines add features such as backreferences, which match a repeat of earlier text and can describe nonregular languages [@F43], and use backtracking, which can go exponential [@F13]. Go's `regexp` package is one counterexample: it does not support backreferences [@F17] and is guaranteed to run in time linear in its input [@F16]. Lexer regexes are the strict regular subset, compiled to an automaton that takes one transition per character during recognition; longest-match scanning may reread characters after backing up [@F25].
:::

## From NFA to DFA: subset construction and minimization

The set simulation is linear, but it computes a new set for every character. Yet the set you could be in after some input depends only on the input, and we already saw one such set, {16, 18, 19}, behave exactly like a single DFA state. So why not compute every reachable set ahead of time, number each one, and record which set leads to which on each character? The result is a DFA in which each state stands for one set of NFA states [@F57], and running it costs one table lookup per character.

Building it takes two operations, and you have already done both by hand. The [ε-closure]{.term def="The set of NFA states reachable from a given set by ε-transitions alone, including the set itself."} of a set of states is everything reachable from it by ε-arrows, including the set itself [@F19]. It is the column headed "after following ε-arrows" in the `<=` trace. Move takes a set and a character, follows every arrow labelled with that character, and takes the ε-closure of the result, which is one whole row of that trace. The [subset construction]{.term def="The algorithm that builds a DFA whose states are the sets of NFA states reachable on some input."} starts from the ε-closure of the NFA's start state, then repeatedly takes an unprocessed set from a worklist, applies move on every character, and adds any new set it finds. Engineering a Compiler names the move step Delta [@F18]. The lab's version is `closure`, `move` and `subset`, lines 113 to 156 of `automata.py`.

Here is the DFA the lab built for all five rules. Each row is one DFA state. The second column lists the NFA states it stands for, the third shows the token kinds among them and the one priority chose, and the last six columns give the next DFA state for each kind of character. The column `other a-z` stands for every lowercase letter except `f` and `i`:

```{.output include="lab/automata/run.out" lines="5-17"}
```

State 3 holds the empty set. It is the dead state, reached once every possibility has died, as when the space arrived in the `iffy` trace, and every character leads from it back to itself. Leave it out, and the table draws as this machine:

```{.dot caption="The lab's DFA for the five rules, leaving out the dead state 3 that every missing arrow leads to."}
digraph {
  rankdir=LR; nodesep=0.25; ranksep=0.45;
  node [shape=doublecircle, fontsize=10, width=0.4, height=0.4, margin=0.02];
  edge [fontsize=10];
  entry [shape=point, width=0.06, label=""];
  d0 [shape=circle, label="0"];
  d1 [label="1\nINT"]; d2 [label="2\nLT"]; d6 [label="6\nLE"];
  d4 [label="4\nIDENT"]; d5 [label="5\nIDENT"]; d7 [label="7\nIDENT"]; d8 [label="8\nIF"];
  entry -> d0;
  d0 -> d1 [label="0-9"];
  d1 -> d1 [label="0-9"];
  d0 -> d2 [label="<"];
  d2 -> d6 [label="="];
  d0 -> d5 [label="i"];
  d0 -> d4 [label="a-z except i"];
  d5 -> d8 [label="f"];
  d5 -> d7 [label="a-z except f, 0-9"];
  d4 -> d7 [label="a-z, 0-9"];
  d8 -> d7 [label="a-z, 0-9"];
  d7 -> d7 [label="a-z, 0-9"];
}
```

Trace `if` on it, with the NFA figure for `IF` and `IDENT` beside you. DFA state 0 is the ε-closure of NFA state 0, which holds 1 and 5 from that figure along with the entries of the other three rules. On `i`, NFA state 1 moves to 2 and state 5 to 6, and the ε-closure adds 3, 7, 8 and 9, giving {2, 3, 6, 7, 8, 9}, the set listed for DFA state 5. On `f`, state 3 moves to 4 and state 9 to 10, and the closure adds 8 and 9, giving {4, 8, 9, 10}, which is DFA state 8.

NFA state 4 is the exit of `IF` and state 8 the exit of `IDENT`, so DFA state 8 accepts two kinds at once. It is the moment after `if` in the `iffy` trace, computed once and stored in a table row. The lab resolves the tie the way scanner generators do, by taking the highest-priority kind [@F26], so state 8 reports `IF`.

A DFA by itself only says whether a whole string is accepted. A lexer needs longest match too, so the scanning loop does what we did by hand with `x1<=y`. It keeps running past accepting states and remembers the last one it saw. When it reaches the dead state or the end of input it backs up to that last accepting position, which yields the longest valid prefix [@F25]. This can reread input: with rules `a` and `a*b`, scanning a run of `a`s with no final `b` repeatedly scans the remaining suffix, then backs up to emit one `a`, taking quadratic time. The lab's `scan`, at lines 177 to 194, uses the same last-accepting-position strategy. With rules for punctuation, spaces and comments added to the five above, it lexes the opening line into `IF IDENT LE INT LBRACE IDENT ASSIGN IDENT STAR INT RBRACE`.

The precomputation has a price. Each DFA state stands for a set of NFA states, and an $n$-state NFA has $2^n$ subsets, so the DFA may have exponentially more states than the NFA [@F20]. The classic witness is the language of strings whose $n$-th symbol from the end is a particular letter. An NFA with $n+1$ states recognises it, and no DFA with fewer than $2^n$ states does [@F21]. Intuitively, the DFA has to remember the last $n$ characters, because any of them might turn out to be the important one. The lab built `(a|b)*a` followed by $n-1$ copies of `(a|b)`:

```{.output include="lab/automata/run.out" lines="32-43"}
```

The NFA column grows by six per step, because Thompson's construction adds a few ε-states per operator, while the minimized DFA doubles. Our five token rules do not show this blowup: they became a 9-state DFA from a 21-state NFA.

Subset construction can produce more states than needed. [DFA minimization]{.term def="Merging the states of a DFA that no input string can tell apart, giving the smallest equivalent DFA."} merges states that behave the same on every possible future input; for a lexer, this must preserve token kinds as well as acceptance. The lab starts by grouping states by the token kind they accept, then splits any group whose members go to different groups on some character, and repeats until nothing changes. Before reading on, look at the table or the drawing again. Which two states have the same accepting kind and identical rows?

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
2. Using the lab's NFA for `LT` and `LE`, write the set of states after each character of `<<`, following ε-arrows each time. Where does the first token end, and what does the whole input lex to?
3. Using the DFA table in this chapter, trace the input `ifx`. Which states does the lexer pass through, and what token does it emit?
4. In C, how is `a---b` split into tokens, and is the result a valid expression?
5. A Go source line ends with `x +`. Does the lexer insert a semicolon after it? What does that mean for writing a long expression across several lines?
6. In flex, you put the rule `[a-z]+` above the rule `if`. Predict the warning and the token kind of `if`. Then predict what happens to `iffy` if the order is the other way around.
:::

::: answers
1. First match gives `<` for `<=` and keyword `if` followed by an identifier `fy` for `iffy`. Both are wrong. Longest match says `<=` and a single identifier `iffy`, and priority only decides between rules that match the same length.
2. The start set is {0, 15, 17}. The first `<` gives {16, 18, 19}, which accepts `LT`. The second `<` matches no arrow out of 16, 18 or 19, because 18 leaves only by an ε-arrow and 19 only on `=`, so the set becomes empty. The last accepting point was after one character, so the first token is `<`. Lexing restarts at the second `<` from {0, 15, 17}, reaches {16, 18, 19} again, and the input ends there, so the whole input is two `LT` tokens.
3. From state 0, `i` leads to state 5, `f` to state 8, and `x` falls in the `other a-z` column, leading to state 7. State 7 accepts `IDENT`, and the input ends, so the lexer emits one identifier `ifx`. The pass through state 8, where `IF` was the chosen kind, does not matter because a longer match came after it.
4. Longest match takes `a`, then `--`, then `-`, then `b`, giving `a -- - b` [@F4]. For an ordinary modifiable integer variable `a` and integer `b`, that is valid: it subtracts `b` from the old value of `a`, while decrementing `a` as a side effect [@F44; @F45; @F46].
5. No. `+` is not on the list of final tokens that trigger insertion, so the expression continues onto the next line. This is why Go style breaks long expressions after an operator rather than before it.
6. flex warns that the `if` rule cannot be matched, because the identifier rule above it matches the same text, and `if` comes out as an identifier. With `if` first, `iffy` is still a single identifier, because four characters beat two and order only breaks ties of equal length.
:::
