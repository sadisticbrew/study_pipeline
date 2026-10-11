#!/usr/bin/env python3
"""Lint a chapter for format errors and sloppy prose.

Usage:
  python3 tools/lint.py <chapter.md> [--json] [--config style/lint.toml]
                        [--facts F] [--sources S] [--topic-dir D] [--base-dir B]
                        [--words MIN,MAX] [--no-context]

Checks the conventions in style/FORMAT.md (front matter, crux/selftest/answers blocks,
code includes and sketches, lab output freshness, citations, terms, acronyms, word
budget) and the prose style rules configured in style/lint.toml.

Context, unless overridden or --no-context is given: facts from <chapter dir>/facts.jsonl;
sources from <chapter dir>/sources.jsonl, else <chapter dir>/../../sources.jsonl; topic dir
(glossary.jsonl, state.json) is <chapter dir>/../.. when the path looks like
topics/<slug>/chapters/<NN-slug>/chapter.md. Includes resolve against --base-dir
(default: the chapter file's directory).

Output: one finding per line as LINE:RULE:severity: message, an excerpt line, then a
summary. --json prints one JSON object instead. Findings about prose carry the line range
of the paragraph so only that paragraph needs rewriting.

Exit status: 0 no errors, 1 at least one error-severity finding, 2 usage or IO problem.
"""

import argparse
import bisect
import json
import os
import re
import sys
import tomllib
from pathlib import Path

from lab import lab_hash  # tools/ is sys.path[0] when run as tools/lint.py

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "style" / "lint.toml"

# Built-in severities; style/lint.toml [severity] overrides them.
DEFAULT_SEVERITY = {
    "front-matter": "error",
    "heading": "error",
    "div": "error",
    "crux": "error",
    "selftest": "error",
    "check-yourself": "error",
    "code-block": "error",
    "sketch-length": "error",
    "include": "error",
    "include-length": "error",
    "code-total": "warning",
    "lab-output": "error",
    "citation": "error",
    "fact-source": "error",
    "facts-missing": "warning",
    "unverified": "info",
    "term-def": "error",
    "term-before-mark": "error",
    "term-duplicate": "error",
    "term-glossary": "warning",
    "acronym": "warning",
    "word-budget": "error",
    "word-budget-low": "warning",
    "semicolon": "error",
    "parentheses": "error",
    "short-sentences": "error",
    "dashes": "error",
    "stock-phrase": "error",
    "contrast-frame": "warning",
    "rhetorical-question": "warning",
    "wall-of-text": "warning",
    "list-heavy": "warning",
    "exclamation": "warning",
}


class UsageError(Exception):
    """Bad arguments or unreadable input: exit status 2."""


# ---------------------------------------------------------------------------
# Text with a source position for every character.
# ---------------------------------------------------------------------------

class M:
    """A string plus the (line, col) in the source file of every character."""

    __slots__ = ("s", "pos")

    def __init__(self, s, pos):
        self.s = s
        self.pos = pos

    def at(self, i):
        if not self.pos:
            return (0, 0)
        return self.pos[min(max(i, 0), len(self.pos) - 1)]

    def sub(self, rx, fn):
        """Like re.sub. fn(match) returns pieces: str (positioned at the match start),
        int (keep that group with its positions) or M (splice in)."""
        out, opos, last = [], [], 0
        for m in rx.finditer(self.s):
            out.append(self.s[last:m.start()])
            opos.extend(self.pos[last:m.start()])
            here = self.at(m.start())
            for piece in fn(m):
                if isinstance(piece, str):
                    out.append(piece)
                    opos.extend([here] * len(piece))
                elif isinstance(piece, int):
                    a, b = m.span(piece)
                    if a >= 0:
                        out.append(self.s[a:b])
                        opos.extend(self.pos[a:b])
                else:
                    out.append(piece.s)
                    opos.extend(piece.pos)
            last = m.end()
        out.append(self.s[last:])
        opos.extend(self.pos[last:])
        return M("".join(out), opos)

    def translate(self, table):
        """Character-for-character replacement (keeps positions)."""
        return M(self.s.translate(table), self.pos)

    def slice(self, a, b):
        return M(self.s[a:b], self.pos[a:b])

    def index_of(self, pos):
        """First index whose source position is at or after pos."""
        return bisect.bisect_left(self.pos, pos)


# ---------------------------------------------------------------------------
# Regular expressions.
# ---------------------------------------------------------------------------

FENCE_RX = re.compile(r"^(\s*)(`{3,}|~{3,})\s*(.*?)\s*$")
DIV_RX = re.compile(r"^(:{3,})(.*)$")
HEAD_RX = re.compile(r"^(#{1,6})(?:\s+(.*?))?(?:\s+#+)?\s*$")
LIST_RX = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)]|#[.)])(?:(\s+)(.*))?$")
HR_RX = re.compile(r"^(?:([-*_])\s*)(?:\1\s*){2,}$")
ATTR_TOKEN_RX = re.compile(
    r"""\s*(?:\.([\w-]+)|\#([\w:.-]+)|([\w-]+)=("(?:[^"\\]|\\.)*"|'[^']*'|[^\s"'}]+))"""
)

CODE_RX = re.compile(r"(`+)(?!`)([\s\S]*?[^`])\1(?!`)")
PH_RX = re.compile("\ue000(\\d+)\ue001")
CITE_RX = re.compile(r"\[(?:[^\[\]]*?[\s;])?-?@[A-Za-z0-9_][^\[\]]*\](?![({])")
CITE_ID_RX = re.compile(r"(?:^|[\s;\[])-?@([A-Za-z0-9_](?:[\w-]*\w)?)")
SPAN_RX = re.compile(r"(?<!!)\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\{([^{}]*)\}")
IMG_RX = re.compile(r"!\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)")
LINK_RX = re.compile(r"\[([^\]]+)\]\((?:[^()]|\([^()]*\))*\)")
REFLINK_RX = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
AUTOLINK_RX = re.compile(r"<(?:https?|mailto|ftp):[^>\s]+>")
DMATH_RX = re.compile(r"\$\$[\s\S]+?\$\$")
IMATH_RX = re.compile(r"(?<![\\$])\$(?=\S)[^$\n]*?\S\$(?!\d)")
EMPH_RX = re.compile(r"\*+|(?<!\w)_+(?=\S)|(?<=\S)_+(?!\w)|~~")
ESC_RX = re.compile(r"\\([!-/:-@\[-`{-~])")
SPACE_PUNCT_RX = re.compile(r"[ \t]+(?=[.,;:!?)])")
QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})

WORD_RX = re.compile(r"\S*[A-Za-z0-9]\S*")
SENT_END_RX = re.compile(r"[.!?]+[\"')\]]*\s+(?=[\"(\[]?[A-Z0-9])")
ABBREV = {"e.g", "i.e", "vs", "cf", "dr", "mr", "mrs", "ms", "fig", "no", "approx", "al", "st"}
DASH_RX = re.compile(r"\u2014|---|(?<!\S)(?:\u2013|--)|(?:\u2013|--)(?!\S)")
ACR_RX = re.compile(r"(?<![\w/&-])([A-Z][A-Z0-9]*(?:[/&-][A-Z0-9]+)*)(?:s|'s)?(?![\w/&-])")
PAREN_ACR_RX = re.compile(r"^[A-Z][A-Z0-9]*(?:[/&-][A-Z0-9]+)*(?:s|'s)?$")
PAREN_ENUM_RX = re.compile(r"^(?:\d{1,2}|[a-z]|[ivx]{1,4})$")

CODE_WORD = "Code"   # what inline code reads as in the prose view
MATH_WORD = "math"


def words(text):
    return len(WORD_RX.findall(text))


def parse_attrs(text):
    """Parse a Pandoc attribute string. Returns (classes, kv, ok)."""
    classes, kv, i = [], {}, 0
    text = text.strip()
    while i < len(text):
        m = ATTR_TOKEN_RX.match(text, i)
        if not m or m.end() == i:
            return classes, kv, False
        if m.group(1):
            classes.append(m.group(1))
        elif m.group(3):
            v = m.group(4)
            if v.startswith('"'):
                v = v[1:-1]
            elif v.startswith("'"):
                v = v[1:-1]
            kv[m.group(3)] = v
        i = m.end()
        while i < len(text) and text[i].isspace():
            i += 1
    return classes, kv, True


def parse_info(info):
    """Code fence info string -> (classes, kv, ok)."""
    info = info.strip()
    if not info:
        return [], {}, True
    if info.startswith("{"):
        if not info.endswith("}"):
            return [], {}, False
        return parse_attrs(info[1:-1])
    return [info.split()[0].lstrip(".")], {}, True


# ---------------------------------------------------------------------------
# Document model.
# ---------------------------------------------------------------------------

class Para:
    def __init__(self, kind, divs, item=None, run=None):
        self.kind = kind          # prose | item | cont | table | quote
        self.divs = divs          # tuple of enclosing div indices, outermost first
        self.item = item          # {"ordered": bool, "indent": int} for list items
        self.run = run            # list run id for list items and continuations
        self.segs = []            # (line, col, text)
        self.vis = self.prose = None
        self.cites = []           # (id, (line, col))
        self.spans = []           # {"text", "attrs", "classes", "pos", "ok"}

    @property
    def start(self):
        return self.segs[0][0]

    @property
    def end(self):
        return self.segs[-1][0]

    def raw(self):
        chars, pos = [], []
        for k, (ln, col, text) in enumerate(self.segs):
            if k:
                chars.append("\n")
                p = self.segs[k - 1]
                pos.append((p[0], p[1] + len(p[2])))
            chars.append(text)
            pos.extend((ln, col + j) for j in range(len(text)))
        return M("".join(chars), pos)


class Doc:
    def __init__(self, lines):
        self.lines = lines
        self.fm = {}
        self.fm_end = 0
        self.paras = []
        self.headings = []        # (level, text, line)
        self.divs = []            # {"classes", "kv", "start", "end", "parent"}
        self.codes = []           # {"start", "end", "info", "classes", "kv", "ok", "body"}
        self.problems = []        # (rule, line, message, para_range)


def strip_comments(line, in_comment):
    out, i = [], 0
    while i < len(line):
        if in_comment:
            j = line.find("-->", i)
            if j < 0:
                out.append(" " * (len(line) - i))
                return "".join(out), True
            out.append(" " * (j + 3 - i))
            i = j + 3
            in_comment = False
        else:
            j = line.find("<!--", i)
            if j < 0:
                out.append(line[i:])
                break
            out.append(line[i:j])
            i = j
            in_comment = True
    return "".join(out), in_comment


def parse(text):
    lines = [ln.expandtabs(4) for ln in text.split("\n")]
    if lines and lines[-1] == "":
        lines.pop()
    doc = Doc(lines)
    n = len(lines)

    # Front matter.
    if n and lines[0].strip() == "---":
        for i in range(1, n):
            if lines[i].strip() in ("---", "..."):
                doc.fm_end = i + 1
                break
        if doc.fm_end:
            for i in range(1, doc.fm_end - 1):
                m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*$", lines[i])
                if m:
                    v = m.group(2)
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                        v = v[1:-1]
                    doc.fm[m.group(1)] = v
        else:
            doc.problems.append(("front-matter", 1, "front matter opened with --- is never closed", None))

    cur = None
    stack = []
    code = None
    icode = False
    in_comment = False
    comment_line = 0
    list_ctx = False
    run = 0
    blank = True

    def flush():
        nonlocal cur
        if cur is not None and cur.segs:
            doc.paras.append(cur)
        cur = None

    for idx in range(doc.fm_end, n):
        ln = idx + 1
        raw = lines[idx]
        if code is not None:
            m = re.match(r"^\s*(`{3,}|~{3,})\s*$", raw)
            if m and m.group(1)[0] == code["char"] and len(m.group(1)) >= code["len"]:
                code["end"] = ln
                doc.codes.append(code)
                code = None
            else:
                code["body"].append(raw)
            continue
        was_comment = in_comment
        eff, in_comment = strip_comments(raw, in_comment)
        if in_comment and not was_comment:
            comment_line = ln
        s = eff.strip()
        indent = len(eff) - len(eff.lstrip(" "))

        if not s:
            flush()
            blank = True
            continue
        if icode:
            if indent >= 4:
                continue
            icode = False

        fm = FENCE_RX.match(eff)
        if fm and not (fm.group(2)[0] == "`" and "`" in fm.group(3)):
            flush()
            classes, kv, ok = parse_info(fm.group(3))
            code = {"start": ln, "end": None, "char": fm.group(2)[0], "len": len(fm.group(2)),
                    "info": fm.group(3), "classes": classes, "kv": kv, "ok": ok,
                    "body": [], "divs": tuple(stack)}
            if len(fm.group(1)) < 2:
                list_ctx = False
            blank = False
            continue

        dm = DIV_RX.match(s)
        if dm:
            flush()
            rest = re.sub(r"\s*:+$", "", dm.group(2).strip()).strip()
            if not rest:
                if stack:
                    doc.divs[stack.pop()]["end"] = ln
                else:
                    doc.problems.append(("div", ln, "closing ::: fence without an open block; "
                                         "remove it", (ln, ln)))
            else:
                if rest.startswith("{"):
                    ok = rest.endswith("}")
                    classes, kv, ok2 = parse_attrs(rest[1:-1]) if ok else ([], {}, False)
                    ok = ok and ok2
                else:
                    classes, kv, ok = [rest.split()[0]], {}, True
                if not ok:
                    doc.problems.append(("div", ln, f"cannot parse block attributes `{rest}`; "
                                         "use `::: name` or `::: {.name title=\"...\"}`", (ln, ln)))
                doc.divs.append({"classes": classes, "kv": kv, "start": ln, "end": None,
                                 "parent": stack[-1] if stack else None})
                stack.append(len(doc.divs) - 1)
            list_ctx = False
            blank = True
            continue

        hm = HEAD_RX.match(s)
        if hm and indent < 4:
            flush()
            title = re.sub(r"\s*\{[^}]*\}\s*$", "", hm.group(2) or "")
            doc.headings.append((len(hm.group(1)), title, ln))
            list_ctx = False
            blank = True
            continue

        if cur is not None and cur.kind in ("prose", "quote") and len(cur.segs) == 1 \
                and re.fullmatch(r"=+|-+", s):
            doc.headings.append((1 if s[0] == "=" else 2, cur.segs[0][2].strip(), cur.start))
            cur = None
            continue

        if cur is None and HR_RX.match(s):
            blank = True
            continue

        if cur is None and blank and indent >= 4 and not list_ctx:
            doc.problems.append(("code-block", ln, "indented code block; use a fenced block with "
                                 "include= or .sketch (see style/FORMAT.md)", (ln, ln)))
            icode = True
            continue

        lm = LIST_RX.match(eff)
        if lm and (cur is None or cur.kind in ("item", "cont")):
            flush()
            if not list_ctx:
                run += 1
            list_ctx = True
            marker = lm.group(2)
            content = lm.group(4) or ""
            col = len(eff) - len(content) if content else len(eff)
            cur = Para("item", tuple(stack), {"ordered": marker[0].isdigit() or marker[0] == "#",
                                               "indent": len(lm.group(1))}, run)
            cur.segs.append((ln, col, content))
            blank = False
            continue

        if s.startswith("|"):
            if re.fullmatch(r"\|?[\s:|-]+\|?", s):
                blank = False
                continue
            if cur is None or cur.kind != "table":
                flush()
                cur = Para("table", tuple(stack))
                list_ctx = False
            cur.segs.append((ln, indent, s))
            blank = False
            continue

        if s.startswith(">"):
            body = re.sub(r"^>\s?", "", s)
            if cur is None or cur.kind != "quote":
                flush()
                cur = Para("quote", tuple(stack))
                list_ctx = False
            cur.segs.append((ln, indent + (len(s) - len(body)), body))
            blank = False
            continue

        if cur is not None and cur.kind != "table":
            cur.segs.append((ln, indent, s))
        else:
            flush()
            if list_ctx and indent >= 2:
                cur = Para("cont", tuple(stack), None, run)
            else:
                list_ctx = False
                cur = Para("prose", tuple(stack))
            cur.segs.append((ln, indent, s))
        blank = False

    flush()
    if code is not None:
        doc.problems.append(("code-block", code["start"], "code fence is never closed", (code["start"], n)))
    if in_comment:
        doc.problems.append(("code-block", comment_line, "HTML comment is never closed (missing -->)",
                             (comment_line, n)))
    for d in stack:
        div = doc.divs[d]
        doc.problems.append(("div", div["start"], f"::: {' '.join(div['classes'])} block is never "
                             "closed; add a line with ::: after its body", (div["start"], n)))
        div["end"] = n
    return doc


# ---------------------------------------------------------------------------
# Inline cleaning: raw paragraph -> visible text and prose view.
# ---------------------------------------------------------------------------

def finish(m, codes, keep_code):
    m = m.sub(EMPH_RX, lambda x: [])
    m = m.sub(ESC_RX, lambda x: [1])
    m = m.translate(QUOTES)
    m = m.sub(SPACE_PUNCT_RX, lambda x: [])
    if keep_code:
        return m.sub(PH_RX, lambda x: [codes[int(x.group(1))]])
    return m.sub(PH_RX, lambda x: [CODE_WORD])


def clean(para):
    raw = para.raw()
    codes = []

    def ph(x):
        a, b = x.span(2)
        body = raw.slice(a, b)
        lead = len(body.s) - len(body.s.lstrip())
        trail = len(body.s.rstrip())
        codes.append(body.slice(lead, max(lead, trail)))
        return [f"\ue000{len(codes) - 1}\ue001"]

    c = raw.sub(CODE_RX, ph)
    for x in CITE_RX.finditer(c.s):
        for cid in CITE_ID_RX.findall(x.group(0)):
            para.cites.append((cid, c.at(x.start())))
    c = c.sub(CITE_RX, lambda x: [])

    def span(x):
        classes, kv, ok = parse_attrs(x.group(2))
        para.spans.append({"text": c.slice(*x.span(1)), "classes": classes, "kv": kv, "ok": ok,
                           "pos": c.at(x.start(1)) if x.group(1) else c.at(x.start()),
                           "attrs": x.group(2)})
        return [1]

    c = c.sub(SPAN_RX, span)
    c = c.sub(IMG_RX, lambda x: [1])
    c = c.sub(LINK_RX, lambda x: [1])
    c = c.sub(REFLINK_RX, lambda x: [1])
    c = c.sub(AUTOLINK_RX, lambda x: ["link"])
    c = c.sub(DMATH_RX, lambda x: [])
    c = c.sub(IMATH_RX, lambda x: [MATH_WORD])
    if para.kind == "table":
        c = c.sub(re.compile(r"\|"), lambda x: [" "])
    para.vis = finish(c, codes, True)
    para.prose = finish(c, codes, False)
    for sp in para.spans:
        sp["vis"] = " ".join(finish(sp["text"], codes, True).s.split())


def sentences(m):
    """Split a prose view into (start, end) sentence spans."""
    out, start = [], 0
    s = m.s
    for x in SENT_END_RX.finditer(s):
        before = s[start:x.start() + 1]
        wm = re.search(r"([A-Za-z.]+)\.$", before)
        if wm and s[x.start()] == "." and wm.group(1).lower().rstrip(".") in ABBREV:
            continue
        out.append((start, x.end()))
        start = x.end()
    if s[start:].strip():
        out.append((start, len(s)))
    return [(a, b) for a, b in out if s[a:b].strip()]


# ---------------------------------------------------------------------------
# Context files.
# ---------------------------------------------------------------------------

def load_jsonl(path):
    out = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise UsageError(f"cannot read {path}: {e.strerror}")
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise UsageError(f"{path}:{i}: invalid JSON: {e.msg}")
        if not isinstance(obj, dict):
            raise UsageError(f"{path}:{i}: expected a JSON object per line")
        out.append(obj)
    return out


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise UsageError(f"cannot read {path}: {e.strerror}")
    except json.JSONDecodeError as e:
        raise UsageError(f"{path}: invalid JSON: {e.msg} (line {e.lineno})")


def phrase_regex(p):
    if p.startswith("re:"):
        return re.compile(p[3:], re.I)
    body = r"\s+".join(re.escape(w).replace("'", "['\u2019]") for w in p.split())
    if p[0].isalnum():
        body = r"(?<![\w-])" + body
    if p[-1].isalnum():
        body += r"(?![\w-])"
    return re.compile(body, re.I)


def term_regex(name):
    ws = name.lower().split()
    if not ws:
        return None
    last = ws[-1]
    forms = {last, last + "s", last + "es"}
    if last.endswith("s"):
        forms.add(last[:-1])
    if last.endswith("es"):
        forms.add(last[:-2])
    if last.endswith("y"):
        forms.add(last[:-1] + "ies")
    if last.endswith("ies"):
        forms.add(last[:-3] + "y")
    forms.discard("")
    head = r"[\s-]+".join(re.escape(w) for w in ws[:-1])
    tail = "(?:" + "|".join(sorted((re.escape(f) for f in forms), key=len, reverse=True)) + ")"
    body = (head + r"[\s-]+" + tail) if head else tail
    return re.compile(r"(?<![\w-])" + body + r"(?![\w-])", re.I)


# ---------------------------------------------------------------------------
# The linter.
# ---------------------------------------------------------------------------

class Linter:
    def __init__(self, path, doc, cfg, ctx):
        self.path = path
        self.doc = doc
        self.cfg = cfg
        self.ctx = ctx
        self.findings = []
        sev = dict(DEFAULT_SEVERITY)
        for k, v in (cfg.get("severity") or {}).items():
            if v not in ("error", "warning", "info", "off"):
                raise UsageError(f"config: severity for {k} must be error, warning, info or off")
            sev[k] = v
        self.sev = sev

    def c(self, section, key, default):
        return (self.cfg.get(section) or {}).get(key, default)

    # -- reporting --------------------------------------------------------
    def excerpt(self, line, col=None):
        if not line or line > len(self.doc.lines):
            return ""
        text = self.doc.lines[line - 1]
        if col is None:
            col = len(text) - len(text.lstrip())
        start = max(0, col - 40)
        if start:
            sp = text.rfind(" ", 0, start + 1)
            start = sp + 1 if sp >= col - 60 and sp >= 0 else start
        end = min(len(text), start + 120)
        out = " ".join(text[start:end].split())
        return ("..." if start else "") + out + ("..." if end < len(text) else "")

    def add(self, rule, line, message, para_range=None, col=None):
        sev = self.sev.get(rule, "error")
        if sev == "off":
            return
        self.findings.append({
            "rule": rule, "severity": sev, "line": line,
            "paragraph_start": para_range[0] if para_range else None,
            "paragraph_end": para_range[1] if para_range else None,
            "message": message, "excerpt": self.excerpt(line, col) if para_range else "",
        })

    def addp(self, rule, para, pos, message):
        """Finding about prose inside para at source position pos=(line, col)."""
        line, col = pos if pos and pos[0] else (para.start, None)
        self.add(rule, line, message, (para.start, para.end), col)

    # -- helpers ----------------------------------------------------------
    def div_classes(self, para):
        return {cl for d in para.divs for cl in self.doc.divs[d]["classes"]}

    def styled(self):
        return [p for p in self.doc.paras if p.kind != "table" and p.prose.s.strip()]

    # -- run --------------------------------------------------------------
    def run(self):
        doc = self.doc
        for p in doc.paras:
            clean(p)
        for rule, line, msg, rng in doc.problems:
            self.add(rule, line, msg, rng)
        self.front_matter()
        self.headings()
        self.structure()
        self.code_blocks()
        self.citations()
        self.terms()
        self.acronyms()
        self.budget()
        self.style()
        self.findings.sort(key=lambda f: (f["line"] or 0, f["rule"]))

    # -- format rules -----------------------------------------------------
    def front_matter(self):
        doc = self.doc
        if not doc.fm_end:
            if not any(r == "front-matter" for r, *_ in doc.problems):
                self.add("front-matter", 1, "missing front matter; start the file with ---, "
                         "topic:, chapter:, title:, ---")
            return
        rng = (1, doc.fm_end)
        for key in ("topic", "chapter", "title"):
            if not doc.fm.get(key):
                self.add("front-matter", 1, f"front matter has no `{key}:`", rng)
        ch = doc.fm.get("chapter")
        if ch and not re.fullmatch(r"\d+", ch):
            self.add("front-matter", 1, f"front matter `chapter: {ch}` must be an integer", rng)

    def headings(self):
        for level, title, line in self.doc.headings:
            if level == 1:
                self.add("heading", line, "level-1 heading; the title comes from front matter, "
                         "use ## for sections", (line, line))
            elif level > 3:
                self.add("heading", line, f"level-{level} heading; use ## sections and ### "
                         "subsections at most", (line, line))

    def structure(self):
        doc = self.doc
        known = set(self.c("divs", "known", DEFAULT_KNOWN_DIVS))
        by_class = {}
        for i, d in enumerate(doc.divs):
            rng = (d["start"], d["end"])
            if not any(cl in known for cl in d["classes"]):
                self.add("div", d["start"], f"unknown block `::: {' '.join(d['classes']) or '?'}`; "
                         f"use one of: {', '.join(sorted(known))}", rng)
            for cl in d["classes"]:
                by_class.setdefault(cl, []).append(i)

        crux = by_class.get("crux", [])
        if not crux:
            self.add("crux", 1, "no ::: crux block; add one after the opening paragraphs "
                     "with the chapter's central question")
        for i in crux[1:]:
            d = doc.divs[i]
            self.add("crux", d["start"], "more than one ::: crux block; keep exactly one",
                     (d["start"], d["end"]))

        counts = {}
        for name in ("selftest", "answers"):
            found = by_class.get(name, [])
            if not found:
                self.add("selftest", 1, f"no ::: {name} block; the chapter needs one "
                         "::: selftest and one ::: answers block")
                continue
            for i in found[1:]:
                d = doc.divs[i]
                self.add("selftest", d["start"], f"more than one ::: {name} block; keep exactly one",
                         (d["start"], d["end"]))
            i = found[0]
            d = doc.divs[i]
            rng = (d["start"], d["end"])
            inside = [p for p in doc.paras if p.divs and p.divs[-1] == i]
            items = [p for p in inside if p.kind == "item"]
            if not items:
                self.add("selftest", d["start"], f"::: {name} must hold an ordered list "
                         "(1. 2. 3.)", rng)
                continue
            top = min(p.item["indent"] for p in items)
            top_items = [p for p in items if p.item["indent"] == top]
            if any(not p.item["ordered"] for p in top_items):
                bad = next(p for p in top_items if not p.item["ordered"])
                self.add("selftest", bad.start, f"::: {name} must be an ordered list; "
                         "number the items 1. 2. 3.", (bad.start, bad.end))
            for p in inside:
                if p.kind in ("prose", "quote", "table"):
                    self.add("selftest", p.start, f"only the numbered list may appear inside "
                             f"::: {name}; move this text out or into an item", (p.start, p.end))
            counts[name] = (len(top_items), d)
        if len(counts) == 2 and counts["selftest"][0] != counts["answers"][0]:
            d = counts["answers"][1]
            self.add("selftest", d["start"], f"selftest has {counts['selftest'][0]} questions but "
                     f"answers has {counts['answers'][0]}; give one answer per question, same order",
                     (d["start"], d["end"]))

        check = [(lv, t, ln) for lv, t, ln in doc.headings
                 if lv == 2 and t.strip().lower() == "check yourself"]
        if not check:
            self.add("check-yourself", 1, "no `## Check yourself` heading; put the ::: selftest "
                     "block under it")
        elif by_class.get("selftest"):
            hline = check[0][2]
            sline = doc.divs[by_class["selftest"][0]]["start"]
            between = [ln for lv, _, ln in doc.headings if lv <= 2 and hline < ln < sline]
            if sline < hline or between:
                self.add("check-yourself", sline, "the ::: selftest block must sit inside the "
                         "`## Check yourself` section", (sline, sline))

    def code_blocks(self):
        base = self.ctx["base_dir"]
        max_sketch = int(self.c("code", "sketch_max_lines", 12))
        max_include = int(self.c("code", "include_max_lines", 25))
        max_output = int(self.c("code", "output_max_lines", 20))
        max_total = int(self.c("code", "total_max_lines", 90))
        total, first = 0, None
        lab_cache = {}
        for cb in self.doc.codes:
            rng = (cb["start"], cb["end"])
            classes, kv = cb["classes"], cb["kv"]
            if not cb["ok"]:
                self.add("code-block", cb["start"], f"cannot parse code block attributes "
                         f"`{cb['info']}`", rng)
                continue
            body = [ln for ln in cb["body"]]
            while body and not body[-1].strip():
                body.pop()
            if "dot" in classes:
                continue
            inc = kv.get("include")
            if inc is None and "sketch" not in classes:
                self.add("code-block", cb["start"], "code block has neither include= nor .sketch; "
                         "include tested code from a lab (```{.lang include=\"lab/x/file\"}) or "
                         "mark short untested code as {.lang .sketch}", rng)
                continue
            if inc is None:
                if len(body) > max_sketch:
                    self.add("sketch-length", cb["start"], f".sketch block has {len(body)} lines "
                             f"(max {max_sketch}); shorten it or move it into a lab and include it",
                             rng)
                continue
            if any(ln.strip() for ln in body):
                self.add("code-block", cb["start"], "include= block must have an empty body; the "
                         "renderer inlines the file", rng)
            path = base / inc
            output = "output" in classes
            if output:
                ok = self.check_lab(cb, path, lab_cache)
                if not ok:
                    continue
            if not path.is_file():
                self.add("include", cb["start"], f"include file not found: {inc} "
                         f"(resolved against {self.ctx['base_shown']})", rng)
                continue
            spec = kv.get("lines")
            if spec is not None:
                shown = self.check_lines(cb, path, spec, inc)
            else:
                shown = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            if shown is None:
                continue
            limit = max_output if output else max_include
            if shown > limit:
                self.add("include-length", cb["start"], f"this block shows {shown} lines of {inc} "
                         f"(max {limit}); show only the lines that carry the idea with "
                         f"lines=\"a-b\", and describe the rest in prose", rng)
            if not output:
                total += shown
                first = first or cb["start"]
        if total > max_total:
            self.add("code-total", first, f"the chapter shows {total} lines of included code "
                     f"(max {max_total}); trim the includes to the essential lines", None)

    def check_lines(self, cb, path, spec, inc):
        """Validate a lines= spec; return how many lines it shows, or None if invalid."""
        rng = (cb["start"], cb["end"])
        m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", spec)
        if not m:
            self.add("include", cb["start"], f"lines=\"{spec}\" is not a range like \"10-34\" "
                     f"or a single line", rng)
            return
        try:
            n = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError as e:
            self.add("include", cb["start"], f"cannot read {inc}: {e.strerror}", rng)
            return
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if not (1 <= a <= b <= n):
            self.add("include", cb["start"], f"lines=\"{spec}\" is outside {inc}, which has "
                     f"{n} lines (1-based, inclusive)", rng)
            return
        return b - a + 1

    def check_lab(self, cb, path, cache):
        rng = (cb["start"], cb["end"])
        lab = path.parent
        cmd = f"python3 tools/lab.py run {self.ctx['chapter_dir_shown']}"
        key = str(lab.resolve()) if lab.exists() else str(lab)
        if key in cache:
            msg = cache[key]
        else:
            msg = None
            labname = lab.name
            if not (lab / "lab.json").is_file():
                msg = (f".output include must point into a lab directory; {lab} has no lab.json")
            else:
                try:
                    lj = load_json(lab / "lab.json")
                except UsageError as e:
                    lj = None
                    msg = f"lab {labname}: {e}"
                if lj is not None:
                    runner = lj.get("runner") or self.ctx["topic_runner"] or "local"
                    status_path = lab / "run.status.json"
                    if runner == "none":
                        msg = (f"lab {labname} has runner \"none\", so it is never run and its "
                               "output may not be included; show the code only, or change the runner")
                    elif not status_path.is_file():
                        msg = (f"lab {labname} has not been run (no run.status.json); "
                               f"run `{cmd}`")
                    else:
                        try:
                            st = load_json(status_path)
                        except UsageError as e:
                            st = None
                            msg = f"lab {labname}: {e}; run `{cmd}`"
                        if st is not None:
                            if st.get("hash") != lab_hash(lab):
                                msg = (f"lab {labname} output is stale: its files changed since the "
                                       f"last run; run `{cmd}`")
                            elif st.get("ok") is not True:
                                msg = (f"lab {labname} last run did not meet its expectation "
                                       f"(exit {st.get('exit')}, expect {st.get('expect')}); fix the lab "
                                       f"and run `{cmd}`")
                            elif not (lab / "run.out").is_file():
                                msg = f"lab {labname} has no run.out; run `{cmd}`"
            cache[key] = msg
        if msg:
            self.add("lab-output", cb["start"], msg, rng)
            return False
        return True

    def citations(self):
        facts = self.ctx["facts"]
        sources = self.ctx["sources"]
        unverified = 0
        unknown_warned = False
        checked_src = set()
        for p in self.doc.paras:
            for cid, pos in p.cites:
                if cid == "unverified":
                    unverified += 1
                    self.addp("unverified", p, pos, "unverified claim [@unverified]; find a fact "
                              "for it or keep the marker")
                    continue
                if facts is None:
                    if not unknown_warned:
                        self.add("facts-missing", pos[0], "no facts.jsonl available, citation ids "
                                 "not checked; pass --facts", (p.start, p.end), pos[1])
                        unknown_warned = True
                    continue
                if cid not in facts:
                    hint = " (S-ids are sources; cite a fact F-id)" if re.fullmatch(r"S\d+", cid) else ""
                    known = ", ".join(sorted(facts, key=lambda k: (len(k), k))) or "none"
                    self.addp("citation", p, pos, f"[@{cid}] is not in facts.jsonl{hint}; "
                              f"known ids: {known}. Cite an existing fact or use [@unverified]")
                    continue
                src = facts[cid].get("source")
                if sources is not None and cid not in checked_src:
                    checked_src.add(cid)
                    if src not in sources:
                        self.addp("fact-source", p, pos, f"fact {cid} cites source {src!r}, which "
                                  "is not in sources.jsonl")
        self.unverified = unverified

    def terms(self):
        doc = self.doc
        glossary = self.ctx["glossary"]
        chapter = self.ctx["chapter"]
        seen = {}
        order = [p for p in doc.paras]
        for pi, p in enumerate(order):
            for sp in p.spans:
                if "term" not in sp["classes"] and not (
                        not sp["ok"] and re.search(r"(?<![\w-])\.term(?![\w-])", sp["attrs"])):
                    continue
                pos = sp["pos"]
                kv = sp["kv"]
                if not sp["ok"] and "key" not in kv:
                    km = re.search(r"(?<![\w-])key=\"([^\"]*)\"", sp["attrs"])
                    if km:
                        kv = dict(kv, key=km.group(1))
                text = sp["vis"]
                name = " ".join((kv.get("key") or text).split())
                shown = name or "?"
                d = kv.get("def", "")
                if not sp["ok"]:
                    self.addp("term-def", p, pos, f"cannot parse attributes of term '{shown}'; "
                              "write {.term def=\"One plain sentence.\"} with no double quotes inside")
                elif not d.strip():
                    self.addp("term-def", p, pos, f"term '{shown}' has no def; add def=\"one plain "
                              "sentence\"")
                elif '"' in d:
                    self.addp("term-def", p, pos, f"def of term '{shown}' contains double quotes; "
                              "rephrase without them")
                elif re.search(r"\[@|`|\*|\$|\[[^\]]*\]\(", d):
                    self.addp("term-def", p, pos, f"def of term '{shown}' must be plain text: no "
                              "citations, code, emphasis or math")
                if not name:
                    self.addp("term-def", p, pos, "term span has no visible text")
                    continue
                low = name.lower()
                if low in seen:
                    self.addp("term-duplicate", p, pos, f"term '{name}' is marked twice (first at "
                              f"line {seen[low]}); remove this .term span and keep plain text")
                    continue
                seen[low] = pos[0]
                if low in glossary and (chapter is None or glossary[low] is None
                                        or glossary[low] < chapter):
                    g = glossary[low]
                    where = f"chapter {g}" if g is not None else "the topic glossary"
                    self.addp("term-glossary", p, pos, f"term '{name}' is already defined in "
                              f"{where}; do not re-mark it, use plain text")
                rx = term_regex(name)
                if rx is None:
                    continue
                cut = p.vis.index_of(pos)
                hit = None
                for q in order[:pi]:
                    x = rx.search(q.vis.s)
                    if x:
                        hit = (q, q.vis.at(x.start()))
                        break
                if hit is None:
                    x = rx.search(p.vis.s, 0, cut)
                    if x:
                        hit = (p, p.vis.at(x.start()))
                if hit:
                    q, hpos = hit
                    self.addp("term-before-mark", q, hpos, f"term '{name}' is used here before it is "
                              f"marked at line {pos[0]}; move the .term span to this first use")
        self.term_names = set(seen)

    def acronyms(self):
        known = self.ctx["acronyms"]
        gloss = set(self.ctx["glossary"])
        names = self.term_names
        first = {}
        expanded = {}
        for p in self.doc.paras:
            s = p.prose.s
            for x in ACR_RX.finditer(s):
                acr = x.group(1)
                letters = sum(ch.isalpha() for ch in acr)
                if not (2 <= letters <= 6) or len(acr) > 10:
                    continue
                if acr in known or acr.lower() in gloss or acr.lower() in names:
                    continue
                if all(part in known for part in re.split(r"[/&-]", acr)):
                    continue  # TCP/IP, CPU-GPU: every part is already known
                if acr not in first:
                    first[acr] = (p, p.prose.at(x.start()))
                if acr not in expanded:
                    pre = s[:x.start()].rstrip(" ")
                    post = s[x.end():].lstrip(" ")
                    if pre.endswith("(") and post.startswith(")") and \
                            re.search(r"[A-Za-z][\w'-]*\s*\($", pre):
                        expanded[acr] = (p, p.prose.at(x.start()))
        word_in_terms = " ".join(sorted(names))
        for acr, (p, pos) in first.items():
            if re.search(r"(?<![\w-])" + re.escape(acr.lower()) + r"(?![\w-])", word_in_terms):
                continue
            if acr in expanded:
                ep, epos = expanded[acr]
                if epos == pos or (ep is p and epos[0] == pos[0] and abs(epos[1] - pos[1]) < 2):
                    continue
                self.addp("acronym", p, pos, f"acronym {acr} is used before its expansion at "
                          f"line {epos[0]}; expand it at first use as 'Full Words ({acr})'")
                continue
            self.addp("acronym", p, pos, f"undefined acronym {acr}; expand it at first use as "
                      f"'Full Words ({acr})', mark it as a .term, or add it to "
                      "style/known-acronyms.txt if the learner already knows it")

    def budget(self):
        total = 0
        allw = 0
        for p in self.doc.paras:
            n = words(p.prose.s)
            allw += n
            if "answers" not in self.div_classes(p):
                total += n
        self.words = total
        self.words_all = allw
        b = self.ctx["budget"]
        if not b:
            return
        lo, hi = b
        over = float(self.c("budget", "over_factor", 1.1))
        under = float(self.c("budget", "under_factor", 0.8))
        if total > hi * over:
            self.add("word-budget", 1, f"{total} prose words, over the budget {lo}-{hi} by more "
                     f"than {round((over - 1) * 100)}%; cut {total - hi} words")
        elif total < lo * under:
            self.add("word-budget-low", 1, f"{total} prose words, under the budget {lo}-{hi} by "
                     f"more than {round((1 - under) * 100)}%")

    # -- style rules ------------------------------------------------------
    def style(self):
        paras = self.styled()
        per_k = self.words_all / 1000.0
        self.style_semicolons(paras, per_k)
        self.style_dashes(paras, per_k)
        stock = [(p, phrase_regex(p)) for p in self.c("stock_phrases", "phrases", [])]
        contrast = [re.compile(x, re.I) for x in self.c("contrast_frames", "patterns", [])]
        pmax = int(self.c("parentheses", "max_per_paragraph", 1))
        pwords = int(self.c("parentheses", "max_words", 6))
        short_under = int(self.c("short_sentences", "under_words", 8))
        short_run = int(self.c("short_sentences", "min_run", 3))
        wall = int(self.c("wall_of_text", "max_words", 170))
        rq_q = int(self.c("rhetorical_question", "max_question_words", 2))
        rq_f = int(self.c("rhetorical_question", "max_fragment_words", 4))
        for p in paras:
            m = p.prose
            s = m.s
            divs = self.div_classes(p)
            self.style_parens(p, pmax, pwords)
            sents = sentences(m)
            lens = [words(s[a:b]) for a, b in sents]
            i = 0
            while i < len(sents):
                j = i
                while j < len(sents) and lens[j] < short_under:
                    j += 1
                if j - i >= short_run:
                    self.addp("short-sentences", p, m.at(sents[i][0]), f"{j - i} short sentences in "
                              f"a row (each under {short_under} words); join them into flowing "
                              "sentences")
                i = max(j, i + 1)
            if "selftest" not in divs:
                for k, (a, b) in enumerate(sents[:-1]):
                    q = s[a:b].rstrip().rstrip("\"')]")
                    if not q.endswith("?"):
                        continue
                    if lens[k] <= rq_q or lens[k + 1] <= rq_f:
                        self.addp("rhetorical-question", p, m.at(a), "rhetorical question answered "
                                  "by a fragment; state the point directly as one sentence")
            for phrase, rx in stock:
                for x in rx.finditer(s):
                    shown = x.group(0) if phrase.startswith("re:") else phrase
                    self.addp("stock-phrase", p, m.at(x.start()), f"stock phrase '{shown}'; say "
                              "the specific thing plainly")
            for rx in contrast:
                for x in rx.finditer(s):
                    frag = " ".join(x.group(0).split())
                    frag = frag if len(frag) <= 60 else frag[:57] + "..."
                    self.addp("contrast-frame", p, m.at(x.start()), f"contrast frame \"{frag}\"; "
                              "say what the thing is directly instead of what it is not")
            n = words(s)
            if n > wall:
                self.addp("wall-of-text", p, (p.start, None), f"paragraph has {n} words (max {wall}); "
                          "split it, main point first")
            bangs = [x.start() for x in re.finditer(r"!", s)]
            if bangs:
                self.addp("exclamation", p, m.at(bangs[0]), f"{len(bangs)} exclamation mark(s) in "
                          "prose; use a period")
        self.style_lists()

    def style_semicolons(self, paras, per_k):
        rate = float(self.c("semicolons", "per_1000_words", 1.0))
        allow = int(per_k * rate)
        found = [(p, p.prose.at(x.start())) for p in paras for x in re.finditer(";", p.prose.s)]
        self.semicolons = len(found)
        self.semicolon_allowance = allow
        for k, (p, pos) in enumerate(found[allow:], allow + 1):
            self.addp("semicolon", p, pos, f"semicolon {k} of {len(found)} (allowance {allow} for "
                      f"{self.words_all} words); split into two sentences or use a comma and a "
                      "conjunction")

    def style_dashes(self, paras, per_k):
        rate = float(self.c("dashes", "per_1000_words", 2.0))
        pmax = int(self.c("dashes", "paragraph_max", 2))
        allow = int(per_k * rate)
        per = [(p, [p.prose.at(x.start()) for x in DASH_RX.finditer(p.prose.s)]) for p in paras]
        total = sum(len(d) for _, d in per)
        self.dashes = total
        self.dash_allowance = allow
        seen = 0
        for p, ds in per:
            if not ds:
                continue
            before = seen
            seen += len(ds)
            if len(ds) >= pmax:
                self.addp("dashes", p, ds[0], f"{len(ds)} dashes in one paragraph (max "
                          f"{pmax - 1}); rewrite with commas, colons or separate sentences")
            elif seen > allow:
                k = max(0, allow - before)
                self.addp("dashes", p, ds[k], f"dash beyond the allowance ({total} dashes, "
                          f"{allow} allowed for {self.words_all} words); rewrite without it")

    def style_parens(self, p, pmax, pwords):
        s = p.prose.s
        groups, stack = [], []
        for i, ch in enumerate(s):
            if ch == "(":
                stack.append(i)
            elif ch == ")" and stack:
                a = stack.pop()
                if not stack:
                    groups.append((a, i))
        counted, long = [], []
        for a, b in groups:
            if a > 0 and (s[a - 1].isalnum() or s[a - 1] in "_)]"):
                continue  # function call or plural like fsync(), file(s)
            inner = " ".join(s[a + 1:b].split())
            if PAREN_ACR_RX.match(inner) or PAREN_ENUM_RX.match(inner) or not inner:
                continue
            counted.append((a, b))
            if words(inner) > pwords:
                long.append((a, b, words(inner)))
        problems = []
        if len(counted) > pmax:
            problems.append(f"{len(counted)} parentheticals in one paragraph (max {pmax})")
        for a, b, n in long:
            problems.append(f"parenthetical of {n} words (max {pwords})")
        if problems:
            at = long[0][0] if long and len(counted) <= pmax else counted[pmax if len(counted) > pmax else 0][0]
            self.addp("parentheses", p, p.prose.at(at), "; ".join(problems) + ". Fold the aside "
                      "into the sentence, give it its own sentence, or move it to a ::: aside block")

    def style_lists(self):
        mx = int(self.c("list_heavy", "max_items", 8))
        exempt = set(self.c("list_heavy", "exempt_divs", ["selftest", "answers"]))
        runs = {}
        for p in self.doc.paras:
            if p.run is None:
                continue
            runs.setdefault(p.run, []).append(p)
        for ps in runs.values():
            items = [p for p in ps if p.kind == "item" and not (self.div_classes(p) & exempt)]
            if len(items) > mx:
                first, last = ps[0], ps[-1]
                self.add("list-heavy", first.start, f"{len(items)} list items in a row (max {mx}); "
                         "turn some of the list into prose", (first.start, last.end))


DEFAULT_KNOWN_DIVS = ["crux", "aside", "misconception", "tryit", "selftest", "answers"]


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------

def shown(path):
    try:
        return os.path.relpath(path)
    except ValueError:
        return str(path)


def build_context(args, doc, cfg, cfg_path):
    chap = Path(args.chapter)
    cdir = chap.parent
    res = chap.resolve()
    auto = not args.no_context

    def need(p, what):
        if not Path(p).exists():
            raise UsageError(f"{what} not found: {p}")
        return Path(p)

    topic_dir = None
    if args.topic_dir:
        topic_dir = need(args.topic_dir, "--topic-dir")
    elif auto and res.name == "chapter.md" and res.parent.parent.name == "chapters" \
            and res.parent.parent.parent.parent.name == "topics":
        topic_dir = res.parent.parent.parent

    facts_path = None
    if args.facts:
        facts_path = need(args.facts, "--facts file")
    elif auto and (cdir / "facts.jsonl").is_file():
        facts_path = cdir / "facts.jsonl"
    facts = None
    if facts_path:
        facts = {}
        for f in load_jsonl(facts_path):
            if "id" in f:
                facts[str(f["id"])] = f

    src_path = None
    if args.sources:
        src_path = need(args.sources, "--sources file")
    elif auto:
        for cand in (cdir / "sources.jsonl", cdir / ".." / ".." / "sources.jsonl"):
            if cand.is_file():
                src_path = cand
                break
    sources = None
    if src_path:
        sources = {str(s["id"]) for s in load_jsonl(src_path) if "id" in s}

    glossary, state = {}, None
    if topic_dir:
        gp = topic_dir / "glossary.jsonl"
        if gp.is_file():
            for g in load_jsonl(gp):
                t = str(g.get("term", "")).strip().lower()
                if t:
                    ch = g.get("chapter")
                    prev = glossary.get(t)
                    glossary[t] = ch if prev is None else min(prev, ch) if ch is not None else prev
        sp = topic_dir / "state.json"
        if sp.is_file():
            state = load_json(sp)

    chapter = int(doc.fm["chapter"]) if re.fullmatch(r"\d+", doc.fm.get("chapter", "")) else None

    budget = None
    if args.words:
        m = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*", args.words)
        if not m or int(m.group(1)) > int(m.group(2)):
            raise UsageError(f"--words must be MIN,MAX with MIN <= MAX, got {args.words!r}")
        budget = [int(m.group(1)), int(m.group(2))]
    elif state and chapter is not None:
        for ch in state.get("chapters") or []:
            if isinstance(ch, dict) and ch.get("n") == chapter:
                w = ch.get("words")
                if isinstance(w, list) and len(w) == 2 and all(isinstance(v, int) for v in w):
                    budget = w
                break
    topic_runner = None
    if state and isinstance(state.get("lab"), dict):
        topic_runner = state["lab"].get("runner")

    acr_file = (cfg_path.parent / cfg.get("acronyms_file", "known-acronyms.txt"))
    acronyms = set()
    if acr_file.is_file():
        for line in acr_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                acronyms.add(line)
    else:
        raise UsageError(f"acronyms file not found: {acr_file} (set acronyms_file in {cfg_path})")

    base = Path(args.base_dir) if args.base_dir else cdir
    if not base.is_dir():
        raise UsageError(f"--base-dir is not a directory: {base}")
    return {
        "base_dir": base, "base_shown": shown(base) or ".",
        "chapter_dir_shown": shown(base),
        "facts": facts, "facts_path": facts_path, "sources": sources, "glossary": glossary,
        "chapter": chapter, "budget": budget, "topic_runner": topic_runner,
        "acronyms": acronyms, "topic_dir": topic_dir,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="lint.py", description=__doc__.split("\n\n")[0],
        epilog="See the module docstring (top of tools/lint.py) for context resolution details.")
    ap.add_argument("chapter", help="chapter Markdown file")
    ap.add_argument("--json", action="store_true", help="print one JSON object")
    ap.add_argument("--config", help=f"lint settings (default: {shown(DEFAULT_CONFIG)})")
    ap.add_argument("--facts", help="facts.jsonl (default: next to the chapter)")
    ap.add_argument("--sources", help="sources.jsonl (default: chapter dir, then ../../)")
    ap.add_argument("--topic-dir", help="topic dir holding glossary.jsonl and state.json")
    ap.add_argument("--base-dir", help="directory include= paths resolve against "
                    "(default: the chapter file's directory)")
    ap.add_argument("--words", metavar="MIN,MAX", help="prose word budget (default: from state.json)")
    ap.add_argument("--no-context", action="store_true",
                    help="do not discover facts, sources or topic dir from the path")
    args = ap.parse_args(argv)

    try:
        cfg_path = Path(args.config) if args.config else DEFAULT_CONFIG
        try:
            cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
        except OSError as e:
            raise UsageError(f"cannot read config {cfg_path}: {e.strerror}")
        except tomllib.TOMLDecodeError as e:
            raise UsageError(f"config {cfg_path}: {e}")
        try:
            text = Path(args.chapter).read_text(encoding="utf-8")
        except OSError as e:
            raise UsageError(f"cannot read {args.chapter}: {e.strerror}")
        except UnicodeDecodeError:
            raise UsageError(f"{args.chapter} is not UTF-8")
        doc = parse(text)
        ctx = build_context(args, doc, cfg, cfg_path)
        try:
            for rx in (cfg.get("contrast_frames") or {}).get("patterns", []):
                re.compile(rx)
            for ph in (cfg.get("stock_phrases") or {}).get("phrases", []):
                phrase_regex(ph)
        except re.error as e:
            raise UsageError(f"config {cfg_path}: bad regular expression: {e}")
        lint = Linter(Path(args.chapter), doc, cfg, ctx)
        lint.run()
    except UsageError as e:
        print(f"lint.py: {e}", file=sys.stderr)
        return 2

    f = lint.findings
    by_sev = {s: sum(1 for x in f if x["severity"] == s) for s in ("error", "warning", "info")}
    by_rule = {}
    for x in f:
        by_rule[x["rule"]] = by_rule.get(x["rule"], 0) + 1
    ok = by_sev["error"] == 0
    stats = {
        "errors": by_sev["error"], "warnings": by_sev["warning"], "info": by_sev["info"],
        "by_rule": dict(sorted(by_rule.items())),
        "unverified": lint.unverified,
        "words_including_answers": lint.words_all,
        "semicolons": lint.semicolons, "semicolon_allowance": lint.semicolon_allowance,
        "dashes": lint.dashes, "dash_allowance": lint.dash_allowance,
        "paragraphs": len(doc.paras),
        "terms": len(lint.term_names),
        "citations": sum(len(p.cites) for p in doc.paras),
        "facts_file": str(ctx["facts_path"]) if ctx["facts_path"] else None,
        "topic_dir": str(ctx["topic_dir"]) if ctx["topic_dir"] else None,
    }
    if args.json:
        print(json.dumps({"ok": ok, "words": lint.words, "budget": ctx["budget"],
                          "findings": f, "stats": stats}, indent=2, ensure_ascii=False))
    else:
        for x in f:
            print(f"{x['line'] or 0}:{x['rule']}:{x['severity']}: {x['message']}")
            if x["paragraph_start"] and x["paragraph_end"] != x["paragraph_start"]:
                print(f"    paragraph: lines {x['paragraph_start']}-{x['paragraph_end']}")
            if x["excerpt"]:
                print(f"    | {x['excerpt']}")
        b = ctx["budget"]
        print("--")
        print(f"words: {lint.words}" + (f" (budget {b[0]}-{b[1]})" if b else " (no budget)"))
        print(f"findings: {by_sev['error']} errors, {by_sev['warning']} warnings, {by_sev['info']} info")
        if by_rule:
            print("by rule: " + ", ".join(f"{k}={v}" for k, v in sorted(by_rule.items())))
        print(f"unverified claims: {lint.unverified}")
        print("result: " + ("OK" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
