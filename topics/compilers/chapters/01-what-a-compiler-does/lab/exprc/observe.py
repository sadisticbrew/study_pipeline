"""Observe file boundaries and process status; SIGFPE is an expected child event."""
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

compiler = sys.argv[1]
driver = Path("driver.c").resolve()

with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    for name, expression in [("example", "(7 + 5) * 3 - 6"),
                             ("division", "10 / (5 - 5)")]:
        assembly = work / f"{name}.s"
        with assembly.open("w") as output:
            compiled = subprocess.run([compiler, expression], stdout=output, check=True)
        print(f"exprc {expression!r}: exit={compiled.returncode}", flush=True)
        if name == "example":
            print("files after exprc: " + ", ".join(sorted(p.name for p in work.iterdir())))
            print("--- example.s ---")
            print(assembly.read_text(), end="", flush=True)
        subprocess.run(["gcc", "-c", str(assembly), "-o", str(work / f"{name}.o")], check=True)
        subprocess.run(["gcc", str(driver), str(work / f"{name}.o"),
                        "-o", str(work / name)], check=True)
        if name == "example":
            print("gcc -c example.s -o example.o; gcc driver.c example.o -o example")
            print("files after gcc: " + ", ".join(sorted(p.name for p in work.iterdir())))
        result = subprocess.run([str(work / name)], capture_output=True, text=True)
        print(f"{name}: stdout={result.stdout.strip()!r}")
        if result.returncode < 0:
            print(f"{name}: signal={signal.Signals(-result.returncode).name} (returncode={result.returncode})")
        else:
            print(f"{name}: exit={result.returncode}")
        if name == "example":
            assert result.returncode == 0 and result.stdout == "30\n", result
        else:
            assert result.returncode == -signal.SIGFPE, result
