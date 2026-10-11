#!/usr/bin/env python3
"""Manage topic state under topics/ (see tools/SCHEMAS.md).

Usage (paths are relative to the repo root; [slug] defaults to topics/.current):
  state.py init <slug> --title T        create topics/<slug>/ skeleton and make it current
  state.py current [slug]               print or set the active topic
  state.py validate [slug]              check state.json, sources.jsonl, glossary.jsonl and
                                        every chapter's facts.jsonl; exit 1 on problems
  state.py roadmap [slug]               regenerate roadmap.md from state.json
  state.py chapter-dir [slug] <n>       create (if needed) and print the chapter directory
  state.py next [slug] [--json]         print the first pending/in_progress chapter; exit 1 if none
  state.py set [slug] <n> key=value...  update a chapter: status=done, title=..., words=4000,6000,
                                        quiz='{"date": "2026-10-11", "solid": [], "shaky": []}'
  state.py merge [slug] [--chapter N] [--json] <scout files...>
                                        merge scout records: sources into the topic library,
                                        facts (only with --chapter) into that chapter's facts.jsonl
  state.py glossary [slug] <n>          collect .term spans of chapter n into glossary.jsonl and
                                        regenerate glossary.md
  state.py status [slug]                short human summary

Scout facts may carry an optional "key" (unique per file); it is reported with the new
F id but not stored. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "topics"
CURRENT = TOPICS / ".current"

SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SID_RE = re.compile(r"S([1-9]\d*)")
FID_RE = re.compile(r"F([1-9]\d*)")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
STATUSES = ("pending", "known", "in_progress", "done")
RUNNERS = ("none", "local", "vng")
KINDS = ("paper", "docs", "source", "book", "spec", "article", "video", "man")
TOP_KEYS = ("slug", "title", "created", "goal", "lab", "parts", "chapters")
LAB_KEYS = ("runner", "toolchains", "notes", "expect", "timeout", "network")
CHAPTER_KEYS = ("n", "slug", "title", "part", "core_ideas", "prereqs", "words", "status", "quiz")
SOURCE_FIELDS = ("title", "url", "kind", "version", "why")
FACT_FIELDS = ("locator", "claim", "quote")
QUOTE_WORDS_WARN = 75  # quotes should be at most about 60 words
SETTABLE = ("status", "title", "words", "quiz")
MARKERS = {"done": "[done]", "known": "[known, skipped]", "in_progress": "[in progress]",
           "pending": "[pending]"}


class Fail(Exception):
    """Usage or environment error: message printed, exit 2."""


# ---------------------------------------------------------------- small helpers
def rel(p) -> str:
    p = Path(p)
    try:
        return os.path.relpath(p, Path.cwd()) if p.resolve().is_relative_to(Path.cwd().resolve()) else str(p)
    except ValueError:
        return str(p)


def today() -> str:
    return datetime.date.today().isoformat()


def valid_date(s) -> bool:
    if not isinstance(s, str) or not DATE_RE.fullmatch(s):
        return False
    try:
        datetime.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def write_text_atomic(path: Path, text: str):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def dump_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def jline(rec) -> str:
    return json.dumps(rec, ensure_ascii=False)


def append_lines(path: Path, recs):
    if not recs:
        return
    prefix = ""
    if path.exists() and path.stat().st_size:
        with open(path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                prefix = "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(prefix + "".join(jline(r) + "\n" for r in recs))


def read_jsonl(path: Path, problems: list):
    """Return [(lineno, obj)]; parse errors go to problems as 'file:line: msg'."""
    out = []
    if not path.exists():
        return out
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"{rel(path)}:{i}: invalid JSON ({e.msg} at column {e.colno})")
            continue
        if not isinstance(obj, dict):
            problems.append(f"{rel(path)}:{i}: each line must be a JSON object")
            continue
        out.append((i, obj))
    return out


def id_num(regex, s):
    m = regex.fullmatch(s) if isinstance(s, str) else None
    return int(m.group(1)) if m else None


def is_str(v, nonempty=True):
    return isinstance(v, str) and (bool(v.strip()) or not nonempty)


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


# ---------------------------------------------------------------- topic resolution
def current_slug():
    if not CURRENT.is_file():
        raise Fail("no active topic: run `state.py init <slug> --title T` or `state.py current <slug>`")
    slug = CURRENT.read_text(encoding="utf-8").strip()
    if not slug:
        raise Fail(f"{rel(CURRENT)} is empty: run `state.py current <slug>`")
    return slug


def topic_dir(slug=None) -> Path:
    slug = slug or current_slug()
    d = TOPICS / slug
    if not (d / "state.json").is_file():
        known = sorted(p.name for p in TOPICS.iterdir() if (p / "state.json").is_file()) if TOPICS.is_dir() else []
        raise Fail(f"no topic {slug!r}: {rel(d / 'state.json')} not found (topics: {', '.join(known) or 'none'})")
    return d


def is_topic(name) -> bool:
    return bool(SLUG_RE.fullmatch(name)) and (TOPICS / name / "state.json").is_file()


def load_state(tdir: Path) -> dict:
    p = tdir / "state.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Fail(f"{rel(p)}:{e.lineno}: invalid JSON ({e.msg}); fix it by hand, then run validate")
    if not isinstance(data, dict):
        raise Fail(f"{rel(p)}: must be a JSON object")
    return data


def save_state(tdir: Path, state: dict):
    write_text_atomic(tdir / "state.json", dump_json(state))


def get_chapter(state: dict, n: int) -> dict:
    for ch in state.get("chapters") or []:
        if isinstance(ch, dict) and ch.get("n") == n:
            return ch
    nums = [c.get("n") for c in state.get("chapters") or [] if isinstance(c, dict)]
    raise Fail(f"no chapter {n} in state.json (chapters: {', '.join(map(str, nums)) or 'none'})")


def chapter_path(tdir: Path, ch: dict) -> Path:
    return tdir / "chapters" / f"{ch['n']:02d}-{ch['slug']}"


def existing_chapter_dir(tdir: Path, ch: dict):
    """The chapter's directory if it exists; Fail if only a differently-named NN-* exists."""
    want = chapter_path(tdir, ch)
    if want.is_dir():
        return want
    cdir = tdir / "chapters"
    others = sorted(p.name for p in cdir.glob(f"{ch['n']:02d}-*") if p.is_dir()) if cdir.is_dir() else []
    if others:
        raise Fail(f"chapter {ch['n']} has slug {ch['slug']!r} in state.json but the directory is "
                   f"{rel(cdir / others[0])}; rename the directory to {want.name}")
    return None


def ensure_chapter_dir(tdir: Path, ch: dict) -> Path:
    d = existing_chapter_dir(tdir, ch) or chapter_path(tdir, ch)
    for sub in ("work", "lab"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def parse_n(s) -> int:
    try:
        n = int(s)
    except (TypeError, ValueError):
        raise Fail(f"chapter number must be an integer, got {s!r}")
    return n


# ---------------------------------------------------------------- validation
def validate_quiz(q, where):
    if q is None:
        return []
    probs = []
    if not isinstance(q, dict):
        return [f'{where}: quiz must be null or {{"date": "YYYY-MM-DD", "solid": [...], "shaky": [...]}}']
    extra = sorted(set(q) - {"date", "solid", "shaky"})
    if extra:
        probs.append(f"{where}: quiz has unknown key(s) {', '.join(extra)} (allowed: date, solid, shaky)")
    if not valid_date(q.get("date")):
        probs.append(f"{where}: quiz.date must be a YYYY-MM-DD date, got {q.get('date')!r}")
    for k in ("solid", "shaky"):
        v = q.get(k)
        if not isinstance(v, list) or not all(is_str(x) for x in v):
            probs.append(f"{where}: quiz.{k} must be a list of non-empty strings")
    return probs


def validate_words(w, where):
    if (not isinstance(w, list) or len(w) != 2 or not all(is_int(x) for x in w)):
        return [f"{where}: words must be [min, max] integers, got {json.dumps(w)}"]
    if w[0] <= 0 or w[0] > w[1]:
        return [f"{where}: words must satisfy 0 < min <= max, got {json.dumps(w)}"]
    return []


def validate_state(state: dict, tdir: Path):
    """Return (errors, warnings) for state.json."""
    E, W = [], []
    f = rel(tdir / "state.json")
    for k in TOP_KEYS:
        if k not in state:
            E.append(f"{f}: missing key {k!r}")
    for k in sorted(set(state) - set(TOP_KEYS)):
        W.append(f"{f}: unknown key {k!r} (allowed: {', '.join(TOP_KEYS)})")
    if "slug" in state and state["slug"] != tdir.name:
        E.append(f"{f}: slug is {state['slug']!r} but the topic directory is {tdir.name!r}")
    if "title" in state and not is_str(state["title"]):
        E.append(f"{f}: title must be a non-empty string")
    if "created" in state and not valid_date(state["created"]):
        E.append(f"{f}: created must be a YYYY-MM-DD date, got {state['created']!r}")
    if "goal" in state:
        if not isinstance(state["goal"], str):
            E.append(f"{f}: goal must be a string")
        elif not state["goal"].strip():
            W.append(f"{f}: goal is empty")
    lab = state.get("lab")
    if "lab" in state:
        if not isinstance(lab, dict):
            E.append(f"{f}: lab must be an object like {{\"runner\": \"local\", \"toolchains\": [], \"notes\": \"\"}}")
        else:
            if lab.get("runner") not in RUNNERS:
                E.append(f"{f}: lab.runner must be one of {', '.join(RUNNERS)}, got {lab.get('runner')!r}")
            if "toolchains" in lab and (not isinstance(lab["toolchains"], list)
                                        or not all(is_str(t) for t in lab["toolchains"])):
                E.append(f"{f}: lab.toolchains must be a list of program names")
            if "notes" in lab and not isinstance(lab["notes"], str):
                E.append(f"{f}: lab.notes must be a string")
            if "expect" in lab and lab["expect"] not in ("success", "failure"):
                E.append(f"{f}: lab.expect must be success or failure")
            if "timeout" in lab and (isinstance(lab["timeout"], bool) or not isinstance(lab["timeout"], (int, float))
                                     or lab["timeout"] <= 0):
                E.append(f"{f}: lab.timeout must be a positive number of seconds")
            if "network" in lab and not isinstance(lab["network"], bool):
                E.append(f"{f}: lab.network must be true or false")
            for k in sorted(set(lab) - set(LAB_KEYS)):
                W.append(f"{f}: unknown key lab.{k} (allowed: {', '.join(LAB_KEYS)})")
    parts = state.get("parts")
    if "parts" in state and not isinstance(parts, list):
        E.append(f"{f}: parts must be a list")
        parts = None
    chapters = state.get("chapters")
    if "chapters" in state and not isinstance(chapters, list):
        E.append(f"{f}: chapters must be a list")
        chapters = None
    chapters = chapters or []
    parts = parts or []
    good = []
    slugs = {}
    for i, ch in enumerate(chapters):
        where = f"{f}: chapters[{i}]"
        if not isinstance(ch, dict):
            E.append(f"{where}: must be an object")
            continue
        if ch.get("n") == i + 1 and is_int(ch.get("n")):
            where = f"{f}: chapter {ch['n']}"
        elif "n" in ch:
            where = f"{f}: chapters[{i}] (n={ch['n']!r})"
        for k in CHAPTER_KEYS:
            if k not in ch:
                E.append(f"{where}: missing key {k!r}")
        for k in sorted(set(ch) - set(CHAPTER_KEYS)):
            W.append(f"{where}: unknown key {k!r} (allowed: {', '.join(CHAPTER_KEYS)})")
        if "n" in ch and (not is_int(ch["n"]) or ch["n"] != i + 1):
            E.append(f"{where}: n must be {i + 1} (chapters are numbered 1, 2, 3, ... in list order), "
                     f"got {ch['n']!r}")
        if "slug" in ch:
            if not isinstance(ch["slug"], str) or not SLUG_RE.fullmatch(ch["slug"]):
                E.append(f"{where}: slug must be lowercase words joined by '-', got {ch['slug']!r}")
            elif ch["slug"] in slugs:
                E.append(f"{where}: slug {ch['slug']!r} already used by chapter {slugs[ch['slug']]}")
            else:
                slugs[ch["slug"]] = ch.get("n")
        if "title" in ch and not is_str(ch["title"]):
            E.append(f"{where}: title must be a non-empty string")
        if "part" in ch and (not is_int(ch["part"]) or not 0 <= ch["part"] < len(parts)):
            E.append(f"{where}: part must be an index into parts (0..{len(parts) - 1}), got {ch['part']!r}")
        for k in ("core_ideas", "prereqs"):
            if k in ch and (not isinstance(ch[k], list) or not all(is_str(x) for x in ch[k])):
                E.append(f"{where}: {k} must be a list of non-empty strings")
        if "words" in ch:
            E += validate_words(ch["words"], where)
        if "status" in ch and ch["status"] not in STATUSES:
            E.append(f"{where}: status must be one of {', '.join(STATUSES)}, got {ch['status']!r}")
        if "quiz" in ch:
            E += validate_quiz(ch["quiz"], where)
        good.append(ch)
    nums = {c.get("n") for c in good if is_int(c.get("n"))}
    listed = {}
    for pi, part in enumerate(parts):
        where = f"{f}: parts[{pi}]"
        if not isinstance(part, dict):
            E.append(f"{where}: must be an object {{\"title\": ..., \"chapters\": [...]}}")
            continue
        for k in sorted(set(part) - {"title", "chapters"}):
            W.append(f"{where}: unknown key {k!r} (allowed: title, chapters)")
        if not is_str(part.get("title")):
            E.append(f"{where}: title must be a non-empty string")
        pcs = part.get("chapters")
        if not isinstance(pcs, list) or not all(is_int(x) for x in pcs):
            E.append(f"{where}: chapters must be a list of chapter numbers")
            continue
        for n in pcs:
            if n not in nums:
                E.append(f"{where}: lists chapter {n}, which does not exist")
            elif n in listed:
                E.append(f"{where}: lists chapter {n}, which parts[{listed[n]}] also lists")
            else:
                listed[n] = pi
        if pcs != sorted(pcs):
            W.append(f"{where}: chapters are not in ascending order")
        if not pcs:
            W.append(f"{where}: has no chapters")
    for ch in good:
        n, p = ch.get("n"), ch.get("part")
        if not is_int(n) or not is_int(p) or not 0 <= p < len(parts):
            continue
        if n not in listed:
            E.append(f"{f}: chapter {n} has part {p} but parts[{p}].chapters does not list it")
        elif listed[n] != p:
            E.append(f"{f}: chapter {n} has part {p} but is listed in parts[{listed[n]}].chapters")
    return E, W


def check_source(rec, where, require_id=True):
    E, W = [], []
    if require_id and id_num(SID_RE, rec.get("id")) is None:
        E.append(f"{where}: id must look like S1, S2, ..., got {rec.get('id')!r}")
    for k in SOURCE_FIELDS:
        if k not in rec:
            E.append(f"{where}: missing field {k!r}")
        elif not isinstance(rec[k], str):
            E.append(f"{where}: {k} must be a string")
    if isinstance(rec.get("title"), str) and not rec["title"].strip():
        E.append(f"{where}: title is empty")
    url = rec.get("url")
    if isinstance(url, str) and url.strip() and not re.match(r"https?://", url.strip(), re.I):
        E.append(f"{where}: url must start with http:// or https:// (or be \"\" for a book), got {url!r}")
    if "kind" in rec and rec["kind"] not in KINDS:
        E.append(f"{where}: kind must be one of {', '.join(KINDS)}, got {rec['kind']!r}")
    if isinstance(url, str) and not url.strip() and isinstance(rec.get("version"), str) \
            and not rec["version"].strip():
        E.append(f"{where}: url is empty, so version must name the edition or release that was read")
    if isinstance(rec.get("why"), str) and not rec["why"].strip():
        W.append(f"{where}: why is empty")
    return E, W


def check_fact(rec, where, require_id=True):
    E, W = [], []
    if require_id and id_num(FID_RE, rec.get("id")) is None:
        E.append(f"{where}: id must look like F1, F2, ..., got {rec.get('id')!r}")
    if not is_str(rec.get("source")):
        E.append(f"{where}: missing source (an S id{'' if require_id else ' or a source key from the same file'})")
    for k in FACT_FIELDS:
        if not is_str(rec.get(k)):
            E.append(f"{where}: {k} must be a non-empty string")
    q = rec.get("quote")
    if isinstance(q, str) and len(q.split()) > QUOTE_WORDS_WARN:
        W.append(f"{where}: quote has {len(q.split())} words; keep quotes to about 60 words")
    return E, W


def cmd_validate(a) -> int:
    tdir = topic_dir(a.slug)
    E, W = [], []
    state = load_state(tdir)
    e, w = validate_state(state, tdir)
    E += e
    W += w
    # topic sources
    sp = tdir / "sources.jsonl"
    if not sp.exists():
        E.append(f"{rel(sp)}: missing (create an empty file)")
    topic_sids = load_source_ids(sp, E, W)
    # glossary
    gp = tdir / "glossary.jsonl"
    seen = {}
    for ln, rec in read_jsonl(gp, E):
        where = f"{rel(gp)}:{ln}"
        if not is_str(rec.get("term")):
            E.append(f"{where}: term must be a non-empty string")
        if not is_str(rec.get("def")):
            E.append(f"{where}: def must be a non-empty string")
        if not is_int(rec.get("chapter")):
            E.append(f"{where}: chapter must be a chapter number")
        t = rec.get("term")
        if isinstance(t, str):
            if t.lower() in seen:
                E.append(f"{where}: term {t!r} duplicates line {seen[t.lower()]}")
            else:
                seen[t.lower()] = ln
    # chapters
    chapters = [c for c in state.get("chapters") or [] if isinstance(c, dict)
                and is_int(c.get("n")) and isinstance(c.get("slug"), str)]
    known = {chapter_path(tdir, c).name for c in chapters}
    cdir = tdir / "chapters"
    if cdir.is_dir():
        for d in sorted(p for p in cdir.iterdir() if p.is_dir()):
            if d.name not in known:
                E.append(f"{rel(d)}: no chapter in state.json matches this directory "
                         f"(expected names: {', '.join(sorted(known)) or 'none'})")
                continue
            sids = topic_sids
            local = d / "sources.jsonl"
            if local.exists():
                sids = load_source_ids(local, E, W)
            fp = d / "facts.jsonl"
            fids = {}
            for ln, rec in read_jsonl(fp, E):
                where = f"{rel(fp)}:{ln}"
                e, w = check_fact(rec, where)
                E += e
                W += w
                fid = rec.get("id")
                if isinstance(fid, str):
                    if fid in fids:
                        E.append(f"{where}: id {fid} duplicates line {fids[fid]}")
                    else:
                        fids[fid] = ln
                src = rec.get("source")
                if isinstance(src, str) and src not in sids:
                    E.append(f"{where}: source {src!r} is not an id in "
                             f"{rel(local if local.exists() else sp)}")
    for w in W:
        print(f"warning: {w}")
    for e in E:
        print(f"error: {e}")
    if E:
        print(f"{len(E)} problem(s) in topic {tdir.name}")
        return 1
    print(f"ok: topic {tdir.name} is valid ({len(chapters)} chapters, {len(topic_sids)} sources"
          f"{f', {len(W)} warning(s)' if W else ''})")
    return 0


def load_source_ids(path: Path, E, W) -> set:
    ids = {}
    for ln, rec in read_jsonl(path, E):
        where = f"{rel(path)}:{ln}"
        e, w = check_source(rec, where)
        E += e
        W += w
        sid = rec.get("id")
        if isinstance(sid, str):
            if sid in ids:
                E.append(f"{where}: id {sid} duplicates line {ids[sid]}")
            else:
                ids[sid] = ln
    return set(ids)


def require_valid(state, tdir):
    E, _ = validate_state(state, tdir)
    if E:
        raise Fail("state.json has problems; fix them first:\n  " + "\n  ".join(E))


# ---------------------------------------------------------------- init / current
def cmd_init(a) -> int:
    slug = a.slug
    if not SLUG_RE.fullmatch(slug) or slug.isdigit():
        raise Fail(f"slug must be lowercase words joined by '-' (not just digits), got {slug!r}")
    if not a.title.strip():
        raise Fail("--title must not be empty")
    tdir = TOPICS / slug
    if tdir.exists():
        raise Fail(f"{rel(tdir)} already exists; refusing to overwrite (use `state.py current {slug}`)")
    (tdir / "work").mkdir(parents=True)
    state = {"slug": slug, "title": a.title.strip(), "created": today(), "goal": "",
             "lab": {"runner": "local", "toolchains": [], "notes": ""}, "parts": [], "chapters": []}
    save_state(tdir, state)
    for name in ("sources.jsonl", "glossary.jsonl", "pitfalls.md"):
        (tdir / name).write_text("", encoding="utf-8")
    CURRENT.write_text(slug + "\n", encoding="utf-8")
    print(f"created {rel(tdir)} and made it the current topic")
    return 0


def cmd_current(a) -> int:
    if a.slug:
        tdir = topic_dir(a.slug)
        CURRENT.write_text(a.slug + "\n", encoding="utf-8")
        print(f"current topic: {a.slug} ({rel(tdir)})")
    else:
        slug = current_slug()
        topic_dir(slug)
        print(slug)
    return 0


# ---------------------------------------------------------------- roadmap
def render_roadmap(state: dict) -> str:
    out = [f"# {state.get('title', state.get('slug'))}: roadmap", "",
           "<!-- Generated by tools/state.py roadmap from state.json. Do not edit by hand. -->", ""]
    goal = (state.get("goal") or "").strip()
    out += [f"**Goal.** {goal or '(not set yet)'}", ""]
    chapters = {c["n"]: c for c in state.get("chapters", []) if isinstance(c, dict) and "n" in c}
    for pi, part in enumerate(state.get("parts", [])):
        out += [f"## Part {pi + 1}: {part.get('title', '')}", ""]
        for n in part.get("chapters", []):
            ch = chapters.get(n)
            if not ch:
                continue
            out.append(f"{n}. **{ch.get('title', '')}** {MARKERS.get(ch.get('status'), '[?]')}")
            for idea in ch.get("core_ideas") or []:
                out.append(f"    - {idea}")
        out.append("")
    if not state.get("parts"):
        out += ["No chapters planned yet.", ""]
    total = len(chapters)
    done = sum(1 for c in chapters.values() if c.get("status") in ("done", "known"))
    out.append(f"Progress: {done} of {total} chapters done or known.")
    return "\n".join(out) + "\n"


def write_roadmap(tdir: Path, state: dict) -> Path:
    p = tdir / "roadmap.md"
    write_text_atomic(p, render_roadmap(state))
    return p


def cmd_roadmap(a) -> int:
    tdir = topic_dir(a.slug)
    state = load_state(tdir)
    require_valid(state, tdir)
    print(f"wrote {rel(write_roadmap(tdir, state))}")
    return 0


# ---------------------------------------------------------------- chapter-dir / next / set
def cmd_chapter_dir(a) -> int:
    tdir = topic_dir(a.slug)
    state = load_state(tdir)
    require_valid(state, tdir)
    ch = get_chapter(state, a.n)
    print(rel(ensure_chapter_dir(tdir, ch)))
    return 0


def cmd_next(a) -> int:
    tdir = topic_dir(a.slug)
    state = load_state(tdir)
    require_valid(state, tdir)
    for ch in state["chapters"]:
        if ch["status"] in ("pending", "in_progress"):
            if a.json:
                print(json.dumps(dict(ch, dir=rel(chapter_path(tdir, ch))), ensure_ascii=False))
            else:
                print(f"{ch['n']} {ch['slug']} {ch['status']}: {ch['title']}")
            return 0
    return 1


def parse_assignment(item: str):
    if "=" not in item:
        raise Fail(f"expected key=value, got {item!r} (keys: {', '.join(SETTABLE)})")
    key, val = item.split("=", 1)
    key = key.strip()
    if key not in SETTABLE:
        raise Fail(f"cannot set {key!r}; settable keys: {', '.join(SETTABLE)}")
    if key == "status":
        if val not in STATUSES:
            raise Fail(f"status must be one of {', '.join(STATUSES)}, got {val!r}")
        return key, val
    if key == "title":
        if not val.strip():
            raise Fail("title must not be empty")
        return key, val.strip()
    if key == "words":
        try:
            w = [int(x) for x in val.split(",")]
        except ValueError:
            raise Fail(f"words must be MIN,MAX integers like 4000,6000, got {val!r}")
        probs = validate_words(w, "value")
        if probs:
            raise Fail(probs[0])
        return key, w
    try:
        q = json.loads(val)
    except json.JSONDecodeError as e:
        raise Fail(f"quiz must be JSON (null or an object): {e.msg}")
    probs = validate_quiz(q, "value")
    if probs:
        raise Fail("; ".join(probs))
    return key, q


def cmd_set(a) -> int:
    tdir = topic_dir(a.slug)
    state = load_state(tdir)
    require_valid(state, tdir)
    ch = get_chapter(state, a.n)
    if not a.assignments:
        raise Fail(f"nothing to set; give key=value pairs (keys: {', '.join(SETTABLE)})")
    changes = [parse_assignment(x) for x in a.assignments]
    for key, val in changes:
        ch[key] = val
    require_valid(state, tdir)
    save_state(tdir, state)
    roadmap = write_roadmap(tdir, state)
    for key, val in changes:
        print(f"chapter {a.n}: {key} = {json.dumps(val, ensure_ascii=False)}")
    print(f"updated {rel(tdir / 'state.json')} and {rel(roadmap)}")
    return 0


# ---------------------------------------------------------------- merge
TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|_hsenc|_hsmkt|igshid|"
                      r"ref|ref_src|ref_url|source|via|spm|yclid|_ga|si)$", re.I)


def norm_url(url: str) -> str:
    u = url.strip()
    if not u:
        return ""
    s = urlsplit(u)
    scheme = s.scheme.lower()
    if scheme == "http":
        scheme = "https"
    host = (s.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = s.port
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = s.path.rstrip("/")
    query = urlencode([(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True) if not TRACKING.match(k)])
    return urlunsplit((scheme, netloc, path, query, ""))


def norm_title(t: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", t.lower()).split())


def norm_ws(s: str) -> str:
    return " ".join(s.split())


def source_index_key(rec):
    url = rec.get("url") or ""
    return ("u", norm_url(url)) if url.strip() else ("t", norm_title(rec.get("title", "")))


def cmd_merge(a) -> int:
    tdir = topic_dir(a.slug)
    state = load_state(tdir)
    E, W = [], []
    out_sources, out_facts, skipped = {}, [], []
    files = [Path(f) for f in a.files]
    if not files:
        raise Fail("give at least one scout file")
    for f in files:
        if not f.is_file():
            raise Fail(f"{f}: no such file")
    chapter, cdir = None, None
    if a.chapter is not None:
        require_valid(state, tdir)
        chapter = get_chapter(state, a.chapter)
    # topic library
    sp = tdir / "sources.jsonl"
    lib_probs = []
    library = read_jsonl(sp, lib_probs)
    if lib_probs:
        raise Fail(f"{rel(sp)} is broken; fix it first:\n  " + "\n  ".join(lib_probs))
    index, sids = {}, set()
    next_s = 1
    for _, rec in library:
        sid = rec.get("id")
        n = id_num(SID_RE, sid)
        if n is None:
            continue
        sids.add(sid)
        next_s = max(next_s, n + 1)
        index.setdefault(source_index_key(rec), sid)
    # chapter facts
    fact_seen, next_f, fp = {}, 1, None
    if chapter is not None:
        existing = existing_chapter_dir(tdir, chapter)
        fp = (existing or chapter_path(tdir, chapter)) / "facts.jsonl"
        fprobs = []
        for _, rec in read_jsonl(fp, fprobs):
            n = id_num(FID_RE, rec.get("id"))
            if n is not None:
                next_f = max(next_f, n + 1)
                fact_seen[(rec.get("source"), norm_ws(str(rec.get("quote", ""))))] = rec["id"]
        if fprobs:
            raise Fail(f"{rel(fp)} is broken; fix it first:\n  " + "\n  ".join(fprobs))
    new_sources, new_facts = [], []
    per_file_keys = []
    for f in files:
        e_start = len(E)
        recs = read_jsonl(f, E)
        dup_keys = set()
        keymap = {}  # local key -> S id
        bad_keys = set()
        # pass 1: sources
        for ln, rec in recs:
            where = f"{rel(f)}:{ln}"
            t = rec.get("type")
            if t not in ("source", "fact"):
                E.append(f"{where}: type must be \"source\" or \"fact\", got {t!r}")
                continue
            if t != "source":
                continue
            key = rec.get("key")
            e, w = check_source(rec, where, require_id=False)
            if not is_str(key):
                e.append(f"{where}: missing key (a short local name that facts use as their source)")
            elif key in keymap or key in bad_keys:
                e.append(f"{where}: key {key!r} is used twice in this file")
            extra = sorted(set(rec) - {"type", "key", *SOURCE_FIELDS})
            if extra:
                w.append(f"{where}: ignored unknown field(s) {', '.join(extra)}")
            W += w
            if e:
                E += e
                if is_str(key):
                    bad_keys.add(key)
                continue
            ik = source_index_key(rec)
            if ik in index:
                keymap[key] = index[ik]
                dup_keys.add(key)
                skipped.append({"file": rel(f), "line": ln, "type": "source", "key": key,
                                "id": index[ik], "reason": "same source already in the library"})
                continue
            sid = f"S{next_s}"
            next_s += 1
            new = {"id": sid, **{k: rec[k].strip() for k in SOURCE_FIELDS}}
            new_sources.append(new)
            index[ik] = sid
            sids.add(sid)
            keymap[key] = sid
        per_file_keys.append((f, keymap, dup_keys))
        for key, sid in keymap.items():
            name = key if out_sources.get(key, sid) == sid else f"{rel(f)}:{key}"
            out_sources[name] = sid
        # pass 2: facts
        fact_keys = set()
        for ln, rec in recs:
            if rec.get("type") != "fact":
                continue
            where = f"{rel(f)}:{ln}"
            if chapter is None:
                E.append(f"{where}: fact records need --chapter N (facts belong to a chapter)")
                continue
            e, w = check_fact(rec, where, require_id=False)
            fkey = rec.get("key")
            if fkey is not None:
                if not is_str(fkey):
                    e.append(f"{where}: key must be a non-empty string if given")
                elif fkey in fact_keys:
                    e.append(f"{where}: fact key {fkey!r} is used twice in this file")
                else:
                    fact_keys.add(fkey)
            extra = sorted(set(rec) - {"type", "key", "source", *FACT_FIELDS})
            if extra:
                w.append(f"{where}: ignored unknown field(s) {', '.join(extra)}")
            src = rec.get("source")
            sid = None
            if is_str(src):
                if src in keymap:
                    sid = keymap[src]
                elif src in bad_keys:
                    e.append(f"{where}: source {src!r} refers to a source line that was rejected above")
                elif id_num(SID_RE, src) is not None and src in sids:
                    sid = src
                else:
                    e.append(f"{where}: source {src!r} is neither a source key in this file nor an S id "
                             f"in {rel(sp)}")
            W += w
            if e:
                E += e
                continue
            label = fkey if is_str(fkey) else where
            dup = fact_seen.get((sid, norm_ws(rec["quote"])))
            if dup:
                skipped.append({"file": rel(f), "line": ln, "type": "fact", "key": label, "id": dup,
                                "reason": "same source and quote already in facts.jsonl"})
                continue
            fid = f"F{next_f}"
            next_f += 1
            new = {"id": fid, "source": sid, **{k: rec[k].strip() for k in FACT_FIELDS}}
            new_facts.append(new)
            fact_seen[(sid, norm_ws(rec["quote"]))] = fid
            out_facts.append({"key": label, "id": fid, "claim": new["claim"]})
        E[e_start:] = sorted(E[e_start:], key=lambda m: int(re.match(r".*?:(\d+): ", m).group(1)))
    # write
    append_lines(sp, new_sources)
    if new_facts:
        cdir = ensure_chapter_dir(tdir, chapter)
        append_lines(cdir / "facts.jsonl", new_facts)
        fp = cdir / "facts.jsonl"
    if a.json:
        print(json.dumps({"sources": out_sources, "facts": out_facts, "skipped": skipped,
                          "errors": E, "warnings": W}, ensure_ascii=False, indent=2))
        return 1 if E else 0
    for w in W:
        print(f"warning: {w}")
    for e in E:
        print(f"error: {e}")
    print(f"sources: {len(new_sources)} new, "
          f"{sum(1 for s in skipped if s['type'] == 'source')} already in {rel(sp)}")
    for f, keymap, dups in per_file_keys:
        for key, sid in keymap.items():
            print(f"source {key} -> {sid}" + (" (already in library)" if key in dups else " (new)"))
    if chapter is not None:
        print(f"facts: {len(new_facts)} new in {rel(fp)}, "
              f"{sum(1 for s in skipped if s['type'] == 'fact')} duplicate(s) skipped")
        for fct in out_facts:
            print(f"fact {fct['key']} -> {fct['id']}  {fct['claim'][:60]}")
        for s in skipped:
            if s["type"] == "fact":
                print(f"skipped fact {s['key']}: duplicate of {s['id']}")
    if E:
        print(f"{len(E)} record(s) rejected; fix them in the scout file and merge that file again "
              "(accepted records are deduplicated on re-merge)")
        return 1
    return 0


# ---------------------------------------------------------------- glossary
def stringify(node) -> str:
    if isinstance(node, list):
        return "".join(stringify(x) for x in node)
    if not isinstance(node, dict):
        return ""
    t = node.get("t")
    c = node.get("c")
    if t == "Str":
        return c
    if t in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if t in ("Code", "Math", "RawInline"):
        return c[-1]
    if t in ("Span", "Link", "Image"):
        return stringify(c[1])
    if t == "Quoted":
        return '"' + stringify(c[1]) + '"'
    if t in ("Cite",):
        return stringify(c[1])
    return stringify(c) if isinstance(c, list) else ""


def find_terms(node, out):
    if isinstance(node, list):
        for x in node:
            find_terms(x, out)
    elif isinstance(node, dict):
        if node.get("t") == "Span":
            (_, classes, kvs), content = node["c"]
            if "term" in classes:
                out.append((dict(kvs), stringify(content)))
        c = node.get("c")
        if isinstance(c, (list, dict)):
            find_terms(c, out)


def term_word(w: str) -> str:
    # Keep acronyms and names with inner capitals (WAL, PostgreSQL, B-tree's "B-");
    # lowercase a word that is only capitalized at its first letter.
    if sum(ch.isupper() for ch in w) >= 2:
        return w
    if w[:1].isupper() and (len(w) == 1 or not w[1].isalpha()):
        return w
    return w[:1].lower() + w[1:] if w[:1].isupper() else w


def normalize_term(text: str) -> str:
    return " ".join(term_word(w) for w in text.split())


def render_glossary(entries) -> str:
    out = ["# Glossary", "", "<!-- Generated by tools/state.py glossary from glossary.jsonl. Do not edit by hand. -->", ""]
    for e in sorted(entries, key=lambda e: (e["term"].lower(), e["term"])):
        out.append(f"**{e['term']}** (chapter {e['chapter']}). {e['def']}")
        out.append("")
    if not entries:
        out += ["No terms yet.", ""]
    return "\n".join(out)


def cmd_glossary(a) -> int:
    tdir = topic_dir(a.slug)
    state = load_state(tdir)
    require_valid(state, tdir)
    ch = get_chapter(state, a.n)
    cdir = existing_chapter_dir(tdir, ch)
    md = (cdir or chapter_path(tdir, ch)) / "chapter.md"
    if not md.is_file():
        raise Fail(f"{rel(md)} not found")
    try:
        r = subprocess.run(["pandoc", "-f", "markdown", "-t", "json", str(md)],
                           capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise Fail("pandoc is not installed; it is needed to parse .term spans")
    if r.returncode != 0:
        raise Fail(f"pandoc could not parse {rel(md)}: {r.stderr.strip()}")
    spans = []
    find_terms(json.loads(r.stdout).get("blocks", []), spans)
    gp = tdir / "glossary.jsonl"
    probs = []
    entries = [rec for _, rec in read_jsonl(gp, probs)]
    if probs:
        raise Fail(f"{rel(gp)} is broken; fix it first:\n  " + "\n  ".join(probs))
    E, W = [], []
    found = {}
    for kvs, text in spans:
        term = kvs.get("key", "").strip() or normalize_term(text)
        d = " ".join(kvs.get("def", "").split())
        if not term:
            E.append(f"{rel(md)}: a .term span has no text and no key")
            continue
        if not d:
            E.append(f"{rel(md)}: term {term!r} has no def=\"...\" attribute")
            continue
        if term.lower() in found:
            W.append(f"{rel(md)}: term {term!r} is marked more than once; only the first counts")
            continue
        found[term.lower()] = {"term": term, "def": d, "chapter": a.n}
    by_term = {e.get("term", "").lower(): e for e in entries}
    added, updated, removed = [], [], []
    kept = []
    for e in entries:  # drop this chapter's entries that are no longer marked
        if e.get("chapter") == a.n and e.get("term", "").lower() not in found:
            removed.append(e["term"])
        else:
            kept.append(e)
    entries = kept
    for low, new in found.items():
        old = by_term.get(low)
        if old is None:
            entries.append(new)
            added.append(new["term"])
        elif old.get("chapter") == a.n:
            if old.get("def") != new["def"] or old.get("term") != new["term"]:
                old.update(new)
                updated.append(new["term"])
        else:
            W.append(f"{rel(md)}: term {new['term']!r} is already in the glossary from chapter "
                     f"{old.get('chapter')}; terms are marked once per topic, so remove this mark")
    write_text_atomic(gp, "".join(jline(e) + "\n" for e in entries))
    write_text_atomic(tdir / "glossary.md", render_glossary(entries))
    for w in W:
        print(f"warning: {w}")
    for e in E:
        print(f"error: {e}")
    print(f"chapter {a.n}: {len(found)} term(s) marked; {len(added)} added, {len(updated)} updated, "
          f"{len(removed)} removed; glossary has {len(entries)} term(s)")
    for label, items in (("added", added), ("updated", updated), ("removed", removed)):
        if items:
            print(f"  {label}: {', '.join(items)}")
    print(f"wrote {rel(gp)} and {rel(tdir / 'glossary.md')}")
    return 1 if E else 0


# ---------------------------------------------------------------- status
def cmd_status(a) -> int:
    tdir = topic_dir(a.slug)
    state = load_state(tdir)
    E, _ = validate_state(state, tdir)
    chapters = [c for c in state.get("chapters") or [] if isinstance(c, dict)]
    counts = {s: sum(1 for c in chapters if c.get("status") == s) for s in STATUSES}
    cur = CURRENT.read_text(encoding="utf-8").strip() if CURRENT.is_file() else None
    print(f"topic: {state.get('title')} ({tdir.name}){'  [current]' if cur == tdir.name else ''}")
    print(f"chapters: {len(chapters)} total, {counts['done']} done, {counts['known']} known, "
          f"{counts['in_progress']} in progress, {counts['pending']} pending")
    nxt = next((c for c in chapters if c.get("status") in ("pending", "in_progress")), None)
    print(f"next: {nxt.get('n')}. {nxt.get('title')} ({nxt.get('status')})" if nxt
          else "next: none, every chapter is done or known")
    shaky = [(c, c["quiz"]) for c in chapters if isinstance(c.get("quiz"), dict) and c["quiz"].get("shaky")]
    if shaky:
        print("shaky quiz items:")
        for c, q in shaky:
            print(f"  chapter {c.get('n')} ({q.get('date')}): {'; '.join(map(str, q['shaky']))}")
    else:
        print("shaky quiz items: none")
    if E:
        print(f"state.json: {len(E)} problem(s); run `state.py validate {tdir.name}`")
    return 0


# ---------------------------------------------------------------- argument parsing
def split_slug(pos: list, need_after: int, looks_like_after):
    """Pop an optional leading slug: it is a slug if the remaining count allows it and the
    first item does not look like the following argument."""
    if pos and len(pos) > need_after and not looks_like_after(pos[0]):
        return pos[0], pos[1:]
    return None, pos


def looks_int(s):
    return bool(re.fullmatch(r"\d+", s))


def build_parser(cmd):
    p = argparse.ArgumentParser(prog=f"state.py {cmd}", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    if cmd == "init":
        p.add_argument("slug")
        p.add_argument("--title", required=True)
    elif cmd in ("current", "validate", "roadmap", "status"):
        p.add_argument("slug", nargs="?")
    elif cmd in ("chapter-dir", "glossary"):
        p.add_argument("args", nargs="+", metavar="[slug] n")
    elif cmd == "next":
        p.add_argument("slug", nargs="?")
        p.add_argument("--json", action="store_true", help="print the chapter as JSON")
    elif cmd == "set":
        p.add_argument("args", nargs="+", metavar="[slug] n key=value")
    elif cmd == "merge":
        p.add_argument("args", nargs="+", metavar="[slug] file")
        p.add_argument("--chapter", type=int, metavar="N")
        p.add_argument("--json", action="store_true", help="machine-readable result")
    else:
        return None
    return p


COMMANDS = {"init": cmd_init, "current": cmd_current, "validate": cmd_validate, "roadmap": cmd_roadmap,
            "chapter-dir": cmd_chapter_dir, "next": cmd_next, "set": cmd_set, "merge": cmd_merge,
            "glossary": cmd_glossary, "status": cmd_status}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    cmd = argv[0]
    p = build_parser(cmd)
    if p is None:
        print(f"unknown command {cmd!r}; commands: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2
    a = p.parse_intermixed_args(argv[1:])
    try:
        if cmd in ("chapter-dir", "glossary"):
            a.slug, rest = split_slug(a.args, 1, looks_int)
            if len(rest) != 1:
                raise Fail(f"usage: state.py {cmd} [slug] <n>")
            a.n = parse_n(rest[0])
        elif cmd == "set":
            a.slug, rest = split_slug(a.args, 1, looks_int)
            if not rest:
                raise Fail("usage: state.py set [slug] <n> key=value ...")
            a.n = parse_n(rest[0])
            a.assignments = rest[1:]
        elif cmd == "merge":
            a.slug, a.files = split_slug(a.args, 1, lambda s: not is_topic(s) or Path(s).is_file())
        return COMMANDS[cmd](a)
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
