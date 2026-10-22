import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import struct
import subprocess
import sys

rows = cols = 2048
n = rows * cols
# Analytic oracle: complete periods plus a final partial period of 0..1008.
periods, tail = divmod(n, 1009)
reference = periods * (1008 * 1009 // 2) + tail * (tail - 1) // 2
# Hash the exact fixture in a stated canonical representation, outside timing.
hash_input = hashlib.sha256()
for start in range(0, n, 16384):
    values = [i % 1009 for i in range(start, min(n, start + 16384))]
    hash_input.update(struct.pack('<' + 'i' * len(values), *values))
source_hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                 for p in ('kernels.c', 'bench.c', 'measure.py', 'run.sh', 'lab.json')}
process = subprocess.Popen(['./out/bench'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
checks = json.loads(process.stdout.readline())['checksums']
assert checks == [reference, reference], (checks, reference)
process.stdin.write('time\n')
process.stdin.flush()
process.stdin.close()
records = [json.loads(line) for line in process.stdout]
assert process.wait() == 0
timer = records[0]['timer_ns']
trials = records[1:]
assert len(timer) == 1001 and all(t >= 0 for t in timer)
assert len(trials) == 18
samples = [[], []]
for k, trial in enumerate(trials):
    repetition, position = divmod(k, 2)
    assert (trial['trial'], trial['position'], trial['order']) == (repetition, position, (repetition+position)%2)
    assert trial['sum'] == reference and trial['ns'] > 0
    samples[trial['order']].append(trial['ns'])
cpu = next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
            if line.startswith('model name')), platform.machine())
compiler = subprocess.check_output(['gcc','--version'], text=True).splitlines()[0]
flags = os.environ['LAB_CFLAGS']
metadata = dict(cpu=cpu, os=platform.platform(), compiler=compiler, python=sys.version.split()[0],
                flags=flags, threads=1, shape=[rows,cols], elements=n, logical_read_bytes=n*4,
                buffer_bytes=n*4, additions_per_visit=n, loads_per_visit=n,
                fixture='flat[i]=i%1009; hash uses little-endian signed int32', input_sha256=hash_input.hexdigest(),
                source_sha256=source_hashes, warmup_per_order=2, trials_per_order=9,
                clock='CLOCK_MONOTONIC', timer_pair_ns=timer, raw_trials=trials,
                cache_policy='repeated same allocation; no cache flush; not deliberately cold',
                order_control='separate translation unit, no LTO, no loop interchange/vectorization/unrolling')
Path('out/measurements.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(f'CPU: {cpu}; threads=1')
print(f'OS: {platform.platform()}; Python {sys.version.split()[0]}; {compiler}')
print(f'flags: {flags}')
print(f'shape={rows}x{cols}; buffer={n*4} bytes (16 MiB); loads=additions={n}/visit; logical read bytes={n*4}/visit')
print(f'checksums before timing: columns_inner={checks[0]} rows_inner={checks[1]} analytic={reference}')
tiny = [[0, 1, 2], [3, 4, 5]]
row_offsets = [4 * v for row in tiny for v in row]
col_offsets = [4 * v for column in zip(*tiny) for v in column]
print(f'A(2x3) offsets: columns_inner={row_offsets}; rows_inner={col_offsets}')
print('CLOCK_MONOTONIC; warmup=2/order; trials=9/order; first order alternates; one full visit/sample')
print(f'timer pair overhead ns: median={statistics.median(timer):.0f} min={min(timer)} max={max(timer)}; not subtracted')
for order, name in enumerate(('columns_inner', 'rows_inner')):
    ns = samples[order]
    ms = [x/1e6 for x in ns]
    median = statistics.median(ms)
    mad = statistics.median(abs(x-median) for x in ms)
    print(f'{name} raw ms: ' + ','.join(f'{x:.3f}' for x in ms))
    print(f'{name} median={median:.3f} ms MAD={mad:.3f} ms min={min(ms):.3f} max={max(ms):.3f}')
print('timed results consumed/checked=18; same allocation and integer workload; setup/checks/printing outside intervals')
print('order control: separate compilation/no LTO; interchange/vectorization/unrolling off for both; out/kernels.s retained')
print('cache: repeated same allocation, no flush; not a cold-cache experiment; scheduling/frequency not controlled')
print('scope: scalar CPU loop-order timings, not universal speed, DRAM traffic, or GPU throughput')
print('input sha256 (canonical little-endian int32): '+hash_input.hexdigest())
combined = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
print('source-set sha256: '+combined+'; per-file hashes/raw ns/metadata: out/measurements.json')
