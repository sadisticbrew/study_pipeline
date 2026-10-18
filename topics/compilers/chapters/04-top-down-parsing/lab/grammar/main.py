from dataclasses import dataclass
from functools import cache
from pathlib import Path
import json

G1 = {"E": [("E", "-", "E"), ("E", "*", "E"), ("(", "E", ")"), ("num",)]}
G2 = {"Expr": [("Expr", "-", "Term"), ("Term",)],
      "Term": [("Term", "*", "Factor"), ("Factor",)],
      "Factor": [("(", "Expr", ")"), ("num",)]}
TOKENS = "10 - 4 - 3 * 2".split()
COLUMNS = ["num", "-", "*", "(", ")", "eof"]
EPS = "ε"


@dataclass(frozen=True)
class Tree:
    label: str
    children: tuple = ()


def parse_trees(grammar, tokens):
    active = set()

    @cache
    def parse(symbol, lo, hi):
        if symbol not in grammar:
            match = hi == lo + 1 and (tokens[lo].isdigit() if symbol == "num" else tokens[lo] == symbol)
            return (Tree(tokens[lo]),) if match else ()
        if (symbol, lo, hi) in active:
            return ()
        active.add((symbol, lo, hi))
        result = []
        for rhs in grammar[symbol]:
            for children in sequence(rhs, lo, hi):
                result.append(Tree(symbol, children))
        active.remove((symbol, lo, hi))
        return tuple(result)

    def sequence(rhs, lo, hi):
        if not rhs:
            return [()] if lo == hi else []
        result = []
        for end in range(lo + 1, hi - len(rhs) + 2):
            for child in parse(rhs[0], lo, end):
                for tail in sequence(rhs[1:], end, hi):
                    result.append((child,) + tail)
        return result

    return parse(next(iter(grammar)), 0, len(tokens))


def expression(tree):
    if not tree.children:
        return tree.label
    if len(tree.children) == 1:
        return expression(tree.children[0])
    left, op, right = tree.children
    if left.label == "(":
        return expression(op)
    return f"({expression(left)} {op.label} {expression(right)})"


def value(tree):
    text = expression(tree)
    # Only internally constructed numeric expressions reach this evaluator.
    return eval(text, {"__builtins__": {}}, {})


def derivation(root):
    frontier = [root]
    print(root.label)
    while any(node.children for node in frontier):
        index = next(i for i, node in enumerate(frontier) if node.children)
        node = frontier[index]
        rhs = " ".join("num" if c.label.isdigit() else c.label for c in node.children)
        frontier[index:index + 1] = node.children
        print(" ".join(c.label for c in frontier) + f"    [{node.label} → {rhs}]")


def eliminate(grammar):
    result = {}
    for lhs, alternatives in grammar.items():
        recursive = [rhs[1:] for rhs in alternatives if rhs[0] == lhs]
        plain = [rhs for rhs in alternatives if rhs[0] != lhs]
        if recursive:
            tail = lhs + "'"
            result[lhs] = [rhs + (tail,) for rhs in plain]
            result[tail] = [rhs + (tail,) for rhs in recursive] + [()]
        else:
            result[lhs] = alternatives
    return result


def first_sequence(rhs, first):
    result = set()
    for symbol in rhs:
        current = first.get(symbol, {symbol})
        result |= current - {EPS}
        if EPS not in current:
            break
    else:
        result.add(EPS)
    return result


def show_set(items):
    order = ["num", "-", "*", "(", ")", "eof", EPS]
    return "{" + ", ".join(x for x in order if x in items) + "}"


def fixed_sets(grammar, trace=False):
    first = {lhs: set() for lhs in grammar}
    follow = {lhs: set() for lhs in grammar}
    follow[next(iter(grammar))].add("eof")
    for mode, sets in [("FIRST", first), ("FOLLOW", follow)]:
        count = 0
        while True:
            before = {lhs: set(items) for lhs, items in sets.items()}
            for lhs, alternatives in grammar.items():
                for rhs in alternatives:
                    if mode == "FIRST":
                        first[lhs] |= first_sequence(rhs, first)
                    else:
                        for i, symbol in enumerate(rhs):
                            if symbol not in grammar:
                                continue
                            suffix = first_sequence(rhs[i + 1:], first)
                            follow[symbol] |= suffix - {EPS}
                            if EPS in suffix:
                                follow[symbol] |= follow[lhs]
            count += 1
            if trace:
                print(f"{mode} pass {count}: " + "  ".join(f"{lhs} {show_set(s)}" for lhs, s in sets.items()))
            if sets == before:
                if trace:
                    print(f"{mode} passes: {count}")
                break
    return first, follow


def predictive_table(grammar, first, follow, trace=False):
    rules, table = {}, {}
    for lhs, alternatives in grammar.items():
        for rhs in alternatives:
            number = len(rules) + 1
            rules[number] = (lhs, rhs)
            start = first_sequence(rhs, first)
            if EPS in start:
                start = (start - {EPS}) | follow[lhs]
            if trace:
                print(f"{number}: {lhs} → {' '.join(rhs) or EPS}; START {show_set(start)}")
            for token in COLUMNS:
                if token in start:
                    table.setdefault((lhs, token), []).append(number)
    return rules, table


def predictive_parse(grammar, rules, table, tokens):
    stack, remaining = ["eof", next(iter(grammar))], tokens + ["eof"]
    while stack:
        top = stack[-1]
        look = "num" if remaining[0].isdigit() else remaining[0]
        before = " ".join(reversed(stack)) + " | " + " ".join(remaining)
        stack.pop()
        if top in grammar:
            number, = table[top, look]
            rhs = rules[number][1]
            stack.extend(reversed(rhs))
            action = f"{number}: {top} → {' '.join(rhs) or EPS}"
        else:
            assert top == look
            action = "accept" if top == "eof" else "match " + remaining[0]
            remaining.pop(0)
        print(before + " | " + action)


def dot_tree(tree, lines, counter):
    name = f"n{counter[0]}"
    counter[0] += 1
    lines.append(f"{name} [label={json.dumps(tree.label, ensure_ascii=False)}];")
    for child in tree.children:
        child_name = dot_tree(child, lines, counter)
        lines.append(f"{name} -> {child_name};")
    return name


def write_dot(path, clusters):
    lines = ['digraph {', 'ordering=out;', 'node [width=0.3, height=0.3, margin=0.03];']
    counter = [0]
    for i, (label, tree) in enumerate(clusters):
        lines.extend([f"subgraph cluster_{i} {{", f"label={json.dumps(label, ensure_ascii=False)};"])
        dot_tree(tree, lines, counter)
        lines.append("}")
    lines.append("}")
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    Path("out").mkdir(exist_ok=True)
    trees = parse_trees(G1, TOKENS)
    for target in [0, 6]:
        tree = next(tree for tree in trees if value(tree) == target)
        print(f"== G1 leftmost derivation: value {target} ==")
        derivation(tree)
        write_dot(f"out/tree-{target}.dot", [(f"worth {target}", tree)])
    print("== G1 trees ==")
    for tree in trees:
        print(f"{expression(tree)} = {value(tree)}")
    print(f"G1 tree count: {len(trees)}")
    layered = parse_trees(G2, TOKENS)
    print("== G2 layered ==")
    print(f"G2 tree count: {len(layered)}")
    print(f"{expression(layered[0])} = {value(layered[0])}")
    write_dot("out/layered.dot", [("layered grammar", layered[0])])
    g3 = eliminate(G2)
    print("== G3 after direct left-recursion elimination ==")
    for lhs, alternatives in g3.items():
        print(lhs + " → " + " | ".join(" ".join(rhs) or EPS for rhs in alternatives))
    print("== G3 FIRST and FOLLOW ==")
    first, follow = fixed_sets(g3, trace=True)
    print("== G3 productions and START ==")
    rules, table = predictive_table(g3, first, follow, trace=True)
    print("== G3 LL(1) table ==")
    print(f"{'row':8}" + "".join(f"{c:>6}" for c in COLUMNS))
    for lhs in g3:
        print(f"{lhs:8}" + "".join(f"{','.join(map(str, table.get((lhs, c), []))) or '.':>6}" for c in COLUMNS))
    print("== G2 conflicting cells ==")
    first2, follow2 = fixed_sets(G2)
    rules2, table2 = predictive_table(G2, first2, follow2)
    for lhs in G2:
        for token in COLUMNS:
            numbers = table2.get((lhs, token), [])
            if len(numbers) > 1:
                print(f"[{lhs}, {token}]: " + "; ".join(f"{n}: {rules2[n][0]} → {' '.join(rules2[n][1])}" for n in numbers))
    print("== G3 predictive parse (stack top first) ==")
    predictive_parse(g3, rules, table, TOKENS)
    leaf = lambda label: Tree(label)
    tail = Tree("E'", (leaf("-"), leaf("4"), Tree("E'", (leaf("-"), leaf("3"), Tree("E'", (leaf(EPS),))))))
    rewritten = Tree("E", (leaf("10"), tail))
    folded = Tree("-", (Tree("-", (leaf("10"), leaf("4"))), leaf("3")))
    write_dot("out/rewritten.dot", [("E → num E', E' → - num E' | ε", rewritten), ("tree the loop builds", folded)])


if __name__ == "__main__":
    main()
