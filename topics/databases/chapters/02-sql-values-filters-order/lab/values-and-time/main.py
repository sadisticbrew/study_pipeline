from pathlib import Path
import sqlite3


def text(value):
    if value is None:
        return "NULL"
    # Preserve enough digits to expose the retrieved REAL, not a rounded display.
    return format(value, ".17g") if isinstance(value, float) else str(value)


def table(label, rows):
    print(label)
    for row in rows:
        print(" | ".join(map(text, row)))


db = sqlite3.connect(":memory:")
db.executescript(Path("seed.sql").read_text())
queries = [sql.strip() for sql in Path("queries.sql").read_text().split(";") if sql.strip()]
assert len(queries) == 11
answers = [db.execute(sql).fetchall() for sql in queries]
print(f"Python sqlite3 runtime: {sqlite3.sqlite_version}")
table("order_id | total_cents | discount_cents | payable_cents | typeof(payable)", answers[0])
table("1299/100 | typeof | 1299/100.0 | typeof", answers[1])
table("0.1+0.2 | 0.3 | equal | typeof(sum)", answers[2])
table("DECIMAL(6,2): order_id | retrieved amount | typeof(amount)", answers[3])
table("CAST('12x' AS INTEGER) | typeof", answers[4])
table("max integer | typeof | max integer + 1 | typeof", answers[5])
for label, rows in zip(
    ("amount TEXT BINARY ASC", "amount TEXT cast INTEGER ASC"), answers[6:8], strict=True,
):
    print(label + ": " + ", ".join(row[0] for row in rows))
table("raw-text order: label | submitted | normalized UTC", answers[8])
assert answers[9] == [(1,)]
table("normalized same-instant equality", answers[9])
# Order the same SQLite normalization results using a SQL sort key.
normalized = db.execute(
    f"SELECT label FROM ({queries[8]}) ORDER BY normalized_utc COLLATE BINARY, label"
).fetchall()
print("normalized UTC order: " + ", ".join(row[0] for row in normalized))
table("fixed-UTC text ASC: order_id | created_at", answers[10])
