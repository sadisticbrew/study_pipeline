---
topic: databases
chapter: 2
title: SQL values, filters, and ordered results
---

A small order service needs a dashboard that shows the two largest pending orders whose discount is known to be zero. The stored data looks innocent. Two orders record a zero discount, two leave the discount unrecorded, three share the same total, and the payable amount has to be computed from stored columns. A quick query that filters on pending status and zero discount, subtracts discount from total, sorts by total, and keeps two rows will run without complaint. Running is not the same as meaning what the team intends, because that quick query never says what a missing discount should do, which tied total comes first, or what the amount and creation-time fields actually promise.

The five stored orders below are the running example for the whole chapter. Read them as given facts, not as query output. The discount column holds either a counted number of cents or a marker that no discount has been recorded yet. A [NULL]{.term def="A marker that a value is missing rather than zero or empty."} here means not yet recorded, not zero. The creation-time strings all share one fixed shape ending in `Z`, and that shared shape is a convention this teaching schema follows rather than a rule the column declaration enforces.

| order_id | buyer | total_cents | discount_cents | status | created_at |
|---|---|---:|---:|---|---|
| 101 | Ada | 1299 | 0 | pending | 2026-10-19T09:00:00Z |
| 102 | Bea | 1299 | NULL | pending | 2026-10-19T09:05:00Z |
| 103 | Ada | 2500 | 250 | shipped | 2026-10-19T10:00:00Z |
| 104 | Cy | 800 | NULL | pending | 2026-10-19T11:00:00Z |
| 105 | Dee | 1299 | 0 | pending | 2026-10-19T12:00:00Z |

::: crux
How do you make a SQL query mean exactly which rows, which values, and which first results you intend?
:::
## A query builds new answers from stored rows

The dashboard starts from stored facts and must produce new answers. Chapter 1 gave you tables with stable identifiers and typed columns: this chapter asks what a query means when it keeps some rows and computes fresh values from them. Think of that meaning as a row-by-row recipe you could follow by hand, not as the order an engine touches data inside. SQLite describes the logic as filtering the input with `WHERE` and then evaluating the result expressions over the survivors [@F1; @F70], and warns the outline is only illustrative because no engine must follow any particular process [@F2].

Five order rows are the stored input. The lab creates one small table holding exactly the opening orders, with the creation-time convention recorded as a comment rather than a constraint the declaration enforces:

```{.sql include="lab/query-results/seed.sql" lines="1-15"}
```

```{.output include="lab/query-results/run.out" lines="1-7"}
```

The first line names the runtime behind every captured result, Python SQLite 3.54.0. The cited SQLite documents are version 3.54.1 and the PostgreSQL ones 18.6, so docs and run are close but not the same artifact.

Start with order 101, where every number you need is present. Its total is 1299 cents and its recorded discount is 0, so the payable amount is `1299 - 0`, which is 1299. A [select-list expression]{.term def="An expression in the SELECT list that computes an output value."} writes that subtraction in the `SELECT` list so it is computed from each kept input row [@F63]. The `AS payable_cents` part names the computed column, an [alias]{.term def="A name given to a computed output column."}. PostgreSQL names an output column with `AS` plus the name after the expression [@F64], and SQLite accepts that form as well as a bare name [@F6]. For a filter on a spelled-out word, single quotes matter. Both engines write a string constant in single quotes and encode an embedded quote by doubling it [@F65; @F5].

```{.sql include="lab/query-results/queries.sql" lines="4-7"}
```

```{.output include="lab/query-results/run.out" lines="8-15"}
```

Read the payable column row by row. Order 101 gives 1299, order 103 gives 2250, order 105 gives 1299, and orders 102 and 104 give NULL because their discount was never recorded, a result the next section explains. Each answer row comes from one stored row, and the stored `order_id` still tells answers apart when computed values match.

The buyer column sharpens the point. Selecting only `buyer` returns five answers, one per stored row, with Ada appearing twice, from orders 101 and 103. By default a `SELECT` returns all candidate answers including repeats. PostgreSQL states that `SELECT ALL`, the default, returns every candidate row including repeats [@F3; @F67], and SQLite behaves as if `ALL` were written when neither keyword appears [@F68]. You know sets from mathematics, where repeats collapse by definition. SQL answers keep repeats unless explicitly asked to drop them.

Asking uses [DISTINCT]{.term def="A keyword that removes duplicate answer rows before returning them."}. The second buyer query keeps one copy of each name, so five answers become four. A [duplicate]{.term def="An answer row equal to another under the query's duplicate-comparison rules."} here means two answers with equal selected values, not two copies of one stored row. The two Ada answers match on the only selected column while their hidden identifiers differ, so one survives. That comparison looks only at selected columns. PostgreSQL treats two result rows as the same when they match on every selected value and counts missing values as equal for that comparison [@F69], while SQLite detects repeats with a sameness test under which two NULLs count as equal [@F4]. Sameness can bridge representations, since an integer and a real value naming the same quantity count as equal and text follows the applicable rule [@F59].
## A missing discount is not a zero discount

The dashboard wants orders whose discount is known to be zero. Two pending orders record 0 and two record nothing at all. A missing discount could mean nobody entered it yet or the decision has not been made. Either way there is no number to subtract or compare. The requirement asks for a recorded zero, not a policy that quietly turns every blank into zero. Before naming any keyword, settle the question asked of each row. Is this discount known to be zero, or is that fact simply absent.

Trace `discount_cents = 0` row by row. Order 101 holds 0, so `0 = 0` answers yes. Order 103 holds 250, so `250 = 0` answers no. Order 102 holds no discount, so the question has no answer to give and guessing zero would invent information the row never stored. SQL keeps a third outcome for this case. Call the first two answers true and false, and the third [unknown]{.term def="The truth value of a test whose answer cannot be decided because an input is missing."}. NULL names the missing value itself. Unknown is what a test returns when a missing input leaves it undecidable. Ordinary comparisons with a missing input signify unknown rather than true or false [@F11; @F79], which is why PostgreSQL warns against writing `expression = NULL`, since two missing values are not known to be equal [@F15]. Arithmetic behaves the same way. A missing operand on an ordinary operation yields a missing result [@F58], and operators generally return NULL when any operand is missing, with only the stated exceptions [@F73]. That is why orders 102 and 104 showed NULL payable amounts. `1299 - NULL` is not 1299.

The lab prints the comparison outcome for every order, labeling SQLite's own 1, 0, or NULL answers as true, false, and unknown for readability. SQLite has no separate true-or-false storage and keeps those answers as the integers 1 and 0 [@F75], converting numeric zero to false, any other number to true, and NULL to NULL when an answer is used as a truth value [@F14]:

```{.sql include="lab/query-results/queries.sql" lines="9-18"}
```

```{.output include="lab/query-results/run.out" lines="16-27"}
```

Read the middle columns first. Orders 101 and 105 compare a recorded 0 against 0 and answer true. Order 103 compares 250 against 0 and answers false. Orders 102 and 104 have nothing to compare, so both the equality and its negation answer unknown. The last two columns ask a different question, not a comparison against a number but whether the value is missing at all. Only rows 102 and 104 answer true to `IS NULL`. SQLite defines `IS` to work like equality except that two missing values count as the same [@F16], and an `IS` or `IS NOT` test always returns definite true or false, never unknown [@F80].

A [predicate]{.term def="A test in WHERE that keeps or discards each candidate row."} in `WHERE` keeps a row in exactly one case. SQLite keeps only rows whose test evaluates to true and discards false or NULL [@F13], where NULL is the same unknown outcome in value form. PostgreSQL likewise keeps only rows that satisfy the condition, with actual row values substituted [@F74]. So `WHERE discount_cents = 0` keeps 101 and 105, `WHERE discount_cents IS NULL` keeps 102 and 104, and `WHERE NOT (discount_cents = 0)` keeps only 103. That last list surprises the habit carried over from ordinary programming, where negating a test recovers everything it rejected. Here the unknown rows are rejected twice, once by the test and once by its negation, because negation of unknown is still unknown.

::: {.misconception title="A missing discount is just zero, so NOT will bring back every other row"}
It will not. On these orders `discount_cents = 0` keeps 101 and 105, while `NOT (discount_cents = 0)` keeps only 103. The missing-discount rows 102 and 104 appear in neither list, because their test was unknown and unknown negated stays unknown. Of the four filters in the output above, only `IS NULL` finds them. Treating a blank as zero would also corrupt the payable column, turning two unknown amounts into confident 1299 and 800 values the rows never earned.
:::

Real dashboard conditions combine two tests, and each combination needs a rule for every input pair. Call each question a [Boolean condition]{.term def="An expression that evaluates to true, false, or unknown for each row."} when stressing that it returns three possible answers rather than a stored number. Requiring both keeps a row only when each side earns it, and accepting either keeps a row when at least one side earns it. The full rules are the [truth table]{.term def="A table showing the result of AND, OR, or NOT for every input combination."} for each connective. Both tables match the PostgreSQL logical-operator tables [@F17] in every cell, and SQLite states the same two surprising cases in its own words [@F18; @F77].

| a | b | a AND b | a OR b |
|---|---|---|---|
| `TRUE` | `TRUE` | `TRUE` | `TRUE` |
| `TRUE` | `FALSE` | `FALSE` | `TRUE` |
| `TRUE` | `UNKNOWN` | `UNKNOWN` | `TRUE` |
| `FALSE` | `TRUE` | `FALSE` | `TRUE` |
| `FALSE` | `FALSE` | `FALSE` | `FALSE` |
| `FALSE` | `UNKNOWN` | `FALSE` | `UNKNOWN` |
| `UNKNOWN` | `TRUE` | `UNKNOWN` | `TRUE` |
| `UNKNOWN` | `FALSE` | `FALSE` | `UNKNOWN` |
| `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |

| a | NOT a |
|---|---|
| `TRUE` | `FALSE` |
| `FALSE` | `TRUE` |
| `UNKNOWN` | `UNKNOWN` |

Two cells deserve derivation rather than memorization. `FALSE AND UNKNOWN` is false because one side already decides it: no completion of the missing input could change the verdict. `TRUE OR UNKNOWN` is true for the mirror reason. By contrast `TRUE AND UNKNOWN` stays unknown, because the missing side could still swing the answer, and `FALSE OR UNKNOWN` stays unknown for the same reason.

The lab produces every one of those nine AND and OR pairs and all three negations by binding each of true, false, and NULL to both inputs of one small query:

```{.sql include="lab/query-results/logic.sql" lines="1-2"}
```

```{.output include="lab/query-results/run.out" lines="37-46"}
```

Try one compound test on the running orders. On order 102, `discount_cents = 0 OR status = 'pending'` gives unknown on the left and true on the right, and the table says `UNKNOWN OR TRUE` is true, so the row survives despite its missing discount. Order 104 survives the same way. On order 103, `discount_cents = 0 AND status = 'pending'` gives false twice, since 103 already shipped, so the row goes away even though its discount is fully known.

This three-valued combination is not the truthiness you know from Python. In Python `None` and `0` both take the false path and `not` flips that result to true. In SQL unknown takes neither path. `WHERE` discards it exactly as it discards false, and `NOT` leaves it unknown rather than flipping it to true. Parentheses decide how the connectives group, with SQLite placing NOT above AND and AND above OR, so `NOT a AND b` groups as `(NOT a) AND b` [@F19]. Write the parentheses anyway. Grouping is contractual, but running order is not: PostgreSQL leaves subexpression order undefined, need not run left to right, and might never evaluate parts whose result cannot change the outcome [@F20; @F71]. Never arrange conditions so that one side must run first to keep the other safe.
## Which two orders are first

The dashboard wants the two largest pending orders with a known zero discount. Pending status plus a recorded zero keeps orders 101 and 105, both totaling 1299. Sorting by total descending then cannot name a first row. A single ordering expression leaves every tied pair unordered: both rows fit this two-row request, but their sequence is not yet precise.

A [sort key]{.term def="An expression whose values decide the order of the answer rows."} is one expression in the `ORDER BY` list, each with an optional direction, ascending for smaller values first and descending for larger values first, ascending being the default [@F26]. A [tie-breaker]{.term def="A later sort key that orders rows the earlier keys left equal."} is a later key that matters only where earlier keys tied. SQLite sorts by the leftmost key first and breaks ties with each later key, leaving rows tied on every key in an undefined order [@F25]. PostgreSQL compares left to right and leaves fully tied rows in an implementation-dependent order [@F22].

Trace the dashboard tie by hand. Both surviving totals are 1299, so the first key ties and the second decides: order 101 carries the smaller identifier and comes first. The identifier earns that role from chapter 1 as the stable primary key that already tells stored rows apart, so adding it as the final key gives every fully tied pair a decisive comparison. [LIMIT]{.term def="A clause that caps the returned row count, here taking the first N ordered rows."} then keeps the first two answers [@F28]. Without `ORDER BY` there is no specified first pair to keep. SQLite leaves multi-row order undefined [@F21], PostgreSQL returns whatever order the system finds fastest [@F23], and repeated `LIMIT` runs without a determining order can return different subsets [@F24].

The lab separates the tie from the tie-break. Sorting the four pending orders by total alone leaves the three 1299 rows in one tied group, and the lab labels that observed sequence as one observation rather than a promise:

```{.sql include="lab/query-results/queries.sql" lines="20-30"}
```

```{.output include="lab/query-results/run.out" lines="28-32"}
```

The tied query returned 101, 102, and 105 at 1299 followed by 104 at 800, but nothing asked for that inner order. The next query adds `order_id ASC` with `LIMIT 2`, and the dashboard adds the known-zero condition on the same ordering, answering 101 for Ada with payable 1299 and 105 for Dee with payable 1299. The identifier order comes from the written second key, not from any habit of the engine.

For unchanged rows, one written ordering, and one comparison rule, that sequence repeats. That scope is narrow by design and promises nothing after concurrent writes. PostgreSQL gives the matching advice: use an `ORDER BY` that makes the order unique with `LIMIT`, or accept an unpredictable subset [@F81]. The unique final key is what makes the dashboard pair meaningful rather than lucky.

Missing values need their own ordering rule, because the engines disagree. SQLite treats NULL as smaller than every value, so missing values come first ascending and last descending, unless the query writes `ASC NULLS LAST` or `DESC NULLS FIRST` [@F27]. PostgreSQL treats nulls as larger by default, last under ascending and first under descending, with the same explicit overrides [@F29]. The lab pins the explicit form onto the discount column:

```{.sql include="lab/query-results/queries.sql" lines="32-39"}
```

```{.output include="lab/query-results/run.out" lines="33-36"}
```

With default ascending the two missing discounts come first, then 0, 0, and 250, and default descending flips that placement. The explicit `NULLS LAST` and `NULLS FIRST` variants put the placement where no reader guesses the engine. Whenever a sorted column can be missing, write the placement you mean.

::: {.misconception title="LIMIT gives me the same first two rows, and sorting by amount settles it"}
Sorting by amount alone settles nothing inside a tie, and one observed tie order proves no rule. Here three pending totals tie at 1299, and rows equal on every written key come back undefined on SQLite and implementation-dependent on PostgreSQL. Adding the unique `order_id` as a final key, with the known-zero filter, gives one repeatable pair for unchanged input, 101 then 105. That repeatability still assumes the same rows, the same keys, and the same comparison rules.
:::
## A number needs a representation contract

The dashboard subtracts cents and reports 1299. That answer is exact because the inputs were counted whole cents and the arithmetic never left integers. But 1299 cents means 12.99 currency units only because this application declares a two-decimal-place contract. The digits alone do not know about a decimal point, and everything exact here flows from our choice to count minor units. Before choosing any column spelling, decide which of three ideas you need: an exact integer count with no fractions, a decimal amount with a fixed fractional count, or an approximate real value good enough for measurement but not for money.

Start from something familiar. One third has no exact finite decimal writing, since 0.33 always needs one more digit, and rounding is the price of stopping. Binary [floating point]{.term def="A number format that stores an approximation with a fixed count of significant binary digits."} pays that price far more often. Most decimal numbers with digits after the point have no exact binary-64 equivalent, even below sixteen significant digits [@F51]. SQLite calls that mathematics rather than a product defect and warns against binary-64 wherever an exact answer is needed [@F52]. For money it sharpens the point: in a binary-64 column holding dollars and cents, only the endings .00, .25, .50, and .75 are exact [@F88].

The lab shows integer cents exact first, then the approximation. Subtracting a recorded discount from a total stays inside integers on every known-discount row, each reported as integer:

```{.sql include="lab/values-and-time/queries.sql" lines="1-8"}
```

```{.output include="lab/values-and-time/run.out" lines="2-9"}
```

Orders 101, 103, and 105 compute 1299, 2250, and 1299, each reported as integer. Then division splits on its operands. `1299 / 100` divides two integers and returns 12, while `1299 / 100.0` with one real operand returns 12.99. [Integer division]{.term def="Division of two integers that returns an integer quotient with the fractional part discarded."} truncates toward zero in SQLite, and PostgreSQL documents the same truncation for its integral types, with `5 / 2` giving 2 and `(-5) / 2` giving -2 [@F48; @F49; @F72]. PostgreSQL gives a decimal-point literal like `2.0` its own starting type, presuming exact numeric [@F50], so the literal steers the arithmetic before any column does. Integer division discards the fractional part rather than rounding it.

The same output shows the approximation the integer contract avoids. Adding the real values 0.1 and 0.2 prints as 0.30000000000000004 while 0.3 prints as 0.29999999999999999, and the equality test returns false. This is one observed pair forced into real arithmetic by its decimal-point spellings, not a theorem that every decimal sum fails. SQLite normally rounds binary-64 for display [@F53], which is why the lab prints enough digits to see past that rounding. PostgreSQL's unadorned decimal literals take a different path as exact numeric [@F50; @F54], so a SQLite real-number inequality says nothing about a PostgreSQL decimal sum.

The most misleading declaration in this chapter is a column spelled `DECIMAL(6,2)`. The lab declares exactly that and inserts three spellings, two numeric-looking and one with a trailing letter:

```{.sql include="lab/values-and-time/seed.sql" lines="17-18"}
```

```{.sql include="lab/values-and-time/queries.sql" lines="10-13"}
```

```{.output include="lab/values-and-time/run.out" lines="10-15"}
```

The string `'12.99'` comes back as real 12.99, `'25.00'` as integer 25, and `'12x'` untouched as text. SQLite ignores the declaration's numeric arguments [@F96]; no decimal type enforced two fractional digits. In these ordinary tables any column except an integer primary key may store any [storage class]{.term def="The actual format SQLite uses for one stored value."}, subject to its constraints [@F7], and declared `DECIMAL(10,5)` carries `NUMERIC` [type affinity]{.term def="SQLite's preferred storage class for values in a column."} [@F60; @F61], converting well-formed numeric text toward integer or real storage while still permitting every storage class [@F8; @F87]. The declaration nudges conversion but guarantees no decimal arithmetic. PostgreSQL proves the name alone means nothing: there `decimal` and `numeric` name one equivalent type [@F62], exact where possible [@F54], while the approximate real family is documented as inexact [@F57].

PostgreSQL's exact type counts two properties. [Precision]{.term def="The total count of significant digits in a numeric value."} counts significant digits on both sides of the point, and [scale]{.term def="The count of digits after the decimal point in a numeric value."} counts only fractional digits [@F55]. `numeric(6,2)` allows at most six significant digits with two after the point, so 1999.99 fits and 19999.99 does not. Excess fractional digits round to the declared scale, and if the whole part then exceeds precision minus scale, the write raises an error [@F56]. That behavior belongs to PostgreSQL's contract, not to the SQLite table the lab ran.

Integers have edges too. SQLite integers span the signed 64-bit range and are exact inside [@F45]. Addition, subtraction, multiplication, and division on integers stay integer absent overflow, but on overflow SQLite performs the same operation as floating point instead [@F46]. PostgreSQL's `bigint` addition refuses that silent change, checking for overflow and raising a `bigint out of range` error [@F47; @F89]. The lab shows SQLite's edge by adding one to the largest integer, which comes back as a real approximation rather than an error:

```{.sql include="lab/values-and-time/queries.sql" lines="14-17"}
```

```{.output include="lab/values-and-time/run.out" lines="16-17"}
```

Integer cents stay exact only while amounts and intermediate results fit the range, and the engines disagree at the boundary. Our 1299-cent values sit far inside it, which is part of why the contract works.

One small conversion shows the same engine-dependence in miniature. A [cast]{.term def="An explicit conversion of a value from one type to another."} states a conversion policy, not validation. SQLite converts text to integer by taking the longest leading stretch that reads as an integer and ignoring the rest [@F9; @F90], so `'12x'` becomes 12. PostgreSQL treats any trailing character beyond whitespace as invalid, so `'12x'` fails [@F91], with its 32-bit conversion raising an error on bad input or overflow [@F10]. The lab output above shows the SQLite half. The PostgreSQL half is documented, never run here, so never treat an accepted conversion on one engine as portable validation.

Now derive the contract the dashboard uses. Storing 1299 with the rule that the last two digits are fractional means 12 whole units and 99 hundredths, which is 12.99. That reading is ours. It holds for amounts with at most two fractional digits, values and intermediates inside the 64-bit range, and rounding decided before storage. Amounts needing three fractional digits, division that must round half-up, or totals that can overflow all need rules this contract never states.
## Text and clock readings follow comparison rules too

The dashboard sorts buyers and creation times that look right to a person. Looking right is not comparing right, because every text comparison follows a rule the query must choose or inherit. Under bytewise comparison, `100` sorts before `20`, since the first characters decide and `1` comes before `2` [@F30]. As numbers, 100 is larger than 20. That rule is a [collation]{.term def="The rule a database uses to compare and order text."}. The declaration `TEXT` alone never settles the order.

SQLite's default text comparison is bytewise. Its built-in `BINARY` collation compares string bytes directly [@F30], and columns default to it unless another collation is declared [@F95]. Without an explicit `COLLATE`, SQLite uses the sorted column's own sequence for a plain column, or `BINARY` for an expression that is neither a column nor explicitly collated [@F31]. PostgreSQL sorts character data by the collation applying to the column [@F32], defaulting to the locale chosen when the database was created [@F33; @F83]. The lab sorts the same three totals both ways, once as byte-compared text and once converted back to numbers:

```{.sql include="lab/values-and-time/queries.sql" lines="19-22"}
```

```{.output include="lab/values-and-time/run.out" lines="18-19"}
```

Bytewise, 1299 comes before 2500, which comes before 800, because `1` precedes `2` precedes `8` in the first position. Numerically, 800 is smallest and 2500 largest. Only the written comparison decides, so never infer numeric order or a universal human alphabetic order from a `TEXT` declaration.

Creation times add a second question. A [timestamp]{.term def="A date and time value that may describe a clock reading or an instant."} can mean two things, and the dashboard needs the second. The clock reading is the date plus the time of day on some local clock. The [instant]{.term def="One point on the shared global timeline."} is the single point on the shared timeline when the order was placed. Two clocks in different places can show different readings at the same instant, so comparing readings as bare strings compares spellings. Comparing instants needs every spelling translated onto one reference first.

That reference is [UTC]{.term def="The shared time reference all zones are measured against."}, and the translation uses the [UTC offset]{.term def="The amount added to UTC to get local time, or subtracted to get back."}. An offset of `+02:00` says the local clock runs two hours ahead, so UTC is found by subtracting two hours. `Z` is the special case of no offset. Request for Comments (RFC) 3339 defines `Z` as offset `00:00` [@F42] and defines offsets as local time minus UTC, so UTC is found by subtracting the offset, with `18:50:00-04:00` equal to `22:50:00Z` [@F43]. The dashboard pair works the same way: `11:00:00+02:00` minus two hours is `09:00:00` UTC, exactly what `09:00:00Z` names.

SQLite stores no dedicated time value. It keeps dates and times as text, real, or integer values with no reserved storage class [@F34; @F84], with its date and time functions accepting only the layouts they enumerate, from date-only through space-separated and `T`-separated forms [@F44], not the whole calendar standard [@F36]. Those functions work in UTC internally, treat a `Z` suffix as doing nothing, and subtract any nonzero hour-and-minute suffix to compute UTC [@F35], with a plain reading, the same value with `Z`, and the same instant with a `-04:00` offset documented as equivalent [@F37]. The lab repeats that demonstration on order 101's instant with two zone spellings and one earlier instant:

```{.sql include="lab/values-and-time/queries.sql" lines="24-32"}
```

```{.output include="lab/values-and-time/run.out" lines="20-26"}
```

The two spellings of the 09:00 instant normalize to the same UTC value, and equality on the normalized values returns true. The query compared normalization outputs, not the raw submitted strings. Raw text order wedges the earlier `09:30:00+02:00` instant between the two spellings of 09:00, while normalized order puts the earlier instant first. Mixed-offset strings need not sort chronologically as raw text, because local clock fields are compared without accounting for their offsets. The five stored creation times avoid the problem with one fixed-width UTC spelling at seconds precision throughout, so sorting that uniform text bytewise walks years, months, days, hours, minutes, and seconds in order:

```{.sql include="lab/values-and-time/queries.sql" lines="33-35"}
```

```{.output include="lab/values-and-time/run.out" lines="27-32"}
```

The orders come out 101 through 105 in creation order, with the `order_id` key breaking nothing since no two strings tie. That agreement rests on stated conditions. Components run least precise to most precise, every value uses the same zone spelling, here all `Z`, and every value carries the same fractional-second precision, here none. RFC 3339 states exactly that restricted condition for sorting date and time strings as strings [@F85]. Drop a leading zero, mix in a `+02:00` spelling, or sort under an unsuitable collation, and the agreement can break.

PostgreSQL draws storage lines SQLite never draws, and the contrast is documentation rather than lab output, since no PostgreSQL was run here. A value determined to be timestamp without time zone silently ignores any zone indication and keeps the fields as written [@F38]. A timestamp with time zone converts zoned input to UTC [@F39], stores it internally as UTC with the original zone forgotten [@F40], and converts back to the session zone for display [@F41]. Input without a stated zone is assumed to be in the session zone and converted the same way [@F86]. The same submitted string can therefore mean keep the fields or convert to an instant, and two sessions in different zones can display one stored instant differently. Store one convention, normalize before comparing, and never assume the submitted spelling travels with the stored value.
::: tryit
Before running the unchanged labs, predict these cases. In `query-results`, would dashboard `LIMIT 3` add another order under the same tie-break? Which rows survive `discount_cents = 0 OR status = 'pending'`, using the truth tables? In `values-and-time`, predict `typeof(total_cents - discount_cents)` on known-discount rows and whether the two zone spellings of 09:00 compare equal after normalization. Run these commands from the repository root for baseline output; trace changes by hand because the harness asserts the original dashboard answer.

```{.text .sketch}
python3 tools/lab.py run topics/databases/chapters/02-sql-values-filters-order --only query-results
python3 tools/lab.py run topics/databases/chapters/02-sql-values-filters-order --only values-and-time
```
:::

## Check yourself

::: selftest
1. Order 104 has a missing discount and pending status. Evaluate `NOT (discount_cents = 0 AND status = 'pending')` on that row step by step, naming the outcome of each side, the AND cell, and the NOT outcome. Then say whether `WHERE` keeps the row, and which single test would keep exactly the missing-discount orders.
2. A sixth order arrives as 106, Dee, 1299, 0, pending, with a later creation time. The dashboard keeps its two-row limit and its `total_cents DESC, order_id ASC` ordering. Predict the two dashboard rows and explain which order is excluded and why the remaining tie still needs the identifier key.
3. In a separate SQLite table, the shop stores a new total as the text `'1299'` in one row and the integer `1299` in another, then runs `SELECT DISTINCT total_cents`. The column is declared `BLOB`, which leaves input storage classes unchanged [@F94]. Using the duplicate-comparison rules from this chapter, predict whether the two answers collapse into one, and say what `typeof` reports for each stored value.
4. Two creation times arrive as `2026-10-19T12:00:00+02:00` and `2026-10-19T09:30:00Z`. Which names the earlier instant, and would sorting the two raw strings bytewise give the chronological order? Show the subtraction that decides and name the normalization the chapter uses before comparing mixed-offset spellings.
:::

::: answers
1. The left side compares NULL with 0, which is unknown, and the right side compares pending with pending, which is true. The AND table says `UNKNOWN AND TRUE` is unknown, and `NOT UNKNOWN` is unknown, so `WHERE` discards row 104 [@F17; @F13]. The missing-discount orders are found only by asking about missingness directly, with `discount_cents IS NULL`, which returns a definite true for exactly rows 102 and 104.
2. Three candidates now tie at 1299 with known zero discounts: 101, 105, and 106. The first key ties on all three, so the identifier tie-break orders them 101, 105, 106, and `LIMIT 2` keeps 101 and 105. Order 106 is excluded only because it carries the largest identifier among equals, and dropping the identifier key would leave the surviving pair undefined on SQLite and implementation-dependent on PostgreSQL [@F25; @F22].
3. They remain two answers, with `typeof` reporting text and integer respectively. `DISTINCT` does not coerce one storage class into another [@F92], and an integer and a text value compare unequal [@F93]. Integer and real values naming the same quantity can collapse [@F59], but that rule does not turn text into a number. In the original `INTEGER`-affinity column, numeric-looking text would instead convert on insertion, before duplicate removal [@F97; @F8]; accepting multiple storage classes does not mean preserving every input's class.
4. Subtract the offset from the local reading to get UTC [@F43; @F35]. `12:00:00` minus two hours is `10:00:00Z`, which is later than `09:30:00Z`, so the `09:30:00Z` order is earlier. Bytewise raw-text order compares `09:30...` against `12:00...` and happens to agree here, but mixed spellings carry no chronological promise because local clock fields are compared without accounting for their offsets. The chapter normalizes each spelling to UTC with SQLite's date and time functions before comparing or sorting [@F35], which is what made the two spellings of the 09:00 instant compare equal in the lab.
:::

Before combining rows from different tables, you can now say precisely which answer rows survive, whether repeats remain, and what a missing value does to each test. Filtering keeps only true. Repeats survive unless `DISTINCT` removes them by comparing selected values. NULL propagates through ordinary comparisons and arithmetic; a test yielding unknown and its negation are both discarded. Ordering needs a decisive final key before `LIMIT` names a first pair, numbers need a representation contract before digits become amounts, and clock readings need normalization before strings become instants. Chapter 3 will match rows across tables, where every one of those decisions meets multiplicity again.
