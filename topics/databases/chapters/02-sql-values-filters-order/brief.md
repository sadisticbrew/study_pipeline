# Chapter 2 brief: SQL values, filters, and ordered results

Topic: `databases`. Chapter directory: `topics/databases/chapters/02-sql-values-filters-order`.
Prose budget: **2500–4500 words**, excluding code and answers. Aim for about 3900–4200 words, leaving room for checker repairs. No budget increase is needed.

This is an approved regeneration of a completed chapter. Replace the previous draft rather than treating it as authoritative research. Existing sources and cached primary documents can be reused after actually reading them. The existing glossary contains only entries attributed to chapter 2, not evidence that the learner knew these mechanisms before this chapter.

## 1. Starting point

Chapter 1 is marked `known`. Its core ideas establish tables, rows, columns, basic value types, stable identifiers, primary and foreign keys, simple constraints, and an initial SQLite CREATE TABLE / INSERT / SELECT trace. It also establishes the distinction between a database, its engine, the SQL language, and a client. There are no earlier `done` chapters and therefore no earlier chapter summaries to read. Chapter 3 is pending and will teach joins, matched and unmatched rows, multiplicity, EXISTS, and the NOT IN / NULL trap. Do not teach those topics here.

The profile establishes ordinary programming in Go, Python, and C, arithmetic and comparisons, set notation, equivalence relations, big-O, and two's-complement arithmetic. It does **not** establish Boolean SQL conditions, three-valued logic, IEEE 754, numeric precision, collation, time conventions, or database implementation machinery. Even though chapter 2's prerequisites name them as things to teach, none are assumed. Do not invoke mathematical logic notation, query plans, indexes, graph terminology, or a binary floating-point derivation without teaching the needed mechanism. Decimal fractions and ordinary arithmetic are enough for the representation discussion.

Connect explicitly to chapter 1's stable primary key when breaking sort ties, and to its stored rows and value types when distinguishing stored facts from computed answers. Contrast SQL's duplicate-preserving answers with the mathematical sets the learner does know, but only after tracing actual repeated answer rows. Do not use formal relational algebra.

`topics/databases/pitfalls.md` is currently empty. `topics/databases/library/` currently has no book copies. Use readable official web documents rather than depending on S8 or other unavailable books.

Regeneration and glossary handling: all 22 existing glossary entries have `chapter: 2`. They are not prior knowledge. The writer must teach their mechanisms in this chapter, and preserve/reuse the appropriate first-use chapter-2 term markings rather than silently treating them as earlier material. Do not duplicate glossary keys or redefine genuinely earlier-topic terms. Section 6 below separately lists only terms absent from the existing glossary, as requested.

## 2. Crux

**How do you make a SQL query mean exactly which rows, which values, and which first results you intend?**

Keep this question in one crux block. The answer must connect filtering, missing information, ordering, and value representation rather than becoming a reference catalogue.

## 3. Opening situation

A small order-service dashboard is supposed to show the two largest pending orders whose discount is known to be zero. The database contains both an explicit zero discount and a discount not yet recorded. Several orders have the same total, and the dashboard computes a payable amount from stored columns. A quick query looks plausible, but the team has not made precise what a missing discount means, which tied rows should appear first, or what the amount and timestamp fields actually represent.

Use the concrete five-row data below, with no assumed SQL semantics. Let the reader first inspect the stored information and the product requirement. Do not show an invented execution result. Any output or executable SQL shown in the chapter must come from the fresh lab. Claims about missing values, expression results, ordering, and representation are covered by Q1–Q24 or derived explicitly from the chosen numbers.

## 4. Sections and budgets

The minimums below sum to **2500** and the maximums to **4500**. Answers and included code/output do not count. Target the middle-to-upper part of the ranges so the foundations are not compressed. Explanations remain flowing OSTEP-style prose. Tables are appropriate for concrete rows and truth tables; do not turn the prose into lists of rules.

### Opening and crux — 150–250 words

- Point: a query that runs is not yet a precise statement of the dashboard's requirements.
- Foundations: order rows and elementary SELECT from known chapter 1; no new mechanism is presumed.
- Sources: introductory situation is invented data, not a historical or performance claim. Its SQL consequences must be grounded in the batches below.

### A. A query computes answer rows — 400–700 words

- Point: read a simple single-table query as a meaning-preserving row-by-row computation. First substitute one order's values into `total_cents - discount_cents`, then name the output with `AS`. Explain single-quoted strings at first use. Teach the conceptual filtering/computation steps without presenting them as an engine's physical execution algorithm.
- Foundations: stored columns, arithmetic, and a basic SELECT from chapter 1 and the profile. Teach a select-list expression and an output alias here, starting with order 101. Trace how selecting only the buyer yields two Ada answer rows even though their order IDs differ, then explain what DISTINCT compares. Do not use DISTINCT as a repair for an unexplained query bug.
- Sources: S34–S38, S3, S37; questions Q1–Q6.
- Use integer division only as a short bridge to the numeric section. If shown, obtain both the SQL and output from the lab.
- Diagram: none. The small result table and actual row substitutions carry this section.

### B. A missing discount changes the answer to a question — 550–950 words

- Point: establish what information is absent before introducing NULL and SQL's third condition outcome. The requirement is a **known zero** discount, not a policy that silently substitutes zero for missing information.
- Foundations: programming comparisons from the profile and row-by-row computation from A. Teach true/false as answers to a concrete test, then the undecidable case, before naming three-valued logic. Trace `discount_cents = 0` for orders 101, 102, and 103 by hand, followed by which rows WHERE retains.
- Build AND from requiring both conditions and OR from accepting either condition, then show the complete AND/OR truth tables and the three NOT outcomes. Explicitly derive `false AND unknown` and `true OR unknown`; do not assume a previously learned logic course. Show IS NULL / IS NOT NULL after demonstrating why comparison to NULL does not ask the right question.
- Distinguish SQL condition semantics from Python truthiness. Do not promise left-to-right or short-circuit execution and do not use Boolean order to guard an error-producing expression.
- Sources: S41–S44, S34, S35; questions Q5 and Q7–Q12.
- Diagram: none. The row trace and truth tables are the right representation.

### C. Which two orders are first? — 400–700 words

- Point: ORDER BY states the ordering, later sort keys resolve ties, and LIMIT alone does not specify a meaningful first pair. Tie the final key to chapter 1's unique order ID. Scope repeatability to the same data, ordering expressions, and comparison rules, not a promise across concurrent changes.
- Foundations: the stable primary key from chapter 1; candidate rows and conditions from A/B. Starting from the actual pending orders, trace a tied total and how the order ID resolves it. State SQLite and PostgreSQL default NULL placement explicitly if discussing it, and introduce explicit NULLS FIRST / NULLS LAST rather than silently generalizing one engine's default.
- Sources: S34, S37, S46; questions Q13–Q16.
- Diagram plan: one small **conceptual result-flow** figure for the final dashboard query, if it earns its place. Use Graphviz's existing `.dot` support. Nodes describe the running example's input rows, WHERE's known-zero pending rows, the computed payable columns, the explicit total/ID order, and LIMIT's first two results. Edges mean stages in explaining the result, **not** engine execution or a query plan. Introduce that meaning before the figure and explain the surviving IDs and tie-break afterward. The nearby prose must fully teach the conditions, computation, and ordering and cite them; no factual claims may exist only in labels. No graph-theory vocabulary is needed. If the flow would only duplicate an equally clear table, omit it and explain the query in prose instead. No diagram quota.

### D. A number needs a representation contract — 500–900 words

- Point: choose a representation by what an amount means, not by the spelling of a column declaration. Teach the distinction between exact integer counts, decimal-scale amounts, and approximate real values before choosing among them.
- Foundations: ordinary arithmetic and two's complement from the profile, stored value types from chapter 1, expression substitution from A. Teach finite representability using a familiar finite-digit example, then explain that a fixed binary representation cannot exactly encode every decimal fraction. No IEEE 754 bit fields or exponent arithmetic are required. Walk through why 1299 cents means 12.99 units only under a declared two-decimal-place contract; do not claim that integer cents solve all currency or rounding requirements.
- Show SQLite's actual inexact real-number example and integer division, contrasting the documented PostgreSQL exact `numeric(p,s)` contract with SQLite's DECIMAL/NUMERIC affinity. Explain precision and scale with a small derived example and acknowledge declared-scale rounding and out-of-range behavior. Pin integer range/overflow claims to each engine rather than calling all integer arithmetic exact without bounds.
- A short explicit conversion example should show that a cast is a conversion policy, not validation. Trace SQLite's `CAST('12x' AS INTEGER)` and contrast the documented PostgreSQL rejection. Do not imply that SQLite's permissive conversion is universal.
- Sources: S33, S35, S39–S40, S49–S52; questions Q6 and Q19–Q24.
- Diagram: none. A few chosen numeric substitutions and observed output suffice. Avoid a catalogue of all engine types.

### E. Text and timestamps also have comparison rules — 400–750 words

- Point: values that look right to a person are not necessarily stored or ordered under the intended comparison rule. Teach a text-comparison rule with one simple example before naming collation. Connect this to sorting time strings.
- Foundations: strings from programming, stored value types from chapter 1, ORDER BY from C. Teach an instant versus a local clock reading, UTC as a common reference, and a numeric UTC offset using one subtraction by hand before discussing timestamp types.
- Keep the order-service timestamp example small. Compare two spellings of the same instant with different offsets, normalize them in the SQLite lab, and explain why the raw strings are not a general chronological order. State the conditions for a normalized fixed-format UTC text convention to sort chronologically, rather than generalizing to arbitrary ISO-like text. Do not require calendar algorithms, daylight-saving rules, or a tour of every time function.
- Clearly separate SQLite's supported time representations and conversion functions from PostgreSQL's documented timestamp-without-time-zone and timestamp-with-time-zone behavior. The latter represents an instant and formats it under the session zone; it does not retain the original named zone/offset. Do not present PostgreSQL output as observed unless actually run.
- Sources: S33, S45–S48; questions Q16–Q18.
- Diagram: none. A single offset calculation and a compact observed normalization example are enough.

### Check yourself and closing connection — 100–250 words

- Include a try-it task using an existing lab and a self-test block with matching answers. At least one question must require predicting a new row or a changed condition, rather than recalling a definition. Suggested probes: a missing discount under NOT; a third tied order under LIMIT; an amount stored as text; timestamps with unequal offsets. Answers must explain mechanisms and cite any new technical rule.
- Close by connecting to chapter 3: before combining rows from different tables, the learner can now reason precisely about which answer rows survive, whether duplicates remain, and what NULL means. Do not pre-teach joins.

## 5. Running example

Use one tiny order service throughout. The following are chosen fictional input data, not claimed program output. `discount_cents` NULL means the discount has not yet been recorded. All cent amounts are within ordinary safe small-integer bounds. `created_at` uses a deliberately stated, fixed-format UTC text convention in this teaching schema; do not claim the declaration itself enforces that convention.

| order_id | buyer | total_cents | discount_cents | status | created_at |
|---|---|---:|---:|---|---|
| 101 | Ada | 1299 | 0 | pending | 2026-10-19T09:00:00Z |
| 102 | Bea | 1299 | NULL | pending | 2026-10-19T09:05:00Z |
| 103 | Ada | 2500 | 250 | shipped | 2026-10-19T10:00:00Z |
| 104 | Cy | 800 | NULL | pending | 2026-10-19T11:00:00Z |
| 105 | Dee | 1299 | 0 | pending | 2026-10-19T12:00:00Z |

Proposed final dashboard query: select the order ID, buyer, and `total_cents - discount_cents AS payable_cents`; keep `status = 'pending' AND discount_cents = 0`; sort by `total_cents DESC, order_id ASC`; return at most two. The lab supplies the runnable query and observed result. Other small expressions and timestamp variants are questions about these same order-service values, not unrelated applications.

## 6. New terms

Do not list or invent new glossary entries for terms already present. The existing glossary already holds NULL, select-list expression, alias, DISTINCT, duplicate, unknown, predicate, truth table, sort key, tie-breaker, LIMIT, collation, storage class, floating point, type affinity, precision, scale, cast, instant, UTC, UTC offset, and timestamp, all attributed to this chapter. Their mechanisms still need first-principles teaching during this regeneration, with the existing chapter's term keys reused as appropriate.

Terms absent from the existing glossary that may merit a first-use marking if actually used: **Boolean condition** and **integer division**. Avoid adding `projection`, `bag semantics`, `total order`, `IEEE 754`, or time-zone acronyms merely to name things that plain prose can explain. Spell out an unfamiliar acronym if it is necessary. Do not introduce a term just because this list offers it.

## 7. Misconceptions — at most two

1. “A missing discount is just zero, so negating the comparison will recover the other orders.” Diagnose using the same recorded/absent values and the WHERE, NOT, and IS NULL rules; grounded by Q7–Q12.
2. “LIMIT gives me the same first two rows, and sorting by amount settles it.” Diagnose using a tied amount and the explicit unique ID tie-break; grounded by Q13–Q15. Do not claim that one demonstration proves unordered results must change on every run.

Do not add extra misconception boxes for numeric or time examples. Explain those pitfalls in ordinary prose.

## 8. Fact questions — four batches of six

Scouts work in **facts mode**, write the exact output file named below, and extract narrow claims with verbatim quotations of at most about 60 words. Read the source before citing it. Budget: **at most 8 searches and about five minutes per scout**. Prefer known official URLs and cached documents through `tools/fetch.py`; no book downloads are needed. Sources path: `topics/databases/sources.jsonl`. Existing source metadata is not itself proof of a version or of a quotation. Pin the actual documents read. Old scout files must be replaced, not appended to. Report each unanswered question, any access limitation, any unavailable book that would actually resolve a question, and elapsed time.

### Batch 1: Answer rows and SQL expressions

Output: `work/scout-1.jsonl` relative to the chapter directory.
Suggested sources: S34 SQLite SELECT, S35 SQLite expressions, S36 SQLite grammar if needed for AS, S37 PostgreSQL SELECT, S38 PostgreSQL lexical structure, S51 PostgreSQL math operators. Prefer readable doc sections over source code where possible.

- **Q1.** For an ordinary single-table SELECT without grouping, how do result expressions compute output values, and what does an `AS` output-column alias name? Ground the particular subtraction/alias notation used by the running query.
- **Q2.** How do SQLite and PostgreSQL spell SQL string constants, and how is a single quote inside one escaped? Distinguish string constants from identifier names without relying on compatibility exceptions.
- **Q3.** Do ordinary SELECT results preserve duplicate answer rows in each engine, and what explicit operation removes them?
- **Q4.** Does DISTINCT compare the complete selected output row rather than the underlying primary key, and how does it treat NULL values for duplicate removal? Do not generalize this special comparison to ordinary `=`.
- **Q5.** What documented single-table SELECT steps explain FROM, WHERE, result expressions, and DISTINCT, and what explicitly prevents presenting this explanation as the engine's fixed physical evaluation order? Include the caveat against assuming SQL Boolean operands execute left-to-right if asserting it.
- **Q6.** What do SQLite and PostgreSQL return for integral division such as `5 / 2`, how does a real/numeric operand change the interpretation, and in which direction is integral division truncated? Distinguish SQLite REAL from PostgreSQL exact numeric rather than giving one cross-engine claim.

### Batch 2: Conditions and missing information

Output: `work/scout-2.jsonl`.
Suggested sources: S41 PostgreSQL comparison functions, S42 logical operators, S43 expression evaluation, S34 SQLite SELECT, S35 SQLite expressions, S44 SQLite NULL handling. Use current primary references, not the historical comparison chart alone.

- **Q7.** What does NULL stand for in the intended SQL value model, and what are the results of ordinary arithmetic and ordinary comparisons when an operand is NULL, including `NULL = NULL`? Do not imply NULL is zero or an empty string.
- **Q8.** Which of true, false, and unknown causes WHERE to retain a row in PostgreSQL, and how does SQLite document its corresponding WHERE filtering behavior? State the engine's representation separately from the conceptual truth outcomes.
- **Q9.** What is the complete three-valued truth table for AND, including `false AND unknown` and `true AND unknown`, and which primary SQLite reference supports the matching NULL behavior used in the lab?
- **Q10.** What is the complete three-valued truth table for OR, including `true OR unknown` and `false OR unknown`, with the same engine distinction?
- **Q11.** What does NOT return for true, false, and unknown, and why does applying NOT to an ordinary comparison against NULL not turn it into a true condition?
- **Q12.** How do `IS NULL` and `IS NOT NULL` differ from ordinary equality/inequality against NULL, and which definite outcomes do the special tests return?

### Batch 3: Ordering, text, and time

Output: `work/scout-3.jsonl`.
Suggested sources: S34 SQLite SELECT, S37 PostgreSQL SELECT, S46 PostgreSQL collation, S33 SQLite types, S35 SQLite expressions, S45 PostgreSQL datetime, S47 SQLite date functions, S48 RFC 3339. Direct readable subsections of these references suffice.

- **Q13.** What guarantees exist about result order without ORDER BY, and what does LIMIT do or fail to determine when no sufficiently specified ordering exists? Do not claim unstable output must visibly change in a particular run.
- **Q14.** How do multiple ORDER BY expressions and ASC/DESC resolve ties, and what remains unspecified when every ordering expression compares equal? Ground why a unique order ID finishes ordering the fixed input example.
- **Q15.** What are SQLite's and PostgreSQL's default NULL positions for ascending and descending ordering, and do both support explicit NULLS FIRST / NULLS LAST? Keep the opposite engine defaults distinct.
- **Q16.** What comparison rule does SQLite's default BINARY text collation use, how does PostgreSQL choose a collation, and why must one not infer numeric order or a universal human alphabetic order from a TEXT declaration? Ground the simple digit-string example if used.
- **Q17.** What date/time storage representations and offset conversions do SQLite's docs actually support? Using RFC 3339 for `Z` and offset meaning if needed, under what explicitly restricted common UTC text format is ordinary string comparison chronological, and why do arbitrary mixed-offset strings not have that property? A normalization-order conclusion may be derived from the lab instead of overclaiming a quoted source.
- **Q18.** In PostgreSQL, what is the difference between timestamp without time zone and timestamp with time zone for interpreting input, storing an instant, displaying under a session zone, and retaining the original input zone? Use UTC/offset definitions from RFC 3339 if needed; do not turn a UTC offset into a complete named time-zone rule set.

### Batch 4: Numeric meaning and conversion

Output: `work/scout-4.jsonl`.
Suggested sources: S49 SQLite floating point, S50 PostgreSQL numeric types, S33 SQLite types, S35 SQLite expressions, S39–S40 PostgreSQL integer text parsing if documentation does not directly settle invalid input, S52 PostgreSQL bigint arithmetic. Read narrowly; no whole-source-tree research.

- **Q19.** What precision/exactness do SQLite INTEGER and REAL provide, what primary evidence explains binary real approximation for decimal fractions, and what can be claimed about a forced-real `0.1 + 0.2` comparison without implying that PostgreSQL's default decimal literals use binary floating point?
- **Q20.** What do PostgreSQL `numeric(p,s)` precision and scale mean for ordinary positive scale, and how are excess fractional digits and excess integer digits handled? Ground a simple amount example and distinguish exact decimal arithmetic from a promise of infinite capacity or no rounding.
- **Q21.** What affinity does a SQLite DECIMAL declaration get, what actual storage classes can values then acquire in an ordinary non-STRICT table, and why does this not provide PostgreSQL-style exact fixed-scale decimal arithmetic?
- **Q22.** What source-backed exactness/representation facts justify integer minor units for small two-decimal-place order amounts, and what remains an explicit application contract about the scale, permitted fractions, and rounding? Derive the chosen 1299-to-12.99 interpretation instead of claiming integer cents solve every money problem.
- **Q23.** What is the signed integer range in SQLite and PostgreSQL bigint, and what do the engines do on integer arithmetic overflow? In particular, distinguish SQLite promotion to floating point from PostgreSQL bigint's out-of-range error.
- **Q24.** What are SQLite's exact TEXT-to-INTEGER CAST rules for `'12x'`, and what authoritative PostgreSQL rule or implementation makes the analogous integer input fail? Ground the strictness contrast narrowly, without implying all conversions in either engine behave identically.

## 9. Lab plan

Topic lab profile: runner **local**, bubblewrap sandbox, no host root, no network needed. Use Python's standard-library `sqlite3`; record the actual SQLite runtime version. PostgreSQL tools were unavailable at topic creation: do not install packages or change services, do not assume they have since appeared, and do not fabricate PostgreSQL output. Documented PostgreSQL contrasts are sufficient here. All runnable code and displayed output come from lab files and fresh `tools/lab.py run` results.

Regeneration: reuse the existing lab directory names below, updating their real implementation to the running example and removing only obsolete files within those labs if necessary. Do not leave unused old labs or scripts to be accidentally checked. Inspect before changing. Do not hand-write generated `run.out` / `run.status.json`. Each lab should have no network, a short timeout, and deterministic values. Run it through the lab tool after all its inputs are final. Do not run repository-wide tests, formatters, or builds mid-flight.

### Lab `query-results`

- Demonstrates: selected expressions and aliases, duplicate-preserving answers versus DISTINCT, missing discount comparisons, IS NULL, the complete condition outcomes, ordered ties and an explicit unique tie-break, LIMIT, NULL placement, and the final dashboard query.
- Runner: `local`; expected result: `success`.
- Input: the five chosen order rows. Keep the small schema and insert data available on disk, with SQL examples in separately includable, readable slices. A Python runner may load the SQL and label observed outputs. Prefer short SQL files to filling the chapter with Python harness code.
- Visible output: actual SQLite version; raw discount versus `discount_cents = 0` results and row inclusion; a repeated buyer result versus DISTINCT; labels or a compact table for all AND/OR/NOT outcomes; tied totals and the final unique order; the final dashboard's actual order IDs and payable amounts. No claim that unordered output must visibly change. Print NULL explicitly, not ambiguously as an empty field.
- Provide runnable reader commands, exact input/output line ranges, and notes about what each excerpt supports. Keep individual included code slices at most 25 lines, outputs at most 20, and total proposed included code across both labs at most about 90 lines. It is fine to leave most of the harness on disk.

### Lab `values-and-time`

- Demonstrates: exact small integer cents, integer versus real division, a REAL rounding/equality case, the actual storage of a value inserted into an ordinary DECIMAL column, a permissive SQLite integer cast, text versus numeric ordering, and normalization of timestamp strings with different UTC offsets.
- Runner: `local`; expected result: `success`.
- Visible output: clearly labelled values and `typeof` where relevant; integer division and a real-operand counterpart; a real equality comparison without Python rounding concealing the difference; a DECIMAL-affinity observation rather than a fake fixed-scale guarantee; `CAST('12x' AS INTEGER)`; a tiny order-amount string sort; two offset spellings of the same instant normalized by SQLite, plus an optional mixed-offset chronology counterexample if it materially teaches the point. Include a near-bound integer overflow observation if it is compact and deterministic, otherwise leave that contrast documented only.
- Keep any PostgreSQL statements out of captured-output sections unless really executed against an available version. The chapter can cite docs for PostgreSQL without a PostgreSQL lab.
- As above, return exact line ranges, what each output actually proves, any limitations, and elapsed time. No machine-state diagrams or generated x86 figures are applicable.
