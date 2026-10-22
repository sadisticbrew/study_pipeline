from pathlib import Path
import sqlite3


def text(value):
    return "NULL" if value is None else str(value)


def truth(value):
    return {1: "TRUE", 0: "FALSE", None: "UNKNOWN"}[value]


def table(label, rows):
    print(label)
    for row in rows:
        print(" | ".join(map(text, row)))


def compact(label, rows):
    print(label + ": " + ", ".join(":".join(map(text, row)) for row in rows))


db = sqlite3.connect(":memory:")
db.executescript(Path("seed.sql").read_text())
queries = [sql.strip() for sql in Path("queries.sql").read_text().split(";") if sql.strip()]
assert len(queries) == 17
answers = [db.execute(sql).fetchall() for sql in queries]
print(f"Python sqlite3 runtime: {sqlite3.sqlite_version}")
table("stored: order_id | buyer | total_cents | discount_cents | status | created_at", answers[0])
table("SELECT: order_id | payable_cents", answers[1])
compact("SELECT buyer", answers[2])
compact("SELECT DISTINCT buyer", answers[3])
print("conditions: order_id | discount | =0 | NOT(=0) | IS NULL | IS NOT NULL")
for order_id, discount, *conditions in answers[4]:
    print(" | ".join([str(order_id), text(discount), *map(truth, conditions)]))
for label, rows in zip(
    ("WHERE =0", "WHERE NOT(=0)", "WHERE IS NULL", "WHERE IS NOT NULL"),
    answers[5:9], strict=True,
):
    compact(label, rows)
table("NULL = NULL | NULL + 1", answers[9])
compact("pending total DESC (observed tied sequence only)", answers[10])
compact("pending total DESC, order_id ASC LIMIT 2", answers[11])
assert answers[12] == [(101, "Ada", 1299), (105, "Dee", 1299)]
table("dashboard: order_id | buyer | payable_cents", answers[12])
for label, rows in zip(
    ("discount ASC default", "discount DESC default", "discount ASC NULLS LAST",
     "discount DESC NULLS FIRST"), answers[13:17], strict=True,
):
    compact(label + " (id:value)", rows)

logic = Path("logic.sql").read_text()
print("a | b | a AND b | a OR b | NOT a")
for a in (1, 0, None):
    for b in (1, 0, None):
        result = db.execute(logic, {"a": a, "b": b}).fetchone()
        print(" | ".join(map(truth, (a, b, *result))))
