# Chapter 1 — Why agreeing is hard

## 1. Starting point

The reader is Pratham: a 2nd-year CS student who writes Go as a main language, has built
an OCI container runtime and an eBPF process tracer, and is comfortable with Linux
namespaces, cgroups, and the VFS. This is the **first chapter of the topic**, so no earlier
summaries or known chapters exist yet. Assume only what the profile and chapter prereqs
grant:

- Comfort writing Go programs, and the idea of programs talking over a network.
- No distributed-systems background at all. Do not assume words like "quorum",
  "consensus", "replication", or "linearizability" are already known.
- Shakier on general C and Linux-internals fundamentals; do not lean on them.

Because it is the first chapter, everything here plants seeds for later chapters. Name the
connections explicitly where they arise: the fault model (delayed, dropped, duplicated
messages; paused or rebooted servers) is the world every later chapter runs in; quorum
intersection is the counting trick that chapter 4 (log replication) will lean on for
commit safety; giving up guaranteed liveness is why chapter 3's elections use randomized
timeouts instead of a deterministic guarantee. The opening scenario should use something
in the reader's comfort zone — storing state for other programs, the way a container
runtime consults a state store like etcd — since "why does anyone even need this" is the
question this chapter answers.

## 2. Crux

**Why can't a cluster of servers that each saw the same requests just agree on what
happened — and what is the least we must assume so that they can agree at all?**

## 3. Opening situation

Pratham has built a container runtime. Somewhere in it there is state that other programs
read and write: which containers exist, their IDs, their resource limits. Today that state
sits in one place, and if that machine reboots or dies, every program depending on it
stalls or breaks. So the obvious move: store the state on three servers instead of one.
The next request comes in — `create container "web-1"` — and now a humble question turns
vicious: the three servers each heard about the request through a flaky network. Which one
of them actually decides, and what happens when the network makes them disagree about
whether the leader is even alive? This chapter is the story of why "just copy the data"
does not end the problem but starts it.

## 4. Sections

Working titles, the point each makes, a word budget, and the source ids most likely to
ground it. Budgets sum to 3200, inside the chapter's 2500–3500 range.

1. **Copy the data, inherit the problem** (~550 words)
   Replication sounds like a backup plan but is really an agreement problem: the servers
   must agree not just on each value but on one order of operations. Introduce the
   replicated state machine as the standard decomposition — deterministic state machines,
   same commands, same order — and how consensus on a log of commands replaces consensus
   on every value. Ground in the Raft paper's Section 2 framing (S1), the dissertation's
   longer motivation (S2, S9), and the 6.5840 lecture's opening framing (S11).
   Lamport's statement of what consensus must guarantee (S3) can state the target
   precisely.

2. **The world we agree in: the fault model** (~550 words)
   What can go wrong here: messages are lost, delayed, duplicated, delivered out of order;
   networks partition; servers pause and reboot, losing volatile memory. What cannot go
   wrong: nobody lies — crash-recovery faults, not Byzantine ones. Also what Raft does not
   assume: synchronized clocks. This is the contract every later chapter runs under.
   Ground in the Raft paper's problem statement and assumptions (S1) and the
   dissertation's model of asynchrony and crash-recovery (S2).

3. **Split brain: one cluster, two truths** (~650 words)
   The natural design is one leader plus followers. Walk the failure: the leader pauses or
   its heartbeats are delayed; a follower's timeout fires; it declares itself the new
   leader; the old leader is still alive and still serving a client. Now two servers each
   believe they are in charge, and each accepts writes the other never sees. This section
   carries the chapter's running example to its worst moment. Ground in the 6.5840
   lecture's "cannot distinguish dead from slow" framing (S11) and the dissertation's
   discussion of what failover cannot safely do (S2).

4. **Why the wall clock can't referee** (~450 words)
   The tempting fix: give the old leader a time limit and reject anything stamped later
   (fencing by timestamp). It fails because clocks on different machines disagree, and a
   process can pause — GC, scheduling, swap — and wake up still believing its lease is
   valid while the world has moved on. No single machine's clock is authority. This
   explains why Raft refuses to put correctness in the hands of time. Ground in the
   dissertation's timing and clock-dependence discussion (S2) and the lecture's treatment
   of pauses and clocks (S11).

5. **FLP in one paragraph: no perfect answer exists** (~550 words)
   State the result honestly but briefly: Fischer, Lynch, and Paterson proved in 1985 that
   no deterministic protocol can guarantee agreement in a fully asynchronous system if even
   one process may crash. So any usable algorithm must give something up. Raft gives up
   guaranteed liveness — it can stall in unlucky timing — but keeps safety, and assumes
   enough synchrony (broadcast time well under election timeout, timeouts well under
   mean time between failures) to finish in practice. Ground in the FLP paper itself
   (S4), the dissertation's partial-synchrony framing (S2), and the Raft paper's timing
   requirement (S1, Section 5.6 / dissertation Section 3.9).

6. **Majorities: the counting trick** (~450 words)
   If a decision must be confirmed by more than half the servers, then any two such
   decisions share at least one server — the counting argument, shown by simple arithmetic
   the reader can verify. That shared server is the witness that carries information
   forward, which is how a later decision learns an earlier one already happened. A
   concrete table: 3 servers tolerate 1 failure, 5 tolerate 2, 7 tolerate 3, and odd
   sizes buy the most tolerance per machine. Ground in the Raft paper's majority
   commitment framing (S1) and etcd's operator-facing quorum arithmetic (S28). Close by
   pointing forward: chapters 3 and 4 turn this counting trick into elections and commits.

## 5. Running example

A tiny container-registry state store, in Go spirit: a map from container name to
configuration, served on three servers, with client commands like
`create("web-1", cpu=2)` and `delete("web-1")`. Deterministic map operations make it a
clean state machine: apply the same commands in the same order and every server ends with
the identical map. The example is introduced in section 1, broken by the network in
section 2, split-brained in section 3 (the `create("web-1")` accepted by two leaders
simultaneously), wrongly "fenced" in section 4, and finally saved by majorities in
section 6. The lab (below) runs this same example.

## 6. New terms

Terms this chapter introduces (glossary is empty; exclude nothing for prior knowledge,
but the profile already grants "write-ahead log" nothing — chapter 2 owns that):

- replicated state machine
- consensus
- fault model (crash-recovery faults; contrast with Byzantine)
- split brain
- fencing (and fencing token, as the failed fix)
- safety vs. liveness
- FLP impossibility result
- partial synchrony
- majority / quorum
- quorum intersection

## 7. Misconceptions

At most two, both real and load-bearing:

1. **"Replication is a backup problem."** Learners arrive thinking copying data to more
   servers makes things safer by default. It does protect against one disk dying, but it
   creates the agreement problem: the hard part was never storing the data, it is deciding
   what happened. Address it in section 1.
2. **"A timeout tells me whether the peer is alive."** Learners treat a missed heartbeat
   as a death certificate. A timeout only proves *you* stopped hearing from them; they may
   be alive, paused, or partitioned from you but talking to others. Address it in
   sections 3 and 4 — it is exactly why split brain happens and why clocks can't referee.

## 8. Fact questions

Twelve to twenty-five precise questions grouped into batches of at most six, by source
area, with suggested source ids for each batch. Scouts should answer from the sources in
`topics/raft/sources.jsonl`; each answer needs a grounded citation.

### Batch A — The replicated state machine idea (suggest S1, S2, S3, S11)

1. How does the Raft paper's Section 2 define a replicated state machine, and what
   example use does it open with (single leader, cluster of 3–7 servers, what replaces
   them when one fails)?
2. What does the Raft paper say the consensus module on each server does — what do
   servers agree on, and what does agreement on a log of commands buy compared to
   agreeing on each value separately?
3. How does Paxos Made Simple state the safety conditions of consensus — the properties
   that must hold for a value to be chosen (which three conditions does Lamport list)?
4. What does Paxos Made Simple identify as the hard case for reaching agreement (two
   proposers, competing ballots — the "dueling proposers" scenario)?
5. How does the 6.5840 lecture frame the purpose of replication (what does a replica buy)
   and the step from "replicas hold copies" to "they must agree on order"?

### Batch B — The fault model and what Raft assumes (suggest S1, S2, S5)

6. What failure modes does the Raft paper assume for the network (lost, delayed,
   duplicated, reordered messages; partitions) — how does it phrase the network's
   behavior?
7. What fault model does the Raft paper assume for servers — crash-recovery rather than
   Byzantine — and what exactly does it say does *not* happen (no lying, no collusion)?
8. What does the Raft paper say about clocks: does Raft require or assume synchronized
   clocks, and what (if anything) does it say about physical clock correctness?
9. What availability assumption does the Raft paper make about servers after a crash
   (persistent state survives; restarted servers rejoin and become consistent)?
10. What does the etcd raft library (S5) say must be persisted — which state does its
    README require written to stable storage before messages may be sent, confirming
    that "reboot and rejoin" is a designed-for event, not an afterthought?

### Batch C — Split brain, timeouts, and the failed clock fix (suggest S11, S2, S5)

11. How does the 6.5840 lecture express the impossibility of distinguishing a dead server
    from a slow one, and what kinds of delay does it attribute to networks (slow links,
    packet loss and retransmission)?
12. What does the lecture (or dissertation) say a server pause looks like from outside
    (no heartbeats while it is actually alive — GC pauses, paging, scheduling)?
13. In the naive failover story, what exactly is the split-brain outcome — two servers
    each acting as leader — and what writes can each then accept that the other never
    sees? What does the dissertation say a failover system must not do during this
    window?
14. Why does fencing by wall-clock timestamp fail: what specific clock pathologies (skew
    between machines, pauses, jumps) make the old leader's "my lease is still valid"
    untrustworthy? What do the sources actually say about relying on clocks for safety
    (the dissertation's stance on time in Raft)?
15. What does the etcd raft library or Raft paper use instead of clocks to invalidate a
    stale leader (higher term / vote counting) — just enough to point forward without
    stealing chapter 3's thunder?

### Batch D — FLP and majorities (suggest S4, S1, S2, S28)

16. What exactly does the FLP paper prove — which system model (asynchronous, one
    crash-faulty process), which guarantee is impossible (termination/agreement in
    bounded time), and in what year was it published?
17. What does FLP's result force real consensus protocols to do instead — what do they
    give up, and what does the dissertation say Raft assumes about timing so that
    termination happens in practice (partial synchrony)?
18. What timing relationship does the Raft paper require (broadcastTime much less than
    electionTimeout much less than MTBF), and where does the paper state it? How does
    the dissertation explain each inequality's role?
19. What does the Raft paper require for a decision to be confirmed (a majority of the
    cluster), and why does the paper say a committed entry survives later elections —
    what role does the shared server between majorities play?
20. What quorum arithmetic does etcd's FAQ state: how many failures do 3, 5, and 7
    members tolerate, what is the recommended cluster size range and minimum, and why
    does it recommend odd numbers?

## 9. Lab plan

The topic's lab profile: runner `local`, Go toolchain, labs are small Go programs
simulating a cluster in one process — nodes as goroutines, a fake network that can delay,
reorder and drop messages.

- **Lab: `split-brain.go`** — demonstrates naive single-leader failover over a fake
  network. Three nodes of the running example registry (`create("web-1")` style
  commands) run as goroutines. Phase 1: one leader, two followers, a client write
  committed and visible on all three. Phase 2: the fake network silently drops
  leader-to-follower heartbeats (a partition); a follower's timeout fires; it declares
  itself leader and serves a second, conflicting write. Phase 3: print each node's view
  — and the old leader still believes it holds the lease. Expected result: `success`.
  What the output makes visible: two nodes simultaneously claiming leadership, and two
  conflicting accepted writes (`web-1` created twice with different configs) — split
  brain seen with the reader's own eyes, plus the fact that no message in the log was
  lost or corrupted: the network merely *delayed* one, which is enough. This is the
  running example of the chapter made runnable, and it plants the fake network that
  later chapters' labs will reuse.
