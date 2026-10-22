# Chapter 2 summary

The reader can interpret single-table SELECT expressions and aliases row by row without confusing explanatory order with physical execution. Results preserve duplicates unless DISTINCT removes them by selected-value comparison. NULLs compare alike for duplicate removal, but text and integer values need not collapse.

NULL marks missing information. Comparisons can yield unknown, WHERE retains only true, and NOT preserves unknown. The reader has derived AND/OR truth tables and can use IS NULL/IS NOT NULL deliberately. ORDER BY needs sufficient tie-breakers, connected to chapter 1’s primary key. LIMIT caps results but supplies no ordering. Uncertain sequence is distinct from membership when all qualifying rows fit.

Amounts require a representation contract. Integer cents are exact only within bounds and a chosen scale. SQLite REAL is approximate; DECIMAL affinity does not enforce PostgreSQL numeric precision/scale. Integer division, overflow, and casts have explicit, sometimes different engine behavior. Storage classes and collation affect comparisons rather than visual appearance.

Clock readings differ from instants. UTC offsets are subtracted before comparing mixed-offset timestamps. Fixed-format, same-zone text permits restricted chronological ordering; PostgreSQL timestamp and timestamptz differ in interpretation, storage, and session-zone display.

The SQLite 3.54.0 labs support these observations; PostgreSQL contrasts were documentation-checked, not executed. Chapter 3 will build joins, multiplicity, and unmatched-row NULLs on these mechanisms.
