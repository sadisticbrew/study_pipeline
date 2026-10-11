---
topic: Storage engines
chapter: 4
title: Write-ahead logging
---

<!-- Style and format exemplar. The voice, pacing and markup here are the target for every chapter. -->

Suppose you are building a small key-value store, and you have reached the part where a `put` has to survive a crash. The obvious plan is to find the page on disk that holds the key, change it, and write it back. That plan works right up until the power fails halfway through the write. When the machine comes back, the page might hold the old value, the new value, or a torn mix of both, and your store has no way of telling which one it is looking at.

Every database has to answer this question, and the answer most of them settled on is surprisingly simple. Before you touch the real data, write down what you are about to do.

::: crux
How can a storage engine change data in place on disk and still recover to a consistent state after a crash at any moment, including the middle of a write?
:::

## The problem with changing things in place

It helps to be precise about what the hardware promises, because the whole design follows from it. A disk stores data in [sectors]{.term key="sector" def="The smallest unit of data a storage device reads or writes, usually 512 bytes or 4 KiB."}, and a database page is usually several sectors long. So a single page write is really a sequence of smaller writes, and a crash can land between any two of them. Careful engines do not even trust a single sector to be written all at once. SQLite, for example, assumes by default that a sector write can be interrupted partway through [@F1].

The trouble, then, is not that disks are unreliable in some vague way. The unit we care about, a page or a whole transaction that touches several pages, is bigger than anything the hardware will protect for us. We need to build one large all-or-nothing step out of small steps that can each be interrupted.

## Writing down the plan first

Picture a carpenter renovating a kitchen who keeps a notebook on the counter. Before she takes out a cabinet, she writes "removing the upper cabinet left of the sink, moving it to the garage". If she is called away and someone else takes over, they can read the last few lines and know exactly what state the room is in and what comes next. The notebook is cheap to write in, it only ever grows at the end, and it tells the whole story even while the kitchen itself is half finished.

A [write-ahead log]{.term def="An append-only file where every change is recorded before the change is applied to the main data files."} is that notebook. The rule is that a change may reach the data files only after the log record describing it has been flushed to permanent storage [@F2]. Once the record is safe, the engine can apply the change to the page whenever it likes, lazily and in the background. If the machine crashes, recovery reads the log and redoes every change that had not yet reached the data pages [@F3].

The analogy captures the shape of the idea, but it breaks in one important place. The carpenter's successor reads the notebook and uses judgment, while recovery code has none. Recovery often cannot tell whether a logged change already reached the page before the crash, so replaying a record that was already applied must do no harm. That property is called [idempotence]{.term def="Applying an operation more than once has the same effect as applying it exactly once."}, and it comes up again every time we look at recovery.

::: {.misconception title="The log makes every write twice as slow"}
Each change really is written twice, once to the log and later to the page. What this belief misses is the shape of those two writes. The log is written sequentially, so syncing it costs much less than flushing the scattered data pages it describes [@F4]. The page writes can then wait and be done in bulk. The result is that a database with a log can usually confirm a commit sooner than one that flushes every changed page directly.
:::

## What "flushed to permanent storage" really means

There is a quiet step hiding in the rule above. When a program calls `write`, the operating system usually copies the data into memory and returns right away, and the data reaches the device at some later point. For the log to do its job, the engine has to force each record all the way down before it lets the matching page change go out. On Linux that means calling [`fsync`]{.term key="fsync" def="A system call that waits until a file's modified data has been transferred to the storage device."} on the log file, which blocks until the device reports that the transfer has finished [@F6].

That wait is the expensive part of the whole scheme, so engines work hard to do it less often. When many small transactions finish at about the same moment, one `fsync` of the log can commit all of them together [@F5]. Each transaction waits a little longer than it would alone, and the system as a whole gets far more work done per second. This trick is usually called group commit.

::: {.aside title="Why not just fsync the page?"}
You could skip the log entirely, write the page, and call `fsync` on the data file. That still leaves the torn page from the start of the chapter, and it does nothing for a transaction that has to change two pages together. If the crash lands between the two page writes, nothing anywhere says that the first page belongs to a transaction that never finished.
:::

::: tryit
The lab for this chapter appends `set` records to a log, calling `fsync` after each one, and kills itself at a chosen point to simulate a power cut. Then it replays the log to rebuild the data. It does this for three different crash points, and each time it checks that the rebuilt state matches some prefix of the operations, never a mix.

```{.python include="lab/replay/wal_demo.py" lines="12-28"}
```

```{.output include="lab/replay/run.out"}
```

Notice that the replay loop in `recover` applies `set` records blindly. Ask yourself what would go wrong if the log held `add 10` records instead.
:::

## Check yourself

::: selftest
1. Your pages are 16 KiB and your disk writes 4 KiB sectors. Describe a crash that leaves a page in a state that never existed logically.
2. Why must replaying a log record that already reached the page be harmless? Give an example of a record that breaks this rule, and rewrite it so that it follows the rule.
3. Group commit makes each individual transaction wait a little longer. Why is it still a good trade?
:::

::: answers
1. The engine starts writing the new version of the page, the first two sectors reach the disk, and the power fails. The page now holds the first half of the new version and the second half of the old one, which matches neither.
2. Recovery often cannot tell which logged changes already reached the pages before the crash, so it may replay some of them a second time. A record like "add 10 to the balance" gives the wrong answer when applied twice. A record like "set the balance to 110" can be applied any number of times safely.
3. Most of the cost of `fsync` is a fixed wait for the device, so sharing one call among many transactions spreads that cost out. Throughput goes up a lot while each transaction's extra delay stays small.
:::
