from functools import cache


@cache
def trees(tokens):
    if len(tokens) == 1:
        return [(tokens[0], int(tokens[0]))]
    result = []
    for split in range(1, len(tokens), 2):
        op = tokens[split]
        for left, a in trees(tokens[:split]):
            for right, b in trees(tokens[split + 1:]):
                value = {"+": lambda: a + b, "-": lambda: a - b,
                         "*": lambda: a * b}[op]()
                result.append((f"({left} {op} {right})", value))
    return result


def eliminate(grammar):
    rewritten = {}
    for lhs, alternatives in grammar.items():
        recursive = [rhs[1:] for rhs in alternatives if rhs[0] == lhs]
        if not recursive:
            rewritten[lhs] = alternatives
            continue
        tail = lhs + "'"
        rewritten[lhs] = [rhs + (tail,) for rhs in alternatives if rhs[0] != lhs]
        rewritten[tail] = [rhs + (tail,) for rhs in recursive] + [()]
    return rewritten


def analyze(grammar):
    nullable = set()
    first = {lhs: set() for lhs in grammar}
    follow = {lhs: set() for lhs in grammar}
    follow["E"].add("$")

    def sequence(rhs):
        starts = set()
        for symbol in rhs:
            starts |= first[symbol] if symbol in grammar else {symbol}
            if symbol not in nullable:
                return starts, False
        return starts, True

    changed = True
    while changed:
        before = (len(nullable), sum(map(len, first.values())))
        for lhs, alternatives in grammar.items():
            for rhs in alternatives:
                starts, empty = sequence(rhs)
                first[lhs] |= starts
                if empty:
                    nullable.add(lhs)
        changed = before != (len(nullable), sum(map(len, first.values())))
    changed = True
    while changed:
        before = sum(map(len, follow.values()))
        for lhs, alternatives in grammar.items():
            for rhs in alternatives:
                for index, symbol in enumerate(rhs):
                    if symbol not in grammar:
                        continue
                    starts, empty = sequence(rhs[index + 1:])
                    follow[symbol] |= starts
                    if empty:
                        follow[symbol] |= follow[lhs]
        changed = before != sum(map(len, follow.values()))
    table, lookaheads = {}, []
    for lhs, alternatives in grammar.items():
        for rhs in alternatives:
            starts, empty = sequence(rhs)
            predict = starts | (follow[lhs] if empty else set())
            lookaheads.append((lhs, rhs, predict))
            for token in sorted(predict):
                table.setdefault((lhs, token), []).append(rhs)
    return nullable, first, follow, lookaheads, table


def symbols(items):
    return "{" + ", ".join(sorted(items)) + "}"


def production(lhs, rhs):
    return lhs + " -> " + (" ".join(rhs) or "epsilon")


def show_sets(grammar, analysis):
    nullable, first, follow, _, _ = analysis
    print("nullable =", symbols(nullable))
    for lhs in grammar:
        print(f"{lhs}: FIRST={symbols(first[lhs])} FOLLOW={symbols(follow[lhs])}")


def parse(grammar, table, tokens):
    stack, remaining = ["$", "E"], list(tokens) + ["$"]
    while stack:
        top, lookahead = stack[-1], remaining[0]
        if top == lookahead:
            action = "accept" if top == "$" else "match " + lookahead
            rhs = None
        else:
            choices = table.get((top, lookahead), [])
            if len(choices) != 1:
                raise ValueError(f"table[{top}, {lookahead}] = {choices}")
            rhs = choices[0]
            action = production(top, rhs)
        print(f"{' '.join(reversed(stack)):<22} | {' '.join(remaining):<25} | {action}")
        stack.pop()
        if rhs is None:
            remaining.pop(0)
        else:
            stack.extend(reversed(rhs))


grammar = {
    "E": [("E", "+", "T"), ("E", "-", "T"), ("T",)],
    "T": [("T", "*", "F"), ("T", "/", "F"), ("F",)],
    "F": [("(", "E", ")"), ("num",), ("id",)],
}
print("== Ambiguous E -> E + E | E - E | E * E | num ==")
all_trees = trees(tuple("10 - 4 - 3 * 2".split()))
for tree, value in all_trees:
    print(f"{tree} = {value}")
print("trees =", len(all_trees))
print("\n== Left-recursive sets and conflicting table cells ==")
analysis = analyze(grammar)
show_sets(grammar, analysis)
for (lhs, token), alternatives in sorted(analysis[4].items()):
    if len(alternatives) > 1:
        print(f"[{lhs}, {token}]: " + " | ".join(production(lhs, rhs) for rhs in alternatives))
print("\n== Mechanically rewritten grammar ==")
rewritten = eliminate(grammar)
for lhs, alternatives in rewritten.items():
    print(lhs + " -> " + " | ".join(" ".join(rhs) or "epsilon" for rhs in alternatives))
print("\n== Rewritten nullable, FIRST, FOLLOW and FIRST+ ==")
analysis = analyze(rewritten)
show_sets(rewritten, analysis)
for lhs, rhs, predict in analysis[3]:
    print(f"FIRST+({production(lhs, rhs)}) = {symbols(predict)}")
print("\n== Full rewritten LL(1) table (one row per nonterminal) ==")
for lhs in rewritten:
    cells = [f"{token}: {' '.join(rhs[0]) or 'epsilon'}"
             for (row, token), rhs in sorted(analysis[4].items()) if row == lhs]
    print(lhs + " | " + " ; ".join(cells))
print("conflicting cells =", sum(len(rhs) > 1 for rhs in analysis[4].values()))
print("\n== Predictive trace (stack top at left) ==")
parse(rewritten, analysis[4], "num - num - num * num".split())
