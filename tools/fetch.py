#!/usr/bin/env python3
"""Download a source once, as plain text, into the topic cache, and fail fast.

Usage (run from the repo root; [slug] defaults to topics/.current):
  fetch.py [slug] <url | S-id> [--max-time SECONDS] [--force]

Prints one line that starts with OK, PARTIAL or UNREADABLE. OK gives the path of a local
text copy to read or grep. PDFs are converted with pdftotext and carry "[pdf page N]"
markers, and a symbol with no text form, often a math symbol such as ε, shows as U+FFFD.
HTML is converted with pandoc and ends with a list of the page's links. Other text is
stored as it is, so source files keep their line numbers.

- A URL that is already in topics/<slug>/cache/ is never downloaded again.
- An S-id is read from the learner's own copy at topics/<slug>/library/<S-id>.<ext>
  (pdf, epub, html, htm, txt or md) when there is one, otherwise from its URL in
  sources.jsonl.
- Dead links, stalls (under 1 KB/s for 20 s), HTTP errors, scanned PDFs and binary files
  are recorded in topics/<slug>/unreachable.jsonl. A permanent failure (such as a 404 or a
  scanned PDF) makes fetch.py refuse the URL at once for 30 days. A network failure does so
  for 6 hours only once two separate calls have failed, because on a flaky connection a
  link that failed once often works on the next try. --force tries again.
- A download still running at --max-time (default 50 s, under the 60 s after which an
  agent's shell command is moved to the background) keeps its partial file, and running
  the same command again resumes it.

Exit codes: 0 OK, 1 UNREADABLE, 2 usage error, 3 PARTIAL (run the same command again).
"""

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import html.parser
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urldefrag, urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state import Fail, norm_url, read_jsonl, rel, topic_dir  # noqa: E402

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) study-pipeline-fetch"
CONNECT_TIMEOUT = 10
STALL_BYTES, STALL_SECONDS = 1024, 20
MAX_FILESIZE = "150M"
REFUSE_FOR = {"network": datetime.timedelta(hours=6), "permanent": datetime.timedelta(days=30)}
NETWORK_FAILURES_TO_REFUSE = 2
LIBRARY_EXTS = (".pdf", ".epub", ".html", ".htm", ".txt", ".md")
NETWORK_REASONS = {6: "dns-failure", 7: "connect-failed", 28: "timed-out", 35: "tls-failure",
                   52: "empty-reply", 56: "connection-reset"}
PERMANENT_CURL = {3: "bad-url", 51: "bad-certificate", 60: "bad-certificate", 63: "too-large"}
SID_RE = re.compile(r"S[1-9]\d*")


class Unreadable(Exception):
    def __init__(self, reason, detail, kind="permanent"):
        super().__init__(detail)
        self.reason, self.detail, self.kind = reason, detail, kind


class Partial(Exception):
    """Out of time with a partial file that the next call resumes."""

    def __init__(self, total):
        super().__init__(total)
        self.total = total


def mb(n: float) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 100_000 else f"{n / 1e3:.0f} KB"


@contextlib.contextmanager
def locked(path: Path):
    """Exclusive lock, so two agents fetching the same URL download it once."""
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def now():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------- unreachable record
def refusal(tdir: Path, url: str):
    """(record, until) when url is refused now, else None. A permanent failure refuses at
    once; network failures refuse while NETWORK_FAILURES_TO_REFUSE of them are recent."""
    key, recent = norm_url(url), {"permanent": [], "network": []}
    for _, rec in read_jsonl(tdir / "unreachable.jsonl", []):
        if norm_url(str(rec.get("url", ""))) != key:
            continue
        try:
            at = datetime.datetime.fromisoformat(rec["at"])
        except (KeyError, TypeError, ValueError):
            continue
        kind = "permanent" if rec.get("kind") == "permanent" else "network"
        if at + REFUSE_FOR[kind] > now():
            recent[kind].append((at, rec))
    if recent["permanent"]:
        at, rec = recent["permanent"][-1]
        return rec, at + REFUSE_FOR["permanent"]
    net = recent["network"]
    if len(net) >= NETWORK_FAILURES_TO_REFUSE:
        # Refused until the older of the counted failures expires.
        return net[-1][1], net[-NETWORK_FAILURES_TO_REFUSE][0] + REFUSE_FOR["network"]
    return None


def record_failure(tdir: Path, url: str, u: Unreadable):
    rec = {"url": url, "reason": u.reason, "kind": u.kind, "detail": u.detail,
           "at": now().isoformat(timespec="seconds")}
    with open(tdir / "unreachable.jsonl", "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- download
def download(url: str, part: Path, deadline: float):
    """Fetch url into part, resuming it if present. Return (content_type, final_url) when
    complete; raise Partial when out of time with a partial file, Unreadable otherwise."""
    misses, restarted, total = 0, False, None
    while True:
        before = part.stat().st_size if part.exists() else 0
        remaining = max(5, int(deadline - time.monotonic()))
        cmd = ["curl", "--silent", "--show-error", "--location", "--fail",
               "--connect-timeout", str(CONNECT_TIMEOUT),
               "--speed-limit", str(STALL_BYTES), "--speed-time", str(STALL_SECONDS),
               "--max-time", str(remaining), "--max-filesize", MAX_FILESIZE,
               "--user-agent", USER_AGENT, "--output", str(part),
               "--write-out", "%{http_code}\t%{content_type}\t%{url_effective}\t"
                              "%header{content-range}\t%header{content-length}"]
        if before:
            cmd += ["--continue-at", "-"]
        r = subprocess.run(cmd + [url], capture_output=True, text=True)
        code, ctype, final, crange, clen = (r.stdout.split("\t") + [""] * 5)[:5]
        if r.returncode == 0:
            return ctype, final or url
        after = part.stat().st_size if part.exists() else 0
        http = int(code) if code.isdigit() else 0
        m = re.search(r"/(\d+)\s*$", crange)
        if m or clen.strip().isdigit():
            total = int(m.group(1)) if m else int(clen) + (before if http == 206 else 0)
        detail = (r.stderr.strip().splitlines() or [f"curl exit {r.returncode}"])[-1]
        time_left = deadline - time.monotonic() > 5
        if before and (r.returncode == 33 or http == 416) and not restarted:
            part.unlink(missing_ok=True)  # the server will not resume; start over
            restarted = True
            continue
        if r.returncode == 22 and 400 <= http < 500 and http not in (408, 429):
            raise Unreadable(f"http-{http}", detail)
        if r.returncode in PERMANENT_CURL:
            raise Unreadable(PERMANENT_CURL[r.returncode], detail)
        if after > before and time_left:
            continue
        if after and not time_left:
            raise Partial(total)
        misses += 1
        if misses < 2 and time_left:
            continue
        reason = f"http-{http}" if http >= 400 else NETWORK_REASONS.get(r.returncode, "network-error")
        raise Unreadable(reason, detail, "network")


# ---------------------------------------------------------------- conversion
def decode(data: bytes, ctype: str) -> str:
    m = (re.search(r"charset=([\w.-]+)", ctype or "", re.I)
         or re.search(rb"<meta[^>]+charset=[\"']?([\w.-]+)", data[:4096], re.I))
    names = [m.group(1).decode() if isinstance(m.group(1), bytes) else m.group(1)] if m else []
    for enc in names + ["utf-8"]:
        try:
            return data.decode(enc)
        except (LookupError, UnicodeDecodeError):
            pass
    return data.decode("latin-1")


class LinkCollector(html.parser.HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base, self.href, self.words, self.links = base, None, [], {}

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.close_link()
            self.href, self.words = dict(attrs).get("href"), []

    def handle_endtag(self, tag):
        if tag == "a":
            self.close_link()

    def handle_data(self, data):
        if self.href is not None:
            self.words.append(data)

    def close_link(self):
        href, self.href = self.href, None
        if not href:
            return
        url = urldefrag(urljoin(self.base, href.strip()))[0]
        if url.startswith(("http://", "https://")) and url != urldefrag(self.base)[0]:
            self.links.setdefault(url, " ".join("".join(self.words).split()))


def pandoc(fmt: str, data: bytes) -> str:
    r = subprocess.run(["pandoc", "-f", fmt, "-t", "plain", "--wrap=none"], input=data,
                       capture_output=True, timeout=180)
    if r.returncode != 0:
        raise Unreadable("not-text", "pandoc failed: " + r.stderr.decode(errors="replace").strip()[:200])
    return r.stdout.decode("utf-8", "replace")


def html_text(path: Path, ctype: str, base: str) -> str:
    page = decode(path.read_bytes(), ctype)
    text = pandoc("html", page.encode("utf-8"))
    links = LinkCollector(base)
    links.feed(page)
    links.close_link()
    if links.links:
        text = text.rstrip() + "\n\n--- links on this page (added by tools/fetch.py) ---\n" + "".join(
            f"{words or '(no text)'} -> {url}\n" for url, words in links.links.items())
    return text


# pdftotext emits a glyph that its font maps to no Unicode character as a raw control
# character, which is invisible when read. Math fonts do this for symbols such as ε and ≠,
# so "i ≠ j" silently reads "i = j". MISSING makes the gap visible.
MISSING = "\ufffd"
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]")


def pdf_text(path: Path) -> str:
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, timeout=180)
    if r.returncode != 0:
        raise Unreadable("not-text", "pdftotext failed: " + r.stderr.decode(errors="replace").strip()[:200])
    pages = CONTROL_RE.sub(MISSING, r.stdout.decode("utf-8", "replace")).split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    chars = sum(len("".join(p.split())) for p in pages)
    if chars < 20 * max(1, len(pages)):
        raise Unreadable("scanned-pdf", f"{len(pages)} pages but only {chars} characters of text")
    return "".join(f"[pdf page {i}]\n{p.rstrip()}\n" for i, p in enumerate(pages, 1))


def to_text(path: Path, ctype: str, base: str):
    """Return (kind, text) for a downloaded or library file."""
    head = path.open("rb").read(8192)
    low, ctype = head.lstrip()[:1024].lower(), (ctype or "").lower()
    suffix = path.suffix.lower()
    if head.startswith(b"%PDF") or "pdf" in ctype or suffix == ".pdf":
        return "pdf", pdf_text(path)
    if "epub" in ctype or suffix == ".epub":
        return "epub", pandoc("epub", path.read_bytes())
    if "html" in ctype or suffix in (".html", ".htm") or low.startswith(b"<!doctype html") or b"<html" in low:
        return "html", html_text(path, ctype, base)
    if b"\0" in head:
        raise Unreadable("not-text", f"binary content ({ctype or 'unknown type'})")
    return "text", decode(path.read_bytes(), ctype)


# ---------------------------------------------------------------- output
def store(txt: Path, kind: str, text: str, origin: str):
    txt.write_text(text, encoding="utf-8")
    txt.with_suffix(".json").write_text(json.dumps(
        {"origin": origin, "kind": kind, "fetched": datetime.date.today().isoformat()}) + "\n")


def ok(txt: Path, cached: bool, note=None) -> int:
    meta = json.loads(txt.with_suffix(".json").read_text())
    text = txt.read_text(encoding="utf-8")
    print(f"OK {rel(txt)}  ({text.count(chr(10))} lines, {meta['kind']}, fetched {meta['fetched']}"
          f"{', already cached' if cached else ''})")
    if meta["kind"].endswith("pdf"):
        print("note: [pdf page N] markers count PDF pages, which can differ from the printed page "
              "numbers; in locators, give the section and the printed page.")
        missing = text.count(MISSING)
        if missing:
            print(f"note: {missing} symbols in this PDF have no text form and show as {MISSING}. They "
                  f"are often math symbols such as ε, ≠ or ∉, so a formula with {MISSING} is missing "
                  "a symbol. Quote it as it stands and do not fill the symbol in.")
    if note:
        print(note)
    return 0


def unreadable(what: str, why: str) -> int:
    print(f"UNREADABLE {what}: {why}. Do not retry it; use another source or skip the question.")
    return 1


# ---------------------------------------------------------------- main
def from_library(tdir: Path, sid: str, src: Path) -> int:
    txt = tdir / "cache" / f"{sid}.txt"
    with locked(txt.with_suffix(".lock")):
        if txt.exists() and txt.stat().st_mtime >= src.stat().st_mtime:
            return ok(txt, True)
        try:
            kind, text = to_text(src, "", src.as_uri())
        except Unreadable as u:
            return unreadable(rel(src), f"{u.reason} ({u.detail})")
        store(txt, f"library {kind}", text, rel(src))
    return ok(txt, False)


def fetch(tdir: Path, target: str, a) -> int:
    (tdir / "cache").mkdir(exist_ok=True)
    note = None
    if SID_RE.fullmatch(target):
        srcs = {rec.get("id"): rec for _, rec in read_jsonl(tdir / "sources.jsonl", [])}
        if target not in srcs:
            raise Fail(f"{target} is not in {rel(tdir / 'sources.jsonl')}")
        lib = tdir / "library"
        copies = sorted(p for p in lib.glob(f"{target}.*") if p.suffix.lower() in LIBRARY_EXTS)
        if copies:
            return from_library(tdir, target, copies[0])
        src, url = srcs[target], (srcs[target].get("url") or "").strip()
        if not url:
            return unreadable(target, f"no URL, and no copy in {rel(lib)}/ (the learner can add "
                                      f"one as {target}.pdf)")
        if src.get("kind") == "book":
            note = (f"note: {target} is a book with no copy in {rel(lib)}/. This is the page at "
                    "its URL, which may not hold the book's text.")
    elif re.match(r"https?://", target):
        url = target
    else:
        raise Fail("give an http(s) URL or an S-id such as S7")

    key = hashlib.sha256(norm_url(url).encode()).hexdigest()[:16]
    txt = tdir / "cache" / f"{key}.txt"
    with locked(txt.with_suffix(".lock")):
        if txt.exists():
            return ok(txt, True, note)
        refused = None if a.force else refusal(tdir, url)
        if refused:
            rec, until = refused
            return unreadable(url, f"{rec.get('reason')} on {rec['at'][:16].replace('T', ' ')} UTC "
                                   f"({rec.get('detail')}); not tried again before "
                                   f"{until.isoformat(timespec='minutes')[:16].replace('T', ' ')} UTC")
        part = txt.with_suffix(".part")
        start, t0 = (part.stat().st_size if part.exists() else 0), time.monotonic()
        try:
            ctype, final = download(url, part, t0 + a.max_time)
            kind, text = to_text(part, ctype, final)
        except Partial as p:
            n = part.stat().st_size
            rate = (n - start) / max(1.0, time.monotonic() - t0)
            mins = max(1, round((p.total - n) / rate / 60)) if p.total and rate > 0 else 0
            left = f", so about {mins} more minute{'s' if mins > 1 else ''} at this speed" if mins else ""
            print(f"PARTIAL {url}: {mb(n)}{' of ' + mb(p.total) if p.total else ''} so far, "
                  f"at about {rate / 1e3:.0f} KB/s{left}. Run the same command again to "
                  "continue, or use another source if that is too slow.")
            return 3
        except Unreadable as u:
            record_failure(tdir, url, u)
            if u.kind == "permanent":
                part.unlink(missing_ok=True)
                return unreadable(url, f"{u.reason} ({u.detail}); recorded in "
                                       f"{rel(tdir / 'unreachable.jsonl')} so other agents skip it")
            then = ("so other agents skip it" if refusal(tdir, url)
                    else "and refused for 6 hours if one more call fails")
            return unreadable(url, f"{u.reason} ({u.detail}); recorded in "
                                   f"{rel(tdir / 'unreachable.jsonl')}, {then}")
        store(txt, kind, text, url)
        part.unlink(missing_ok=True)
    return ok(txt, False, note)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fetch.py", description=__doc__,
                                 usage="fetch.py [slug] <url | S-id> [--max-time SECONDS] [--force]",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("args", nargs="+", metavar="[slug] target")
    ap.add_argument("--max-time", type=int, default=50, metavar="SECONDS",
                    help="give up on this call after this long (default 50)")
    ap.add_argument("--force", action="store_true", help="try a URL recorded as unreadable again")
    a = ap.parse_args(argv)
    try:
        if len(a.args) > 2:
            raise Fail("usage: fetch.py [slug] <url | S-id>")
        slug, target = (a.args if len(a.args) == 2 else [None, a.args[0]])
        return fetch(topic_dir(slug), target.strip(), a)
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
