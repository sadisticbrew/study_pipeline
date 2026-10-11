"""Tiny write-ahead log: append records, crash at a chosen point, replay."""
import json
import os
import random
import subprocess
import sys

LOG = "wal.log"
OPS = [("set", f"k{i % 4}", i) for i in range(12)]


def writer(crash_after):
    with open(LOG, "a") as log:
        for n, (op, key, val) in enumerate(OPS):
            if n == crash_after:
                os._exit(1)  # simulated power cut: no cleanup at all
            log.write(json.dumps({"op": op, "key": key, "val": val}) + "\n")
            log.flush()
            os.fsync(log.fileno())  # the record is on disk before we go on


def recover():
    state = {}
    with open(LOG) as log:
        for line in log:
            rec = json.loads(line)
            state[rec["key"]] = rec["val"]  # "set" is safe to apply twice
    return state


def main():
    for seed in (1, 2, 3):
        if os.path.exists(LOG):
            os.remove(LOG)
        crash_after = random.Random(seed).randrange(1, len(OPS))
        subprocess.run([sys.executable, __file__, "write", str(crash_after)])
        expected = {}
        for _, key, val in OPS[:crash_after]:
            expected[key] = val
        state = recover()
        print(f"seed {seed}: crashed after {crash_after} of {len(OPS)} ops")
        print(f"  recovered {state}")
        print(f"  matches the first {crash_after} ops: {state == expected}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "write":
        writer(int(sys.argv[2]))
    else:
        main()
