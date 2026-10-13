"""Observe contract variants as child processes, including real signal exits."""
from pathlib import Path
import signal
import subprocess
import tempfile


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def observe(binary):
    child = subprocess.run([str(binary)], capture_output=True, text=True)
    status = (f"signal={signal.Signals(-child.returncode).name} (returncode={child.returncode})"
              if child.returncode < 0 else f"exit={child.returncode}")
    return child, status


print("=== gcc version ===")
print(run("gcc", "--version").splitlines()[0])
print("=== correct sum3: assembly source ===")
print(Path("correct.s").read_text().rstrip())
print("=== caller: live rbx across sum3 (hand-written, not gcc-selected) ===")
print("\n".join(Path("probe.s").read_text().splitlines()[7:14]))
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    flags = ["-O2", "-fcf-protection=none", "-fno-asynchronous-unwind-tables"]
    print("=== callee-saved register variants ===")
    for variant, expected_after in (("correct", 1000), ("clobber", 60)):
        binary = work / variant
        run("gcc", *flags, "driver.c", "probe.s", f"{variant}.s", "-o", str(binary))
        child, status = observe(binary)
        print(f"{variant}: {child.stdout.strip()}; {status}")
        assert child.returncode == 0, child
        assert child.stdout == f"sum3(10,20,30) = 60; caller rbx: 1000 -> {expected_after}\n", child
    print("=== vector_local: gcc -O2 instructions at aligned store ===")
    assembly = work / "vector.s"
    run("gcc", *flags, "-S", "vector.c", "-o", str(assembly))
    lines = assembly.read_text().splitlines()
    store = next((i for i, line in enumerate(lines) if "movaps" in line and "(%rsp)" in line), None)
    if store is not None:
        start = lines.index("vector_local:")
        print(next(line.strip() for line in lines[start:store]
                   if "subq" in line and "%rsp" in line))
        print("\n".join(line.strip() for line in lines[store - 1:store + 2]))
    else:
        print("no movaps store to rsp in this gcc output")
    print("=== stack alignment variants ===")
    aligned = work / "aligned"
    run("gcc", *flags, "alignment-driver.c", "vector.c", "alignment.S", "-o", str(aligned))
    child, status = observe(aligned)
    print(f"aligned: {child.stdout.strip()}; {status}")
    assert child.returncode == 0 and child.stdout == "sum3(10,20,30) = 60\n", child
    misaligned = work / "misaligned"
    run("gcc", *flags, "-DMISALIGNED", "alignment-driver.c", "vector.c", "alignment.S", "-o", str(misaligned))
    attempts = [observe(misaligned) for _ in range(5)]
    if store is not None and all(child.returncode == -signal.SIGSEGV for child, status in attempts):
        print(f"misaligned: stdout={attempts[0][0].stdout!r}; {attempts[0][1]}; attempts=5/5")
    else:
        print("misaligned variant dropped: no repeatable aligned-store SIGSEGV")
        for index, (child, status) in enumerate(attempts, 1):
            print(f"attempt {index}: stdout={child.stdout!r}; {status}")
