# Brief: What survives a crash

## 1. Starting point

The reader has finished chapter 1. They know that a replicated state machine keeps
identical deterministic state machines on several servers, and that consensus is
really about agreeing on one ordered log of commands rather than on every value.
They know the crash-recovery fault model: messages can be lost, delayed,
duplicated, or reordered; networks partition; servers crash and may restart; but
no server lies. They have seen split brain happen in a simulation when a follower
timed out and promoted itself, and they know that a timeout proves silence, not
death. They can do quorum arithmetic and understand why any two majorities must
intersect.

They also know the learner, Pratham, has built an OCI container runtime and is
comfortable with processes, files, and Go, but is shaky on Linux-internals
fundamentals. So this chapter can build durability ideas from scratch using files
and processes, without assuming deep kernel knowledge, but it should not be
condescending about the basics.

This chapter must explicitly connect back to three earlier ideas:
- The crash-recovery fault model from chapter 1: servers restart, so they must
  remember enough to resume safely.
- Split brain: the next chapter will show how terms prevent stale leaders, but
  terms only work if a server remembers which term it is in after a reboot.
- Majorities and quorum intersection: durable state is what lets a server
  rejoin a majority after a crash instead of starting from a blank slate.

## 2. Crux

When a server restarts after a crash, what does it have to remember so that it
cannot break safety, and how must it write that information so the memory
survives?

## 3. Opening situation

A five-node Raft cluster has just elected a leader. The leader proposes a command
and one follower, server 3, appends it to its log and replies "yes" to the
leader. The leader counts replies, commits the command, and tells the client it
is done. Then server 3 crashes and restarts. On restart it has an empty log and
no memory of the term it was in. It immediately starts a new election in the same
term it already voted in, votes for a different candidate, and helps overwrite
the command the cluster just committed.

The opening section should make the reader feel that a reboot is not a reset
button. A server that wakes up amnesiac is dangerous, so the protocol must decide
exactly what state is worth saving and exactly when it is safe to say "saved."

## 4. Sections

1. **A server that wakes up amnesiac.** Revisit the opening scenario and make it
   concrete. Show the minimum information a rebooted server must have to avoid
   voting twice, rolling back a committed entry, or reintroducing a stale leader.
   Word budget: 500. Sources: S1, S2, S5.

2. **Volatile versus durable state.** Introduce the distinction between state
   that lives in memory and dies with the process, and state that must survive a
   reboot. Give Raft's three persisted fields: `currentTerm`, `votedFor`, and the
   log entries, and explain why everything else can be reconstructed. Word
   budget: 600. Sources: S1, S2, S5.

3. **The write-ahead log.** Explain the log as an append-only record of commands,
   and why appending is simpler and safer than updating state in place. Connect
   this to PostgreSQL WAL and SQLite rollback journals. Show that the log is the
   source of truth, and that the state machine is derived from it. Word budget:
   700. Sources: S2, S7, S8.

4. **fsync and the lie of "written to disk."** Explain the page cache, the disk
   write cache, and why `write` returning does not mean the data will survive a
   crash. Introduce `fsync` and `fdatasync` as the operations that force ordering,
   not just durability. Stress that Raft cares about write order: a server must
   persist state before it sends a message that depends on that state. Word
   budget: 700. Sources: S6, S8, S5.

5. **Replaying a log safely.** Show what happens on restart: read the persisted
   term and vote, then replay the log to rebuild the state machine. Introduce
   idempotency: the same command applied twice must leave the state machine in
   the same state as applying it once, because a reboot can happen in the middle
   of apply. Word budget: 600. Sources: S1, S2, S7.

## 5. Running example

Carry one small key-value command through the chapter. The command is
`Set("web-1", "10.0.0.7")`. It is appended to the log as entry 4 in term 2. We
watch server 3 append it, fsync, reply to the leader, crash, and restart. On
restart it reads its saved term 2, its saved vote for the leader, and its log up
through entry 4, then replays the log to rebuild the key-value store. The same
command may be replayed, so applying it a second time leaves the store unchanged.

## 6. New terms

- **volatile state:** state kept only in memory, such as the commit index and
  last applied index, which is lost when the process exits and reconstructed on
  restart.
- **durable state:** state stored on some medium that survives a process crash
  and reboot.
- **persisted state:** durable state that the protocol explicitly writes so it
  can be reloaded after a restart.
- **write-ahead log (WAL):** an append-only sequence of records describing the
  operations that must be applied to the state machine; the source of truth from
  which the state machine is rebuilt.
- **stable storage:** storage that survives crashes, typically a local disk with
  appropriate sync operations, though the Raft paper deliberately abstracts over
  the exact mechanism.
- **fsync:** a system call that forces all modified data and metadata for a file
  out to the underlying storage device, establishing an ordering boundary.
- **fdatasync:** like fsync, but forces only data and a subset of metadata,
  omitting metadata not required for later reads of the file contents.
- **page cache:** the kernel's in-memory cache of file contents; writes normally
  go here first and are flushed to disk later.
- **disk write cache:** volatile memory on the disk controller or drive itself
  that can buffer writes and lose them if power fails before the cache is flushed.
- **replay:** the act of reading a log after a crash and reapplying its entries
  to rebuild state.
- **idempotent:** an operation that produces the same result no matter how many
  times it is applied, so replaying it is safe.

## 7. Misconceptions

1. **"fsync means the data is physically on the platter."** In reality, fsync
   only guarantees that the operating system has handed the data to the storage
   device in the requested order. Some disks and controllers have write caches
   that may still lose data on power loss unless the drive is told to flush them.
2. **"As long as I fsync eventually, the order of writes does not matter."**
   Order matters deeply for Raft. A server must persist state before it sends any
   message that depends on that state; otherwise a crash can leave the system
   believing an action happened when the state that justified it was lost.

## 8. Fact questions

### Batch A: Raft persisted state and invariants (S1, S2, S5, S9)

1. Which three pieces of state does the Raft paper require a server to persist?
2. Why is `commitIndex` not among the persisted fields in the basic Raft
   algorithm?
3. What must a server do with its persisted state before it replies to a
   RequestVote or AppendEntries message?
4. If a server crashes after granting a vote in term T but before persisting
   `votedFor`, what safety property can it violate after restarting?
5. Why is persisting a log entry before replying to AppendEntries necessary for
   the Leader Completeness Property?
6. Does the basic Raft algorithm ever require a follower to persist its
   `commitIndex`? Why or why not?

### Batch B: fsync, stable storage, and ordering (S6, S8, S5)

7. What guarantee does `fsync` provide about the ordering of prior writes?
8. Why must a directory entry be synced after creating a new log file in the same
   directory?
9. Does `fsync` guarantee that data has left the disk's own volatile write cache?
   What additional measures are sometimes needed?
10. What is the difference between `fsync` and `fdatasync`?
11. In etcd's raft library, what must the application do with the `HardState`
    before it is allowed to send the messages from a `Ready`?

### Batch C: WAL, replay, and idempotency (S7, S2, S1)

12. What is the defining property of a write-ahead log compared to updating a
    database file in place?
13. Why can a write-ahead log be replayed after a crash even if the most recent
    write was only partially completed?
14. Why must operations applied during replay be idempotent?
15. In PostgreSQL, why is only the WAL required to be synced at transaction
    commit, rather than the data files that store the actual tables?
16. What does SQLite assume about sector writes when it explains its atomic
    commit procedure?

### Batch D: Production practice (S5, S28)

17. Why does etcd's raft README say the application must fsync before sending
    messages from a `Ready`?
18. What is the recommended minimum and maximum number of etcd members, and why
    is an odd count preferred?

## 9. Lab plan

There are three small Go labs. Each runs with the local Go runner and uses the
file system (a temp directory) as the durable medium.

1. **Lost vote.** Demonstrates that in-memory state is not enough.
   - What it shows: a server that grants a vote in term 2 but only keeps
     `currentTerm` and `votedFor` in memory loses that vote on crash. After
     restart it grants another vote in term 2, violating one vote per term.
   - Runner: local Go.
   - Expected result: failure (the program prints a safety violation and exits
     nonzero).
   - Output should make visible: the first vote grant, the simulated crash and
     restart, and the second vote grant in the same term.

2. **Persisted vote.** Demonstrates the fix.
   - What it shows: the same server persists `currentTerm` and `votedFor` to a
     file and fsyncs before replying to RequestVote. After a crash and restart it
     refuses to vote again in the same term.
   - Runner: local Go.
   - Expected result: success.
   - Output should make visible: the persisted file contents after the vote, the
     crash and restart, and the refusal of the duplicate vote.

3. **WAL replay.** Demonstrates the write-ahead log and idempotent replay.
   - What it shows: a small key-value store appends `Set` commands to a WAL file,
     fsyncs, applies them to an in-memory map, and then simulates a crash. On
     restart it replays the WAL from the beginning, rebuilding the map. Replaying
     entries that were already applied before the crash does not change the map.
   - Runner: local Go.
   - Expected result: success.
   - Output should make visible: the WAL entries, the map before the crash, the
     replay trace, and the final map after replay.
