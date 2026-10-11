## 2026-10-11 chapter 1: FLP rules out termination, not agreement
- Kind: error
- Wrong or unclear: FLP says no consensus protocol can guarantee agreement in an asynchronous system with one crash.
- Correct: FLP says no deterministic protocol can guarantee termination (a liveness property) in a fully asynchronous system with one crash. Agreement (safety) alone is achievable, and Raft keeps it unconditionally.
- Evidence: chapter 1 F32

## 2026-10-11 chapter 1: majority size needs a floor
- Kind: error
- Wrong or unclear: a majority of n servers is (n/2)+1.
- Correct: a majority of n servers is floor(n/2)+1. For n = 3 that is 2, not 2.5.
- Evidence: chapter 1 F38, F39

## 2026-10-11 chapter 2: what a returned fsync promises
- Kind: error
- Wrong or unclear: fsync only guarantees the data was handed to the device in order, so a disk cache can still lose it.
- Correct: fsync blocks until the device reports the transfer complete, including flushing a disk cache if present. The real caveat is that older kernels and some filesystems cannot flush disk caches, and then the cache must be disabled.
- Evidence: chapter 2 F11, F14

## 2026-10-11 chapter 2: PostgreSQL full page images are periodic
- Kind: error
- Wrong or unclear: PostgreSQL writes a full page image to the WAL before every page modification.
- Correct: PostgreSQL periodically writes full page images to the WAL before modifying the page on disk.
- Evidence: chapter 2 F19

## 2026-10-11 chapter 2: fsync ordering
- Kind: error
- Wrong or unclear: every write before fsync is ordered before every write after it.
- Correct: once fsync has returned, the writes it flushed are on the device, so a write issued after it returns cannot land ahead of them. fsync gives no ordering among writes that have not yet been flushed.
- Evidence: chapter 2 F11
