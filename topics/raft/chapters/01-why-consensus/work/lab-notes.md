# Lab notes: split-brain

## Lab metadata

- **Name:** `split-brain`
- **Directory:** `topics/raft/chapters/01-why-consensus/lab/split-brain/`
- **Runner:** `local` (bubblewrap sandbox, no network)
- **Toolchain:** Go
- **Expected result:** `success` (exit 0)

## What it demonstrates

A naive single-leader container-registry cluster (three nodes, map from container name
to `Config`) running over a fake in-memory network. The lab shows that delaying/dropping
*heartbeats* is enough to split the cluster: a follower times out, promotes itself, and
accepts a conflicting write while the old leader still believes it is in charge.

This is the chapter 1 running example made runnable, and it introduces the fake-network
pattern later labs reuse.

## Source file line ranges for chapter includes

All line numbers refer to `lab/split-brain/split-brain.go`.

- **`Registry` state machine (lines 16-38):** the tiny container registry — a map from
  container name to config. Shows the deterministic state machine the chapter talks about.
- **Fake network and partition (lines 40-93):** `Network` routes messages through
  per-node buffered channels and `Drop(from, to)` silently discards one direction.
  This is the concrete network fault model.
- **Naive node and self-promotion (lines 110-120, 158-196):** a follower tracks the last
  heartbeat and, when the election timeout expires, calls `becomeLeader()`. There is no
  voting or term comparison — this is the *naive* design the chapter is showing fail.
- **Propose / replication (lines 198-204):** a leader writes locally and fans the write
  out to its peers. Fire-and-forget is enough here because the phases wait for delivery.
- **Main orchestration (lines 213-255):** the three phases spelled out in order:
  1. A is leader, write `web-1 cpu=2`.
  2. Drop A↔B/C, wait for B's timeout.
  3. Write `web-1 cpu=4` to B, then print every node's view.

The most important include for the chapter is probably **lines 213-255** plus the final
output, because that is the story the reader follows.

## What `run.out` shows

```
== Phase 1: A leader, client writes web-1 cpu=2 ==
== Phase 2: partition A from B,C; B times out and becomes leader ==
[B] timeout: promoting self to leader
== Phase 3: new client writes web-1 cpu=4 to leader B ==
== Result: each node's view ==
node A: leader, registry map[web-1:{cpu:2}]
node B: leader, registry map[web-1:{cpu:4}]
node C: follower, registry map[web-1:{cpu:4}]

No client write was lost or corrupted: only heartbeats were dropped.
```

### Output line by line

1. `== Phase 1: A leader, client writes web-1 cpu=2 ==`  
   Sets the starting state: one accepted write on the leader.
2. `== Phase 2: partition A from B,C; B times out and becomes leader ==`  
   The network partition begins; heartbeats from A to B and C are dropped.
3. `[B] timeout: promoting self to leader`  
   B has not heard from A, concludes A is gone, and declares itself leader.
4. `== Phase 3: new client writes web-1 cpu=4 to leader B ==`  
   A second, conflicting write is accepted by the new leader.
5. `== Result: each node's view ==`  
   Header for the money shot.
6. `node A: leader, registry map[web-1:{cpu:2}]`  
   The *old* leader still believes it holds the lease and still has the first value.
7. `node B: leader, registry map[web-1:{cpu:4}]`  
   The *new* leader has accepted a conflicting write for the same key.
8. `node C: follower, registry map[web-1:{cpu:4}]`  
   C follows B because B's heartbeats still reach C; C now has the second value.
9. `No client write was lost or corrupted: only heartbeats were dropped.`  
   Reinforces the chapter's point: no message was lost or corrupted — the network
   merely delayed/dropped heartbeats, and that alone was enough to create split brain.

## Two-line summary for the writer

The lab shows node A still claiming leadership with `web-1={cpu:2}` while node B also
claims leadership with `web-1={cpu:4}`, and node C follows B — split brain caused
entirely by dropped heartbeats, with no client write lost or corrupted.
