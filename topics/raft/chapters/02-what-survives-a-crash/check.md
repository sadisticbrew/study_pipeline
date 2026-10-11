# Check report — chapter 2: What survives a crash

**Summary:** supported 26 (all distinct fact citations check out), miscited 0, stretched 0, unsupported 1 (fixed), contradicted 0, output mismatch 0, misleading simplification 0.

| Line | Category | Original text (shortened) | Change | Evidence |
|---|---|---|---|---|
| 67 | unsupported | "SQLite uses a rollback journal for the same purpose, recording the old state of a page before the page is changed, and its atomic-commit procedure assumes… [@F24]" | Added `[@F30]` after the rollback-journal clause; `[@F24]` now covers only the sector-write clause. | F30 (new fact from S8, §3.5: "SQLite first creates a separate rollback journal file and writes into the rollback journal the original content of the database pages that are to be altered.") |

## What I checked and found sound

- Every cited claim matches its fact at the stated strength. In particular F1 (three persisted fields), F2 (commitIndex reinitializable to zero), F5/F7 (vote and log-entry persistence), F9/F10 (commit index optional; etcd HardState), F18/F23/F24 (WAL rule, PostgreSQL, SQLite sector writes), F11–F16 (fsync/fdatasync), F19/F20 (full page images, CRC-32C), F21 (persistent last-applied index), F22 (ARIES LSN), F3/F4/F26 (persist before responding; etcd Ready ordering), F27/F29 (quorum and member count), F6/F8 (election safety, leader completeness).
- All three labs' descriptions match `run.out`: `lost-vote` (double vote, safety violation), `persisted-vote` (reload `term=2 votedFor=A`, refuse), `wal-replay` (map rebuilt from WAL).
- The `floor(n/2)+1` wording in answer 5 is the corrected form called for in `pitfalls.md`; no FLP claim appears.

## Doubts for a human

- **Line 41:** "the Raft paper deliberately leaves abstract … in practice it is usually a local disk" is a characterization the single citation `[@F1]` does not literally contain (F1 states persistent state goes to *stable storage*). It is a fair gloss and appears verbatim in the brief, so I left it, but a stricter citation would split the "abstract mechanism" claim from the "persisted fields" claim.
- **Line 45:** "even the server's role as follower, candidate, or leader: all of these are derived from the three persisted fields plus messages from peers." A restarted server does not *derive* its role — it starts as a follower by convention. The intent (role need not be persisted) is correct, so I did not edit, but the word "derived" is slightly stronger than the mechanism.
- **Line 21:** "the leader commits the entry on the strength of that yes" in a five-node cluster could imply one follower's yes commits the entry; the next sentence ("because a majority had it") corrects this, so I left it.

## Human review, 2026-10-11

The checker missed three errors, all corrected by hand and recorded in `topics/raft/pitfalls.md`: the first misconception box contradicted F11 about fsync and disk caches (line 87), the PostgreSQL full-page-image sentence dropped "periodically" (line 119), and the fsync ordering sentence overstated F11 (line 79). The fact summaries of F11 and F19 overstated their quotes and were corrected. The checker now judges claims against verbatim quotes only.
