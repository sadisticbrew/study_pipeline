#!/usr/bin/env python3
"""Switch model roles back to OpenCode Go when the Codex subscription ends.

Usage: python3 tools/models_opencode.py [--dry-run]

Rewrites every role in .omp/config.yml that is not already on `opencode-go/` to its
OpenCode Go model below, and drops the `# [codex]` comment lines. Roles already on
OpenCode Go (the scout) are left as they are. Prints each change.
"""
import argparse
import re
import sys
from pathlib import Path

CONFIG = Path(".omp/config.yml")

# The pre-Codex roles. The checker is DeepSeek because the writer is GLM, which keeps
# writer and checker in different model families.
OPENCODE = {
    "sp_writer": "opencode-go/glm-5.2:low",
    "sp_checker": "opencode-go/deepseek-v4-pro:high",
    "sp_scout": "opencode-go/deepseek-v4.1-flash:low",
    "sp_lab": "opencode-go/kimi-k2.7-code:high",
}

ROLE_RX = re.compile(r"^(\s+)(sp_\w+):\s*(\S+)\s*$")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="show changes, write nothing")
    args = ap.parse_args()

    if not CONFIG.exists():
        sys.exit(f"models_opencode.py: {CONFIG} not found; run from the repo root")

    out, changes = [], []
    for line in CONFIG.read_text(encoding="utf-8").splitlines(keepends=True):
        if line.startswith("# [codex]"):
            changes.append(f"drop comment: {line.strip()}")
            continue
        m = ROLE_RX.match(line)
        if m:
            indent, role, model = m.groups()
            if not model.startswith("opencode-go/"):
                if role not in OPENCODE:
                    sys.exit(f"models_opencode.py: no OpenCode model known for {role} ({model})")
                changes.append(f"{role}: {model} -> {OPENCODE[role]}")
                line = f"{indent}{role}: {OPENCODE[role]}\n"
        out.append(line)

    if not changes:
        print("Already on OpenCode Go models; nothing to change.")
        return
    print("\n".join(changes))
    if args.dry_run:
        print("(dry run: nothing written)")
        return
    CONFIG.write_text("".join(out), encoding="utf-8")
    print(f"Wrote {CONFIG}.")


if __name__ == "__main__":
    main()
