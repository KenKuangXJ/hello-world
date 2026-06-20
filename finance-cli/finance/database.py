import sqlite3
from datetime import date, datetime
from .models import Expense

DB_FILE = "finance.db"


def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)


def add_expense(expense: Expense) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (amount, category, date, notes) VALUES (?, ?, ?, ?)",
            (expense.amount, expense.category, expense.date.isoformat(), expense.notes),
        )
        return cur.lastrowid


def list_expenses(year: int | None = None, month: int | None = None,
                  category: str | None = None) -> list[Expense]:
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    if year and month:
        query += " AND strftime('%Y', date) = ? AND strftime('%m', date) = ?"
        params += [str(year), f"{month:02d}"]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY date DESC, id DESC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        Expense(
            id=row["id"],
            amount=row["amount"],
            category=row["category"],
            date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
            notes=row["notes"],
        )
        for row in rows
    ]


def stats_by_category(year: int | None = None, month: int | None = None) -> list[dict]:
    query = """
        SELECT category, COUNT(*) as count, SUM(amount) as total
        FROM expenses WHERE 1=1
    """
    params = []
    if year and month:
        query += " AND strftime('%Y', date) = ? AND strftime('%m', date) = ?"
        params += [str(year), f"{month:02d}"]
    elif year:
        query += " AND strftime('%Y', date) = ?"
        params.append(str(year))
    query += " GROUP BY category ORDER BY total DESC"

    with _connect() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def daily_stats(year: int, month: int) -> list[dict]:
    query = """
        SELECT date, SUM(amount) as total
        FROM expenses
        WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY date
        ORDER BY date ASC
    """
    with _connect() as conn:
        return [dict(r) for r in conn.execute(query, (str(year), f"{month:02d}")).fetchall()]


def delete_expense(expense_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return cur.rowcount > 0


def get_all_categories() -> list[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM expenses ORDER BY category").fetchall()
    return [r["category"] for r in rows]


def get_months_range() -> list[tuple[int, int]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT strftime('%Y', date) as y, strftime('%m', date) as m "
            "FROM expenses ORDER BY y DESC, m DESC"
        ).fetchall()
    return [(int(r["y"]), int(r["m"])) for r in rows]
