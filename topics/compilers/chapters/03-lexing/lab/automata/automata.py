"""Small regular-expression compiler; state numbers follow construction order."""
from time import perf_counter
import re
import sys


class Parser:
    # Grammar: alt := concat ('|' concat)*; concat := repeat*.
    def __init__(self, text):
        self.text, self.pos = text, 0

    def peek(self):
        return self.text[self.pos:self.pos + 1]

    def take(self):
        char = self.peek()
        self.pos += 1
        return char

    def parse(self):
        node = self.alt()
        if self.pos != len(self.text):
            raise ValueError("unexpected regex suffix")
        return node

    def alt(self):
        node = self.concat()
        while self.peek() == '|':
            self.take()
            node = ('alt', node, self.concat())
        return node

    def concat(self):
        nodes = []
        while self.peek() and self.peek() not in ')|':
            node = self.atom()
            while self.peek() and self.peek() in '*+?':
                node = (self.take(), node)
            nodes.append(node)
        node = ('eps',)
        for part in nodes:
            node = part if node == ('eps',) else ('cat', node, part)
        return node

    def atom(self):
        char = self.take()
        if char == '(':
            node = self.alt()
            if self.take() != ')':
                raise ValueError("missing closing parenthesis")
            return node
        if char == '[':
            chars = set()
            while self.peek() and self.peek() != ']':
                start = self.take()
                if self.peek() == '-':
                    self.take()
                    end = self.take()
                    if not end or ord(end) < ord(start):
                        raise ValueError("invalid character range")
                    chars.update(map(chr, range(ord(start), ord(end) + 1)))
                else:
                    chars.add(start)
            if self.take() != ']':
                raise ValueError("missing closing bracket")
            return ('chars', frozenset(chars))
        if char == '\\':
            char = self.take()
            if not char:
                raise ValueError("missing escaped character")
        elif char in ')|*+?]':
            raise ValueError("unexpected regex operator")
        return ('chars', frozenset(char))


class NFA:
    def __init__(self):
        self.edges, self.accept = [], {}

    def state(self):
        self.edges.append([])
        return len(self.edges) - 1

    def edge(self, start, chars, end):
        self.edges[start].append((chars, end))

    def build(self, node):
        kind = node[0]
        if kind in ('chars', 'eps'):
            start, end = self.state(), self.state()
            self.edge(start, node[1] if kind == 'chars' else None, end)
            return start, end
        if kind == 'cat':
            start, middle = self.build(node[1])
            other, end = self.build(node[2])
            self.edge(middle, None, other)
            return start, end
        start, end = self.state(), self.state()
        left, right = self.build(node[1])
        self.edge(start, None, left)
        self.edge(right, None, end)
        if kind == 'alt':
            left2, right2 = self.build(node[2])
            self.edge(start, None, left2)
            self.edge(right2, None, end)
        else:
            if kind in ('*', '?'):
                self.edge(start, None, end)
            if kind in ('*', '+'):
                self.edge(right, None, left)
        return start, end

    def closure(self, states):
        result, pending = set(states), list(states)
        while pending:
            for chars, end in self.edges[pending.pop()]:
                if chars is None and end not in result:
                    result.add(end)
                    pending.append(end)
        return frozenset(result)

    def move(self, states, char):
        return self.closure({end for state in states
                             for chars, end in self.edges[state]
                             if chars is not None and char in chars})


def compile_rules(rules):
    nfa = NFA()
    start = nfa.state()
    for priority, (name, regex) in enumerate(rules):
        entry, exit = nfa.build(Parser(regex).parse())
        nfa.edge(start, None, entry)
        nfa.accept[exit] = (priority, name)
    return nfa, start


def subset(nfa, start):
    alphabet = sorted({char for edges in nfa.edges
                       for chars, _ in edges if chars is not None for char in chars})
    states = [nfa.closure({start})]
    indices = {states[0]: 0}
    rows, accepting = [], []
    for stateset in states:
        candidates = sorted(nfa.accept[s] for s in stateset if s in nfa.accept)
        accepting.append(candidates[0][1] if candidates else None)
        row = {}
        for char in alphabet:
            target = nfa.move(stateset, char)
            # Include the empty subset as the rejecting sink.
            if target not in indices:
                indices[target] = len(states)
                states.append(target)
            row[char] = indices[target]
        rows.append(row)
    return alphabet, states, rows, accepting


def minimize(dfa):
    # Moore refinement preserves token kind, not merely accepting/rejecting.
    alphabet, states, rows, accepting = dfa
    kinds = {kind: i for i, kind in enumerate(dict.fromkeys(accepting))}
    groups = [kinds[kind] for kind in accepting]
    while True:
        signatures = {}
        refined = []
        for state, row in enumerate(rows):
            key = (accepting[state], tuple(groups[row[c]] for c in alphabet))
            if key not in signatures:
                signatures[key] = len(signatures)
            refined.append(signatures[key])
        if refined == groups:
            return len(signatures)
        groups = refined


def scan(dfa, text):
    _, states, rows, accepting = dfa
    pos = 0
    while pos < len(text):
        state, cursor, last = 0, pos, None
        while cursor < len(text) and text[cursor] in rows[state]:
            state = rows[state][text[cursor]]
            cursor += 1
            if accepting[state] is not None:
                last = cursor, accepting[state]
            if not states[state]:
                break
        if last is None:
            raise ValueError(f"no token at offset {pos}")
        end, kind = last
        if kind not in ('WS', 'COMMENT'):
            yield kind, text[pos:end]
        pos = end


def nfa_fullmatch(nfa, start, text):
    current = nfa.closure({start})
    for char in text:
        current = nfa.move(current, char)
    return any(state in nfa.accept for state in current)


RULES = [('IF', 'if'), ('IDENT', '[a-z][a-z0-9]*'),
         ('INT', '[0-9]+'), ('LT', '<'), ('LE', '<=')]
OPENING = 'if x1 <= 10 { y = x1 * 2 } // done'


def main():
    print('== Python ==')
    print(sys.version.splitlines()[0])
    nfa, start = compile_rules(RULES)
    dfa = subset(nfa, start)
    alphabet, states, rows, accepting = dfa
    print('\n== Running token automaton (complete DFA, including sink) ==')
    print(f'NFA states={len(nfa.edges)} edges={sum(map(len, nfa.edges))}')
    print('accept NFA states: ' + ', '.join(f'{s}:{name}' for s, (_, name) in nfa.accept.items()))
    print(f'DFA states={len(states)} minimized={minimize(dfa)}')
    classes = [('0-9', '0'), ('f', 'f'), ('i', 'i'), ('other a-z', 'a'), ('<', '<'), ('=', '=')]
    print('state | NFA set | accept candidates -> chosen | ' + ' '.join(name for name, _ in classes))
    for i, stateset in enumerate(states):
        candidates = [name for _, name in sorted(nfa.accept[s] for s in stateset if s in nfa.accept)]
        print(f'{i:2} | ' + ','.join(map(str, sorted(stateset))) + ' | '
              + '/'.join(candidates) + ' -> ' + str(accepting[i]) + ' | '
              + ' '.join(str(rows[i][char]) for _, char in classes))
    print('\n== Longest-match scan (five rules plus punctuation/trivia) ==')
    extra = [('LBRACE', '{'), ('RBRACE', '}'), ('ASSIGN', '='), ('STAR', r'\*'),
             ('SLASH', '/'), ('COMMENT', '//[a-z ]*'), ('WS', '[ \t\n]+')]
    full_nfa, full_start = compile_rules(RULES + extra)
    for kind, lexeme in scan(subset(full_nfa, full_start), OPENING):
        print(f'{kind:7} {lexeme!r}')
    print('\n== nth symbol from end is a: (a|b)*a(a|b)^(n-1) ==')
    print('n NFA DFA minimized 2^n')
    for n in range(1, 11):
        machine, entry = compile_rules([('MATCH', '(a|b)*a' + '(a|b)' * (n - 1))])
        deterministic = subset(machine, entry)
        print(n, len(machine.edges), len(deterministic[1]), minimize(deterministic), 2 ** n)
    print('\n== Measured fullmatch: a? repeated n, then a repeated n; input a^n ==')
    print('n re_ms NFA_ms re_match NFA_match')
    for n in (8, 12, 16, 20, 24):
        pattern = 'a?' * n + 'a' * n
        regex = re.compile(pattern)
        machine, entry = compile_rules([('MATCH', pattern)])
        before = perf_counter()
        backtrack = regex.fullmatch('a' * n) is not None
        middle = perf_counter()
        simulated = nfa_fullmatch(machine, entry, 'a' * n)
        after = perf_counter()
        print(f'{n} {(middle-before)*1000:.3f} {(after-middle)*1000:.3f} {backtrack} {simulated}')


if __name__ == '__main__':
    main()
