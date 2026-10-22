Supported: 39 unchanged paragraph units; miscited: 0; stretched: 3; unsupported: 2; contradicted: 7; output mismatch: 3; misleading simplification: 10; stretched facts: 3; remaining [@unverified]: 0.

Counts classify individual findings, not sentences: several findings share a paragraph. The initial `claims.py` output contained 57 prose paragraph units; 18 units needed changes, leaving 39 supported unchanged units. Line numbers below remain unchanged by the repairs.

| Line | Category | Change | Evidence |
|---|---|---|---|
| 36, term definition | misleading simplification | Remove the definition's per-input-row restriction, which would exclude grouped result expressions. | F63; roadmap chapter 4 |
| 36 | stretched | Replace an exact evaluation-count promise with computation from each retained row. | F63; F2 |
| 36 | output mismatch | Stop claiming the immediately following queries contain a word-valued filter. | `lab/query-results/queries.sql:4-7` |
| 68 | contradicted | Correct hypothetical zero-discount payables to 1299 and 800, not two 1299 values. | Opening rows 102/104; `lab/query-results/run.out:4-6` |
| 103 | misleading simplification | Remove the claim that every Python object necessarily completes a Boolean branch. | [Python data model, truth-testing overflow caveat](https://docs.python.org/3/reference/datamodel.html#object.__len__) |
| 103 | stretched | Attribute undefined subexpression evaluation order specifically to PostgreSQL, as the cited quotes do. | F20; F71 |
| 106 | misleading simplification | Distinguish uncertain sequence from membership when both qualifying rows fit the limit. | F25; F28; `lab/query-results/run.out:30-32` |
| 110 | misleading simplification | Say there is no specified first pair, not that no pair can be returned. | F21; F23; F28 |
| 135 | output mismatch | Include the known-zero filter when claiming the repeatable pair is 101, 105. | `lab/query-results/run.out:29-32` |
| 151 | misleading simplification | Name integer division explicitly; the previous pronoun could incorrectly refer to exact numeric. | F48; F49; F50; F72 |
| 166 | unsupported | Add evidence that SQLite ignores declared numeric parameters; observed values alone cannot establish scale enforcement. | New F96 |
| 166 | misleading simplification | Qualify storage-class flexibility by constraints, including the displayed NOT NULL declarations. | F7; `lab/query-results/seed.sql:1-8` |
| 170 | stretched | Restrict the arithmetic rule to addition, subtraction, multiplication, and division. | F46; SQLite datatype documentation §5 |
| 185 | misleading simplification | Qualify digit-string ordering as bytewise rather than universal across collations. | F30; F32; F83 |
| 187 | unsupported | Cite the actual default-column-collation rule, not merely BINARY's comparison behavior. | New F95; F30 |
| 197 | misleading simplification | Different places can show different clock readings; different places need not have different offsets. | F43; elementary offset arithmetic |
| 201 | contradicted | Restrict accepted-layout limitations to date/time functions, not SQLite's arbitrary stored text. | F34; F36; F44; F7 |
| 201 | output mismatch | Describe two zone spellings rather than two nonzero-offset spellings. | `lab/values-and-time/run.out:21-23` |
| 209, 242 | contradicted | Explain that raw comparison uses local fields without accounting for offsets, not displaced offset characters. | F35; F43; `lab/values-and-time/run.out:20-26` |
| 209 | misleading simplification | Mixed-offset raw strings need not sort chronologically; some pairs happen to agree. | Self-test 4's explicit arithmetic; F43; F85 |
| 221 | contradicted | Ask whether LIMIT 3 adds a row: only two rows satisfy the dashboard filter. | `lab/query-results/run.out:22,30-32`; F28 |
| 221 | contradicted | Run unchanged baselines; reason about modifications separately because the harness asserts the original dashboard. | `lab/query-results/main.py:44`; original reader command paths |
| 233, 240 | contradicted | Say order 106 is excluded; no previously returned order leaves the answer. | F25; F28; derived candidate order 101, 105, 106 |
| 234, 241 | contradicted | Specify preserved storage classes and correct DISTINCT: text '1299' and integer 1299 remain separate. | New F92–F94; F97; F8; F59 |
| 245 | misleading simplification | Distinguish NULL-valued arithmetic from unknown predicates and their rejection by WHERE. | F11; F13; F17; F58 |
| `facts.jsonl:46` | stretched fact | Narrow “an operation” to the four arithmetic operators addressed by the quoted rule. | F46 quote; SQLite expressions §2 |
| `facts.jsonl:48` | stretched fact | Exclude operators such as remainder from the blanket integer/real arithmetic summary. | F48 quote; SQLite datatype documentation §5 |
| `facts.jsonl:87` | stretched fact | Remove DECIMAL affinity assignment and arithmetic conclusions absent from this fact's own quote. | F87 quote; F60 separately establishes the affinity example |

## Coverage and evidence

Checked every printed paragraph, all first-use term definitions, the five-row input table, every AND/OR cell and NOT outcome, both misconception blocks, all SQL/output includes and surrounding deductions, every self-test question and answer, and the closing summary. Read both labs' SQL seeds, queries, Python runners, truth-table query, and complete captured `run.out` files. No diagram was present; its omission is permitted.

The complete truth tables agree with F17 and all nine captured SQLite input pairs. WHERE retains only true; comparison with NULL, NOT UNKNOWN, and IS NULL/IS NOT NULL match the recorded outputs and cited quotes. Ordinary SELECT multiplicity, full selected-row DISTINCT comparison, NULL duplicate comparison, absent physical-order guarantees, tie-breaking, LIMIT, and opposite engine-default NULL placement were checked. The original three-valued-logic derivations and remaining row deductions are correct.

Checked integer/REAL division, displayed real approximation, DECIMAL affinity, permissive integer casts, signed integer range, SQLite overflow promotion, and documented PostgreSQL bigint overflow and exact numeric precision/scale behavior. The two-decimal cents interpretation remains an application contract, not a universal currency rule. Checked raw versus normalized timestamp ordering, the restricted fixed-format UTC convention, offset subtraction, and PostgreSQL input/storage/session-display distinctions. The captured runtime is SQLite 3.54.0; SQLite documentation metadata is 3.54.1 and PostgreSQL documentation metadata is 18.6. PostgreSQL source evidence for integer parsing additionally identifies its own REL_18_0 provenance; no PostgreSQL output is claimed.

Added six narrow facts, F92–F97, after reading cached primary SQLite documents through `tools/fetch.py`; narrowed F46, F48, and F87 with `tools/state.py fact`. No source registry, generated output, glossary, roadmap, learner profile, or state was hand-edited. All includes and term markers were preserved. No tests, lab reruns, builds, formatters, or lint were run. A count-only prose-delta calculation was performed for budget awareness, not a final lint gate.

Remaining `[@unverified]` claims: **none**.

Elapsed checker time: **372 seconds** from the recorded start through report preparation.

## Human flags / limitations

- The final writer gate must count prose: the draft began at 4497; an intermediate estimate was 4533 before the corrected try-it was shortened to offset additions. No final authoritative word count was run.
- PostgreSQL contrasts remain documentation/source-backed only; no PostgreSQL runtime was exercised.
- SQLite documentation and actual runtime versions differ as explicitly stated; the captured outputs, not newer documentation alone, ground lab observations.
