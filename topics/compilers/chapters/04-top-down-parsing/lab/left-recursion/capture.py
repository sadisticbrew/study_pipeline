import subprocess

print("== Naive parser (default goroutine stack limit) ==", flush=True)
result = subprocess.run(["./out/parser", "naive"], capture_output=True, text=True)
lines = result.stderr.splitlines()
limits = [line for line in lines if line.startswith("runtime: goroutine stack exceeds ")]
fatal = [line for line in lines if line == "fatal error: stack overflow"]
for line in limits + fatal:
    print(line)
print(f"exit status: {result.returncode}")
if not limits or not fatal or result.returncode == 0:
    raise SystemExit("expected Go stack-overflow diagnostic was not observed")
