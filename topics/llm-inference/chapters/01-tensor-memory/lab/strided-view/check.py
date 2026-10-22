import json
import subprocess

# Values come from nested-list operations; offsets use the selected fixture IDs.
a = [[0, 1, 2], [3, 4, 5]]
t = [list(column) for column in zip(*a)]
s = [row[1:] for row in a]
r = [row[::-1] for row in a]
flat = lambda rows: [value for row in rows for value in row]
bytes_of = lambda rows: [4 * value for value in flat(rows)]
expected = {
    "A": (0, [2, 3], [12, 4], bytes_of(a), flat(a)),
    "T": (0, [3, 2], [4, 12], bytes_of(t), flat(t)),
    "S": (4, [2, 2], [12, 4], bytes_of(s), flat(s)),
    "R": (8, [2, 3], [12, -4], bytes_of(r), flat(r)),
    "reshape": (0, [3, 2], [8, 4], bytes_of(a), flat(a)),
    "bias": (0, [2, 3], [0, 4], [0, 4, 8] * 2, [10, 20, 30] * 2),
    "copy": (0, [3, 2], [8, 4], bytes_of(a), flat(t)),
    "sum": (0, [2, 3], [12, 4], bytes_of(a), [v+b for row in a for v,b in zip(row, [10,20,30])]),
    "restored": (0, [2, 3], [12, 4], bytes_of(a), flat(a)),
    "row_bias": (0, [2, 3], [4, 0], [0]*3 + [4]*3, [10]*3 + [20]*3),
    "row_sum": (0, [2, 3], [12, 4], bytes_of(a), [v+b for row,b in zip(a, [10,20]) for v in row]),
    "step": (0, [3], [8], [0,8,16], flat(a)[::2]),
    "step_matrix": (0, [3,1], [8,8], [0,8,16], flat(a)[::2]),
    "rank3": (0, [1,2,3], [24,12,4], bytes_of(a), flat(a)),
    "overlap": (0, [256], [0], [0]*256, [0]*256),
    "stride_limit": (0, [1], [65536], [0], [0]),
    "negative_stride_limit": (0, [1], [-65536], [0], [0]),
    "last_element": (20, [256], [0], [20]*256, [5]*256),
    "singleton": (0, [2,1,3], [12,-65536,4], bytes_of(a), flat(a)),
    "singleton_reshape": (0, [3,2], [8,4], bytes_of(a), flat(a)),
    "capacity_limit": (65532, [1], [0], [65532], [42]),
    "capacity_min": (0, [1], [0], [0], [7]),
}
rejections = set('''negative_index index_at_extent huge_index second_axis_extent readonly_store
transpose_reshape step_reshape_policy reshape_count reshape_huge broadcast_incompatible
truncated_element tiny_capacity capacity_domain negative_capacity reverse_underrun origin_one_past
negative_origin origin_domain origin_huge rank_zero rank_four empty_axis negative_axis
 dimension_domain huge_dimension stride_domain negative_stride_domain stride_min stride_max
positive_reach_overrun negative_reach_underrun null_storage maximum_origin_one_past
broadcast_lower_rank broadcast_rank_four broadcast_empty broadcast_huge'''.split())
records = [json.loads(line) for line in subprocess.check_output(["./out/view"], text=True).splitlines()]
views = {}; rejected = set(); aliases = []
for record in records:
    if "name" in record:
        name = record["name"]
        assert name not in views
        origin, shape, strides, offsets, values = expected[name]
        assert (record["origin"], record["shape"], record["strides"]) == (origin, shape, strides), name
        assert record["offsets"] == offsets, name
        assert record["values"] == values, name
        assert record["readonly"] == (name in ("bias", "row_bias")), name
        views[name] = record
    elif "reject" in record:
        assert record["accepted"] is False, record
        assert record["reject"] not in rejected
        rejected.add(record["reject"])
    else:
        assert record["alias"] == [500, 500, 5]
        aliases.append(record["alias"])
assert set(views) == set(expected) and rejected == rejections and len(aliases) == 1
print("platform: CHAR_BIT=8 sizeof(int32_t)=4; A=[[0,1,2],[3,4,5]]; capacity=24 bytes")
for name in ("A", "T", "S", "R", "reshape", "bias"):
    v = views[name]
    print(f'{name}: origin={v["origin"]} shape={v["shape"]} strides={v["strides"]}' + (" readonly" if v["readonly"] else ""))
print(f'A[1,2]: offset={views["A"]["offsets"][5]} value={views["A"]["values"][5]}; T[2,1]: offset={views["T"]["offsets"][5]} value={views["T"]["values"][5]}')
for name in ("T", "S", "R"):
    print(f'{name} logical order: offsets={views[name]["offsets"]}; values={views[name]["values"]}')
print(f'copy(T) values={views["copy"]["values"]}; reshape(A) values={views["reshape"]["values"]}')
print(f'write T[2,1]=500: T={aliases[0][0]} A[1,2]={aliases[0][1]} copy(T)[2,1]={aliases[0][2]}; restored A[1,2]={views["restored"]["values"][5]}')
print(f'bias[0,2]/bias[1,2]: offsets={views["bias"]["offsets"][2]}/{views["bias"]["offsets"][5]}; A+b values={views["sum"]["values"]} (separate array)')
print(f'row bias (2,1): strides={views["row_bias"]["strides"]}; values={views["row_sum"]["values"]}; bias (2,) rejected')
print(f'step-two view -> (3,1): offsets={views["step_matrix"]["offsets"]} values={views["step_matrix"]["values"]}; narrow reshape API rejects step input')
print('rejected: index=-1/extent/INT64_MAX; capacity=23; reverse origin=0; readonly write; INT64_MIN/MAX strides')
print('domain: rank=1..3 extent=1..256 capacity=4..65536 origin=0..65536 |stride|<=65536; empty/scalar unsupported')
print(f'singleton reshape values={views["singleton_reshape"]["values"]}; capacity=65536 last offset={views["capacity_limit"]["offsets"][0]} value={views["capacity_limit"]["values"][0]}')
print(f'independent comparisons: descriptors={len(views)} offsets={sum(len(v["offsets"]) for v in views.values())} values={sum(len(v["values"]) for v in views.values())} alias_events={len(aliases)} rejections={len(rejected)}')
