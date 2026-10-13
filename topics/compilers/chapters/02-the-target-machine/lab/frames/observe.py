"""Compile the same uninstrumented factorial at two optimization levels."""
from pathlib import Path
import re
import subprocess
import tempfile


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def function_assembly(path):
    lines = path.read_text().splitlines()
    start = lines.index("fact:")
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("\t.size\tfact,"))
    # Keep local branch labels and instructions, not file/debug/ABI metadata.
    return "\n".join(line for line in lines[start:end]
                     if not line.lstrip().startswith(".") or line.startswith(".L"))


print("=== gcc version ===")
print(run("gcc", "--version").splitlines()[0])
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    flags = ["-fno-asynchronous-unwind-tables", "-fcf-protection=none"]
    for level in ("O0", "O2"):
        path = work / f"{level}.s"
        run("gcc", f"-{level}", *flags, "-S", "fact.c", "-o", str(path))
        print(f"=== gcc -{level} -S fact (-fno-asynchronous-unwind-tables) ===")
        print(function_assembly(path))
    obj = work / "fact.o"
    run("gcc", "-c", str(work / "O0.s"), "-o", str(obj))
    print("=== objdump -dr: O0 fact, addresses, bytes, relocation ===")
    disassembly = run("objdump", "-dr", "--disassemble=fact", str(obj))
    print(disassembly[disassembly.index("0000000000000000 <fact>:"):].rstrip())
    binary = work / "fact"
    run("gcc", "-O0", "-g", *flags, "fact.c", "-o", str(binary))
    print("=== O0 activations: offsets from first &n ===")
    trace = run("gdb", "-q", "-nx", "-batch", "-x", "frames.gdb", str(binary))
    observations = [line for line in trace.splitlines()
                    if line.startswith("n=") or line.startswith("fact(5)")]
    print("\n".join(observations))
    frames = [tuple(map(int, match)) for match in
              re.findall(r"n=(\d+)  &n - &n_first = (-?\d+) bytes", trace)]
    assert [n for n, offset in frames] == [5, 4, 3, 2, 1], trace
    offsets = [offset for n, offset in frames]
    spacing = [b - a for a, b in zip(offsets, offsets[1:])]
    assert offsets[0] == 0 and len(set(spacing)) == 1 and spacing[0] < 0, trace
    assert "fact(5) = 120" in observations, trace
