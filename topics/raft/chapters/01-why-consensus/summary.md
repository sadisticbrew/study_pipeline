The reader now understands why replication creates an agreement problem rather than
solving one. They can state the replicated state machine decomposition: deterministic
state machines on each server, kept in sync by agreeing on a single ordered log of
commands, so consensus runs once on order instead of on every value. They know the fault
model every later chapter runs under — messages can be lost, delayed, duplicated, or
reordered, networks partition, servers crash and recover, but nothing lies (crash-recovery,
not Byzantine) — and that Raft's safety must not depend on timing or clock correctness.
They saw split brain happen in a lab: a partition cut A off from B and C, B timed out and
self-promoted, and two leaders accepted conflicting `web-1` writes. Nothing was corrupted;
the network only failed to deliver messages, including B's write to A. They know a timeout
proves only silence, never death, and why wall-clock fencing fails (clock drift, pauses),
which sets up term-based invalidation later. They can state FLP in a paragraph — no
deterministic protocol guarantees termination under pure asynchrony with one crash — and
what Raft gives up in exchange: guaranteed liveness, keeping safety. They can do the
quorum arithmetic: floor(n/2)+1, any two majorities intersect, 3/5/7 members tolerate 1/2/3
failures, odd sizes preferred.

Threads left open: what durable state survives a reboot (chapter 2), how terms and votes
actually break ties (chapter 3), and how majorities become the commit rule (chapter 4).
