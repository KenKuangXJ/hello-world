from dataclasses import dataclass
from datetime import date


@dataclass
class Expense:
    id: int | None
    amount: float
    category: str
    date: date
    notes: str
