"""Capture function bodies, omitting assembly metadata/directives outside the idea."""
from pathlib import Path
import re
import subprocess
import tempfile

source = Path("f.c").resolve()
version = subprocess.check_output(["llc", "--version"], text=True)
registered = set(re.findall(r"^\s+(\S+)\s+-", version, re.MULTILINE))
# Prefer a familiar second ISA, but accept other installed integer backends.
candidates = [("aarch64", "aarch64-linux-gnu"), ("riscv64", "riscv64-linux-gnu"),
              ("arm", "armv7-linux-gnueabi"), ("ppc64", "powerpc64-linux-gnu"),
              ("mips", "mips-linux-gnu"), ("loongarch64", "loongarch64-linux-gnu"),
              ("bpf", "bpfel")]
targets = ["x86_64-linux-gnu"]
for backend, triple in candidates:
    if backend in registered:
        targets.append(triple)
        break

with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    command = ["clang", "--target=x86_64-linux-gnu", "-S", "-emit-llvm", "-O1",
               "-fno-discard-value-names", str(source), "-o", "f.ll"]
    print("clang --target=x86_64-linux-gnu -S -emit-llvm -O1 -fno-discard-value-names f.c -o f.ll")
    subprocess.run(command, cwd=work, check=True)
    ir = work / "f.ll"
    # C IR is not generally target-neutral. This function has only i32 arithmetic:
    # remove x86 CPU attributes and layout/triple once, before either llc invocation.
    text = re.sub(r'^target (?:datalayout|triple) = .*\n', '', ir.read_text(), flags=re.MULTILINE)
    text = re.sub(r' "(?:target-cpu|target-features|tune-cpu)"="[^"]*"', '', text)
    ir.write_text(text)
    print("f.ll: removed target layout/triple and CPU attributes once (scalar i32 example)")
    print("--- f.ll: function body ---")
    body = re.search(r"^define .*?^}", text, re.MULTILINE | re.DOTALL)
    if body is None:
        raise RuntimeError("no LLVM function body found")
    print(body.group())
    for triple in targets:
        command = ["llc", f"-mtriple={triple}", "-asm-verbose=false", "f.ll", "-o", "f.s"]
        print(f"--- llc -mtriple={triple} -asm-verbose=false f.ll -o f.s ---")
        subprocess.run(command, cwd=work, check=True)
        lines = (work / "f.s").read_text().splitlines()
        active = False
        count = 0
        for line in lines:
            if line.startswith("f:"):
                active = True
            if active and line.startswith(".Lfunc_end"):
                break
            # Output contains the actual label/instructions, not CFI or blank lines.
            clean = line.split("//", 1)[0].rstrip()
            if active and clean and not clean.lstrip().startswith((".", "#")):
                print(clean)
                count += 1
        if count == 0:
            raise RuntimeError(f"no assembly function body found for {triple}")
    if len(targets) == 1:
        print("No second integer backend from the candidate list is registered.")
        print(version[version.index("Registered Targets:"):].rstrip())
