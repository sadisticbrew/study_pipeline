#!/usr/bin/env python3
"""Run and check chapter labs (lab/<name>/ with lab.json + run.sh).

Usage:
  lab.py run <chapter-dir> [--only NAME] [--topic-dir D]
      Run every lab (or only NAME) in a fresh temp copy of its directory and write
      run.out and run.status.json back into the lab dir. Exit 1 if any lab is not ok.
  lab.py check <chapter-dir> [--topic-dir D]
      Report each lab as fresh / stale / missing / failed. Exit 1 unless all are fresh.
  lab.py doctor [--toolchains go,rustc,gcc,...] [--boot]
      Report which runners work here (bwrap sandbox, vng + /dev/kvm) and which
      toolchains are on PATH. --boot really boots a vng guest (slow). Exit 1 if any
      checked item is unavailable.

<chapter-dir> may also be the path of a chapter.md; its directory is used.
Settings merge: lab.json > topic state.json "lab" > built-ins
(runner "local", expect "success", timeout 60, network false). The topic dir is
<chapter-dir>/../.. when the path looks like topics/<slug>/chapters/<NN-slug>/,
otherwise only --topic-dir provides one.

Runners: local = bubblewrap sandbox (host / read-only, only the temp workdir writable,
no network unless "network": true); vng = virtme-ng VM booting the host kernel, root
in the guest; none = never run (status records ok true, no run.out).

A lab may write files for the chapter (generated figures, traces) into out/. After a run,
<lab>/out/ is replaced by the workdir's out/ (removed if the run made none); it is not
part of the hash, so editing it never makes a lab stale.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BUILTIN = {"runner": "local", "expect": "success", "timeout": 60, "network": False}
RUNNERS = ("local", "vng", "none")
EXPECTS = ("success", "failure")
OUTPUT_FILES = ("run.out", "run.status.json")
OUTPUT_DIR = "out"  # files the lab writes for the chapter; kept, and not part of the hash
MAX_LINES = 400
HEAD_LINES = 300  # kept from the top when truncating; the rest comes from the tail
FAIL_TAIL = 15


class LabError(Exception):
    pass


# ---------------------------------------------------------------- hashing
# Lab input hash; tools/lint.py imports this function, so it is the only definition:
#   h = sha256()
#   walk the lab dir with os.walk(followlinks=False); take every entry that is a file
#   (os.path.isfile, so symlinks to files count with their target's bytes);
#   rel = path relative to the lab dir, as a POSIX string;
#   skip rel == "run.out" and rel == "run.status.json" (top level only), and every rel
#   that starts with "out/" (the kept output directory);
#   sort by rel (plain str order); for each: h.update(rel.encode("utf-8") + b"\0" + bytes)
#   result = h.hexdigest()
def lab_hash(lab_dir: Path) -> str:
    rels = []
    for root, _dirs, files in os.walk(lab_dir, followlinks=False):
        for name in files:
            full = os.path.join(root, name)
            if not os.path.isfile(full):
                continue
            rel = Path(os.path.relpath(full, lab_dir)).as_posix()
            if rel in OUTPUT_FILES or rel.startswith(OUTPUT_DIR + "/"):
                continue
            rels.append(rel)
    h = hashlib.sha256()
    for rel in sorted(rels):
        with open(lab_dir / rel, "rb") as f:
            h.update(rel.encode("utf-8") + b"\0" + f.read())
    return h.hexdigest()


# ---------------------------------------------------------------- settings
def chapter_dir_of(arg: str) -> Path:
    p = Path(arg)
    if p.is_file():
        p = p.parent
    if not p.is_dir():
        raise LabError(f"{arg}: not a directory (give the chapter directory or its chapter.md)")
    return p


def derive_topic_dir(chapter_dir: Path):
    r = chapter_dir.resolve()
    if (re.fullmatch(r"\d\d-.+", r.name) and r.parent.name == "chapters"
            and r.parent.parent.parent.name == "topics"):
        return r.parent.parent
    return None


def topic_defaults(topic_dir) -> dict:
    if topic_dir is None:
        return {}
    state = Path(topic_dir) / "state.json"
    if not state.is_file():
        return {}
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise LabError(f"{state}: cannot read lab defaults: {e}")
    lab = data.get("lab") if isinstance(data, dict) else None
    if not isinstance(lab, dict):
        return {}
    return {k: lab[k] for k in BUILTIN if k in lab}


def validate_settings(s: dict, where: str):
    problems = []
    if s.get("runner") not in RUNNERS:
        problems.append(f'runner must be one of {", ".join(RUNNERS)}, got {s.get("runner")!r}')
    if s.get("expect") not in EXPECTS:
        problems.append(f'expect must be "success" or "failure", got {s.get("expect")!r}')
    t = s.get("timeout")
    if isinstance(t, bool) or not isinstance(t, (int, float)) or t <= 0:
        problems.append(f"timeout must be a positive number of seconds, got {t!r}")
    if not isinstance(s.get("network"), bool):
        problems.append(f'network must be true or false, got {s.get("network")!r}')
    if problems:
        raise LabError(f"{where}: " + "; ".join(problems))


def lab_settings(lab_dir: Path, defaults: dict) -> dict:
    lj = lab_dir / "lab.json"
    try:
        own = json.loads(lj.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LabError(f"{lj}: invalid JSON: {e}")
    if not isinstance(own, dict):
        raise LabError(f"{lj}: must be a JSON object like {json.dumps(BUILTIN)}")
    unknown = sorted(set(own) - set(BUILTIN))
    if unknown:
        raise LabError(f"{lj}: unknown key(s) {', '.join(unknown)}; allowed: {', '.join(BUILTIN)}")
    merged = dict(BUILTIN)
    merged.update(defaults)
    merged.update(own)
    validate_settings(merged, str(lj))
    return merged


def find_labs(chapter_dir: Path, only=None):
    """Return (labs, problems): labs = sorted list of lab dirs that have lab.json and run.sh."""
    root = chapter_dir / "lab"
    labs, problems = [], []
    if not root.is_dir():
        if only:
            problems.append(f"{root}: no lab directory, so there is no lab {only!r}")
        return labs, problems
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if only and d.name != only:
            continue
        missing = [f for f in ("lab.json", "run.sh") if not (d / f).is_file()]
        if missing:
            problems.append(f"{d}: missing {' and '.join(missing)} (every lab needs lab.json and run.sh)")
            continue
        labs.append(d)
    if only and not labs and not problems:
        names = sorted(p.name for p in root.iterdir() if p.is_dir())
        problems.append(f"{root}: no lab named {only!r} (labs: {', '.join(names) or 'none'})")
    return labs, problems


# ---------------------------------------------------------------- output cleaning
ANSI_RE = re.compile(
    r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC
    r"|\x1b\[[0-?]*[ -/]*[@-~]"  # CSI
    r"|\x1b[@-Z\\-_]"  # other 2-byte escapes
)


def clean_output(raw: bytes, workdir: str) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = ANSI_RE.sub("", text)
    text = text.replace("\r\n", "\n")
    for w in sorted({workdir, os.path.realpath(workdir)}, key=len, reverse=True):
        text = text.replace(w, ".")
    lines = []
    for line in text.split("\n"):
        if "\r" in line:  # progress-bar style overwrites: keep what was finally shown
            line = line.rsplit("\r", 1)[1]
        lines.append(line.rstrip())
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) > MAX_LINES:
        tail = MAX_LINES - HEAD_LINES
        cut = len(lines) - MAX_LINES
        lines = lines[:HEAD_LINES] + [f"[... {cut} lines truncated by tools/lab.py ...]"] + lines[-tail:]
    return "\n".join(lines) + "\n" if lines else ""


# ---------------------------------------------------------------- runners
PASS_ENV = ("PATH", "LANG", "LC_ALL", "GOROOT", "GOTOOLCHAIN", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN",
            "JAVA_HOME", "PKG_CONFIG_PATH")


def bwrap_cmd(workdir: str, network: bool) -> list:
    if not shutil.which("bwrap"):
        raise LabError("runner local needs bubblewrap (bwrap) on PATH; install it or set runner none")
    home = os.path.join(workdir, ".home")
    cache = os.path.join(workdir, ".cache")
    cmd = [
        "bwrap",
        "--ro-bind", "/", "/",          # whole host read-only (home included)
        "--dev", "/dev",
        "--tmpfs", "/dev/shm",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
        "--tmpfs", "/run",              # hides host sockets (dbus, docker, wayland, ...)
    ]
    if network:
        cmd += ["--ro-bind-try", "/run/systemd/resolve", "/run/systemd/resolve"]
    cmd += [
        "--bind", workdir, workdir,     # the only writable host path
        "--unshare-all",
    ]
    if network:
        cmd.append("--share-net")
    cmd += ["--die-with-parent", "--new-session", "--chdir", workdir, "--clearenv"]
    env = {k: os.environ[k] for k in PASS_ENV if k in os.environ}
    env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
    real_rustup = os.path.join(os.path.expanduser("~"), ".rustup")
    if "RUSTUP_HOME" not in env and os.path.isdir(real_rustup):
        env["RUSTUP_HOME"] = real_rustup  # rustup proxies on PATH still find their toolchains
    env.update({
        "HOME": home,
        "XDG_CACHE_HOME": cache,
        "TMPDIR": "/tmp",
        "USER": os.environ.get("USER", "lab"),
        "TERM": "dumb",
    })
    env.setdefault("LANG", "C.UTF-8")
    for k, v in sorted(env.items()):
        cmd += ["--setenv", k, v]
    os.makedirs(home, exist_ok=True)
    os.makedirs(cache, exist_ok=True)
    return cmd + ["bash", "run.sh"]


def kvm_problem():
    if not os.path.exists("/dev/kvm"):
        return ("/dev/kvm does not exist: KVM is unavailable (no hardware virtualization, "
                "kvm module not loaded, or running inside a VM without nested virt)")
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        return ("/dev/kvm is not readable and writable by this user: add the user to the "
                "'kvm' group (then log in again) or fix the device permissions")
    return None


def vng_cmd(workdir: str, network: bool) -> list:
    if not shutil.which("vng"):
        raise LabError("runner vng needs virtme-ng (vng) on PATH; install it or use runner local")
    prob = kvm_problem()
    if prob:
        raise LabError(f"runner vng: {prob}. Use runner local if the lab does not need root or its own kernel")
    cmd = ["vng", "--run", "--user", "root", "--rwdir", workdir, "--cwd", workdir]
    if network:
        cmd += ["--network", "user"]
    return cmd + ["--exec", "bash run.sh"]


def run_process(cmd: list, cwd: str, timeout: float):
    """Run cmd in its own process group; return (exit_or_None, timed_out, output_bytes)."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, False, out
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = proc.communicate()
        return None, True, out
    except BaseException:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        raise


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def remove_kept_out(lab_dir: Path):
    kept = lab_dir / OUTPUT_DIR
    if kept.is_dir() and not kept.is_symlink():
        shutil.rmtree(kept)
    elif kept.exists() or kept.is_symlink():
        kept.unlink()


def run_lab(lab_dir: Path, settings: dict) -> dict:
    """Run one lab and write its outputs. Returns the status dict plus 'output' text."""
    runner, expect, timeout, network = (settings[k] for k in ("runner", "expect", "timeout", "network"))
    digest = lab_hash(lab_dir)
    if runner == "none":
        out_file = lab_dir / "run.out"
        if out_file.exists():
            out_file.unlink()  # output of a never-run lab must not be included
        remove_kept_out(lab_dir)
        status = {"ok": True, "exit": None, "expect": expect, "runner": "none", "duration_s": 0.0,
                  "hash": digest, "ran_at": now_iso(), "timed_out": False}
        write_json(lab_dir / "run.status.json", status)
        return dict(status, output="")
    tmp = tempfile.mkdtemp(prefix=f"lab-{lab_dir.name}-")
    try:
        workdir = os.path.join(tmp, "w")
        shutil.copytree(lab_dir, workdir, symlinks=True,
                        ignore=lambda d, names: [n for n in names if n in OUTPUT_FILES or n == OUTPUT_DIR]
                        if Path(d) == lab_dir else [])
        cmd = bwrap_cmd(workdir, network) if runner == "local" else vng_cmd(workdir, network)
        start = time.monotonic()
        code, timed_out, raw = run_process(cmd, workdir, timeout)
        duration = round(time.monotonic() - start, 2)
        text = clean_output(raw, workdir)
        if timed_out:
            text += f"[tools/lab.py: killed after the {timeout}s timeout]\n"
        remove_kept_out(lab_dir)
        produced = Path(workdir) / OUTPUT_DIR
        if produced.is_dir() and not produced.is_symlink():
            shutil.copytree(produced, lab_dir / OUTPUT_DIR, symlinks=False, ignore_dangling_symlinks=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok = (not timed_out) and ((code == 0) if expect == "success" else (code not in (0, None)))
    (lab_dir / "run.out").write_text(text, encoding="utf-8")
    status = {"ok": ok, "exit": code, "expect": expect, "runner": runner, "duration_s": duration,
              "hash": digest, "ran_at": now_iso(), "timed_out": timed_out}
    write_json(lab_dir / "run.status.json", status)
    return dict(status, output=text)


# ---------------------------------------------------------------- commands
def resolve_topic(args, chapter_dir: Path):
    if args.topic_dir:
        if not Path(args.topic_dir).is_dir():
            raise LabError(f"--topic-dir {args.topic_dir}: not a directory")
        return Path(args.topic_dir)
    return derive_topic_dir(chapter_dir)


def cmd_run(args) -> int:
    chapter_dir = chapter_dir_of(args.chapter_dir)
    defaults = topic_defaults(resolve_topic(args, chapter_dir))
    labs, problems = find_labs(chapter_dir, args.only)
    for p in problems:
        print(f"ERROR {p}")
    if not labs and not problems:
        print(f"{chapter_dir}: no labs (nothing under lab/)")
        return 0
    bad = len(problems)
    for lab in labs:
        rel = f"lab/{lab.name}"
        try:
            s = lab_settings(lab, defaults)
            res = run_lab(lab, s)
        except LabError as e:
            print(f"ERROR {rel}: {e}")
            bad += 1
            continue
        if res["runner"] == "none":
            print(f"SKIP  {rel}: runner none (not run, ok)")
            continue
        if res["timed_out"]:
            how = f"timed out after {s['timeout']}s"
        else:
            how = f"exit {res['exit']}, expected {res['expect']}"
        tag = "OK   " if res["ok"] else "FAIL "
        print(f"{tag} {rel}: {how}, runner {res['runner']}, {res['duration_s']}s")
        if not res["ok"]:
            bad += 1
            tail = res["output"].rstrip("\n").split("\n")[-FAIL_TAIL:] if res["output"] else ["(no output)"]
            print(f"      last {len(tail)} lines of {rel}/run.out:")
            for line in tail:
                print(f"      | {line}")
    return 1 if bad else 0


def lab_check(lab: Path, defaults: dict):
    """Return (state, detail) with state in fresh/stale/missing/failed."""
    s = lab_settings(lab, defaults)
    sf = lab / "run.status.json"
    if not sf.is_file():
        return "missing", "never run: run tools/lab.py run"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
        if not isinstance(st, dict):
            raise ValueError("not an object")
    except (OSError, ValueError) as e:
        return "missing", f"run.status.json unreadable ({e}): rerun"
    if st.get("hash") != lab_hash(lab):
        return "stale", "lab files changed since the last run: rerun"
    changed = [k for k in ("runner", "expect") if st.get(k) != s[k]]
    if changed:
        return "stale", f"settings changed since the last run ({', '.join(changed)}): rerun"
    if s["runner"] != "none" and not (lab / "run.out").is_file():
        return "missing", "run.out missing: rerun"
    if st.get("ok") is not True:
        why = "timed out" if st.get("timed_out") else f"exit {st.get('exit')}, expected {st.get('expect')}"
        return "failed", f"last run failed ({why}); see run.out"
    return "fresh", f"ok, runner {st.get('runner')}, ran {st.get('ran_at')}"


def cmd_check(args) -> int:
    chapter_dir = chapter_dir_of(args.chapter_dir)
    defaults = topic_defaults(resolve_topic(args, chapter_dir))
    labs, problems = find_labs(chapter_dir)
    for p in problems:
        print(f"ERROR {p}")
    if not labs and not problems:
        print(f"{chapter_dir}: no labs")
        return 0
    bad = len(problems)
    for lab in labs:
        try:
            state, detail = lab_check(lab, defaults)
        except LabError as e:
            state, detail = "invalid", str(e)
        if state != "fresh":
            bad += 1
        print(f"{state:<8} lab/{lab.name}: {detail}")
    return 1 if bad else 0


def tool_version(path: str) -> str:
    for args in (["--version"], ["version"], ["-V"]):
        try:
            r = subprocess.run([path] + args, capture_output=True, text=True, timeout=10,
                               stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = (r.stdout or r.stderr).strip()
        if r.returncode == 0 and text:
            return text.splitlines()[0].strip()
    return "(version unknown)"


def cmd_doctor(args) -> int:
    bad = 0
    # bwrap: actually create a sandbox like the local runner does
    if not shutil.which("bwrap"):
        print("FAIL runner local: bwrap not found on PATH (install bubblewrap)")
        bad += 1
    else:
        with tempfile.TemporaryDirectory(prefix="lab-doctor-") as tmp:
            cmd = bwrap_cmd(tmp, False)[:-2] + ["bash", "-c", "touch ok"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
                works = r.returncode == 0 and os.path.exists(os.path.join(tmp, "ok"))
                err = (r.stderr or r.stdout).strip()
            except subprocess.TimeoutExpired:
                works, err = False, "timed out"
        if works:
            print("ok   runner local: bubblewrap sandbox works")
        else:
            print(f"FAIL runner local: bwrap could not create the sandbox: {err or 'unknown error'} "
                  "(unprivileged user namespaces may be disabled: check kernel.unprivileged_userns_clone "
                  "or apparmor_restrict_unprivileged_userns)")
            bad += 1
    # vng
    vng = shutil.which("vng")
    prob = kvm_problem()
    if not vng:
        print("FAIL runner vng: vng (virtme-ng) not found on PATH")
        bad += 1
    elif prob:
        print(f"FAIL runner vng: {prob}")
        bad += 1
    elif args.boot:
        with tempfile.TemporaryDirectory(prefix="lab-doctor-") as tmp:
            Path(tmp, "run.sh").write_text('echo "uid=$(id -u) kernel=$(uname -r)"\n')
            try:
                code, timed_out, out = run_process(vng_cmd(tmp, False), tmp, 180)
            except LabError as e:
                code, timed_out, out = None, False, str(e).encode()
        text = clean_output(out, tmp).strip()
        want = f"uid=0 kernel={os.uname().release}"
        if code == 0 and want in text:
            print(f"ok   runner vng: booted the host kernel, {want}")
        else:
            last = "\n".join(text.split("\n")[-FAIL_TAIL:])
            print(f"FAIL runner vng: test boot failed ({'timeout' if timed_out else f'exit {code}'}):\n{last}")
            bad += 1
    else:
        print(f"ok   runner vng: {vng} found and /dev/kvm usable (use --boot to test a real boot)")
    # toolchains
    names = [t.strip() for t in (args.toolchains or "").split(",") if t.strip()]
    for name in names:
        path = shutil.which(name)
        if path:
            print(f"ok   toolchain {name}: {path} ({tool_version(path)})")
        else:
            print(f"FAIL toolchain {name}: not found on PATH")
            bad += 1
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="lab.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run", help="run labs and write run.out / run.status.json")
    p.add_argument("chapter_dir")
    p.add_argument("--only", metavar="NAME", help="run only lab/NAME")
    p.add_argument("--topic-dir", metavar="D", help="topic dir for state.json lab defaults")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("check", help="report fresh/stale/missing/failed per lab")
    p.add_argument("chapter_dir")
    p.add_argument("--topic-dir", metavar="D", help="topic dir for state.json lab defaults")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("doctor", help="report which runners and toolchains work here")
    p.add_argument("--toolchains", metavar="LIST", help="comma-separated, e.g. go,rustc,gcc,python3")
    p.add_argument("--boot", action="store_true", help="really boot a vng guest to test it")
    p.set_defaults(fn=cmd_doctor)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except LabError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
