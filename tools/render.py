#!/usr/bin/env python3
"""Render a chapter (style/FORMAT.md) to PDF via pandoc + Typst.

Usage:
  tools/render.py <chapter.md> [--theme light|dark|both] [--out-dir DIR]
                  [--facts F] [--sources S] [--topic-dir T] [--base-dir D] [--png]

Writes <stem>.pdf (light) and <stem>-dark.pdf (dark) into --out-dir (default:
the chapter's directory); chapter.md gives chapter.pdf / chapter-dark.pdf.
Intermediate files (.typ, diagrams, PNGs) go to <out-dir>/.build/<stem>/.
--png also writes page PNGs there: png/<stem>-light-NN.png, png/<stem>-dark-NN.png.

Defaults: facts from <chapter dir>/facts.jsonl; sources from
<chapter dir>/sources.jsonl if present, else <topic dir>/sources.jsonl, where
the topic dir is --topic-dir or two levels above the chapter dir.
include= paths resolve against --base-dir (default: the chapter's directory).

Exits 1 with one message per problem on: missing include file, bad lines
range, citation to an unknown fact id, fact with an unknown source id,
malformed facts/sources files, pandoc or typst failure.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "style"
FILTER = STYLE / "filter.lua"
TEMPLATE = STYLE / "template.typ"
FONTS = STYLE / "fonts"
EXPECTED_FONTS = [
    "literata/Literata-Regular.ttf",
    "literata/Literata-Italic.ttf",
    "literata/Literata-SemiBold.ttf",
    "literata/Literata-Bold.ttf",
    "inter/Inter-Regular.ttf",
    "inter/Inter-SemiBold.ttf",
    "inter/Inter-Bold.ttf",
    "jetbrains-mono-nl/JetBrainsMonoNL-Regular.ttf",
]


class RenderError(Exception):
    pass


def warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


def load_jsonl(path, kind, problems):
    """Return {id: record} from a JSON Lines file; record problems."""
    out = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"{path}:{n}: invalid JSON ({e.msg})")
            continue
        if not isinstance(rec, dict) or not isinstance(rec.get("id"), str):
            problems.append(f'{path}:{n}: {kind} record has no string "id"')
            continue
        if rec["id"] in out:
            problems.append(f"{path}:{n}: duplicate {kind} id {rec['id']}")
            continue
        out[rec["id"]] = rec
    return out


def run(cmd, what):
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise RenderError(f"{what} not found on PATH ({cmd[0]})")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("chapter", type=Path)
    ap.add_argument("--theme", choices=["light", "dark", "both"], default="both")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--facts", type=Path)
    ap.add_argument("--sources", type=Path)
    ap.add_argument("--topic-dir", type=Path)
    ap.add_argument("--base-dir", type=Path)
    ap.add_argument("--png", action="store_true", help="also write page PNGs to the build dir")
    a = ap.parse_args()

    chapter = a.chapter.resolve()
    if not chapter.is_file():
        raise RenderError(f"chapter file not found: {a.chapter}")
    cdir = chapter.parent
    stem = chapter.stem
    out_dir = (a.out_dir or cdir).resolve()
    base_dir = (a.base_dir or cdir).resolve()
    facts_path = (a.facts or cdir / "facts.jsonl").resolve()
    if a.sources:
        sources_path = a.sources.resolve()
    elif (cdir / "sources.jsonl").exists():
        sources_path = cdir / "sources.jsonl"
    else:
        topic = (a.topic_dir or cdir.parent.parent).resolve()
        sources_path = topic / "sources.jsonl"
    if a.facts and not facts_path.is_file():
        raise RenderError(f"facts file not found: {a.facts}")
    if a.sources and not sources_path.is_file():
        raise RenderError(f"sources file not found: {a.sources}")
    if not base_dir.is_dir():
        raise RenderError(f"base dir not found: {base_dir}")

    for f in EXPECTED_FONTS:
        if not (FONTS / f).is_file():
            warn(f"font file missing: {FONTS / f}; Typst will fall back to another font")

    problems = []
    facts = load_jsonl(facts_path, "fact", problems) if facts_path.is_file() else {}
    sources = load_jsonl(sources_path, "source", problems) if sources_path.is_file() else {}
    if problems:
        raise RenderError("\n".join(problems))

    build = out_dir / ".build" / stem
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    config = {
        "chapter": str(chapter),
        "base_dir": str(base_dir),
        "build_dir": str(build),
        "facts_path": str(facts_path),
        "facts_exists": facts_path.is_file(),
        "facts": {k: str(v.get("source") or "") for k, v in facts.items()},
        "sources_path": str(sources_path),
        "sources_exists": sources_path.is_file(),
        "sources": {
            k: {f: str(v.get(f) or "") for f in ("title", "url", "version")}
            for k, v in sources.items()
        },
    }
    cfg_path = build / "render-config.json"
    cfg_path.write_text(json.dumps(config, indent=1), encoding="utf-8")

    typ = build / f"{stem}.typ"
    p = run(
        [
            "pandoc", str(chapter),
            "--from", "markdown",
            "--to", "typst",
            "--standalone",
            "--template", str(TEMPLATE),
            "--lua-filter", str(FILTER),
            "--metadata", f"render-config={cfg_path}",
            "--output", str(typ),
        ],
        "pandoc",
    )
    err_file = build / "filter-errors.txt"
    if err_file.is_file():
        lines = err_file.read_text(encoding="utf-8").splitlines()
        raise RenderError("\n".join(f"{chapter.name}: {line}" for line in lines))
    if p.returncode != 0:
        raise RenderError(f"pandoc failed on {a.chapter}:\n{p.stderr.strip()}")
    if p.stderr.strip():
        print(p.stderr.strip(), file=sys.stderr)

    themes = ["light", "dark"] if a.theme == "both" else [a.theme]
    out_dir.mkdir(parents=True, exist_ok=True)
    for theme in themes:
        pdf = out_dir / (f"{stem}.pdf" if theme == "light" else f"{stem}-{theme}.pdf")
        targets = [(pdf, [])]
        if a.png:
            png_dir = build / "png"
            png_dir.mkdir(exist_ok=True)
            targets.append(
                (png_dir / f"{stem}-{theme}-{{0p}}.png", ["--format", "png", "--ppi", "110"])
            )
        for target, extra in targets:
            p = run(
                [
                    "typst", "compile",
                    "--font-path", str(FONTS),
                    "--input", f"theme={theme}",
                    *extra,
                    str(typ), str(target),
                ],
                "typst",
            )
            if p.returncode != 0:
                raise RenderError(
                    f"typst failed ({theme} theme) on {typ}:\n{p.stderr.strip()}"
                )
            if p.stderr.strip():
                print(p.stderr.strip(), file=sys.stderr)
        print(f"wrote {pdf}")
    if a.png:
        print(f"wrote PNGs to {build / 'png'}")


if __name__ == "__main__":
    try:
        main()
    except RenderError as e:
        print(f"render error: {e}", file=sys.stderr)
        sys.exit(1)
