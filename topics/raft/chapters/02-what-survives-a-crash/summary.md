The reader now knows what a rebooted Raft server must remember and why the rest
can be reconstructed. They can list the three persisted fields — `currentTerm`,
`votedFor`, and the log entries — and explain why `commitIndex` and
`lastApplied` are kept only in volatile memory. They understand that a server
must persist state before it sends any message that depends on that state, and
that `fsync` is the tool that makes "written to disk" mean something about
surviving a crash, though it does not by itself guarantee that a disk cache has
been flushed.

They have seen the write-ahead log as the source of truth: an append-only record
from which the state machine is rebuilt. They can replay a log after a crash and
explain why replayed operations must be idempotent, because a server may have
applied an entry once already. They connect this durability layer back to the
crash-recovery fault model from chapter 1 and forward to the election rules in
chapter 3: terms only prevent stale leaders if a server remembers its term after
a reboot.

Terms introduced: volatile state, durable state, stable storage, persisted state,
`fsync`, `fdatasync`, write-ahead log (WAL), page cache, disk write cache,
replay, and idempotent operation.

Threads left open: how a server decides when to become a candidate and how the
the term and vote rules keep elections safe (chapter 3), and how the leader
carries the log across a majority (chapter 4).
