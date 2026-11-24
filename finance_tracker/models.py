"""Pure-Python data layer (no Qt imports so it is easy to unit-test).

A ``Profile`` holds a person's transactions and settings. A ``ProfileStore``
persists any number of profiles to a single JSON file.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_CATEGORIES = ["Food", "Transportation", "Shopping", "Entertainment", "Bills", "Others"]
DEFAULT_DATA_FILE = Path.home() / ".finance_tracker" / "data.json"


class InsufficientFundsError(ValueError):
    """Raised when an expense is larger than the current balance."""


def validate_amount(value) -> float:
    """Parse user input into a positive, finite, 2-decimal float.

    Accepts both ``12.50`` and ``12,50`` (Greek/European decimal comma).
    """
    try:
        amount = float(str(value).strip().replace(",", "."))
    except ValueError:
        raise ValueError("Invalid input. Please enter a valid number.") from None
    if not math.isfinite(amount):
        raise ValueError("Invalid input. Please enter a valid number.")
    if amount <= 0:
        raise ValueError("Value must be a positive number.")
    return round(amount, 2)


@dataclass
class Transaction:
    kind: str           # "income" or "expense"
    amount: float
    day: str            # ISO date, e.g. "2024-12-04"
    category: str = ""  # only meaningful for expenses


@dataclass
class Profile:
    name: str
    currency: str = "€"
    daily_limit: float = 0.0  # 0 disables the daily limit / streak feature
    created: str = field(default_factory=lambda: date.today().isoformat())
    transactions: List[Transaction] = field(default_factory=list)

    # ---- totals -----------------------------------------------------------
    @property
    def total_income(self) -> float:
        return sum(t.amount for t in self.transactions if t.kind == "income")

    @property
    def total_expenses(self) -> float:
        return sum(t.amount for t in self.transactions if t.kind == "expense")

    @property
    def balance(self) -> float:
        return round(self.total_income - self.total_expenses, 2)

    def expenses_by_category(self) -> Dict[str, float]:
        totals: Dict[str, float] = defaultdict(float)
        for t in self.transactions:
            if t.kind == "expense":
                totals[t.category] += t.amount
        return dict(totals)

    def spent_on(self, day: date) -> float:
        iso = day.isoformat()
        return sum(t.amount for t in self.transactions if t.kind == "expense" and t.day == iso)

    # ---- mutations --------------------------------------------------------
    def add_income(self, amount: float, day: Optional[date] = None) -> Transaction:
        tx = Transaction("income", amount, (day or date.today()).isoformat())
        self.transactions.append(tx)
        return tx

    def add_expense(self, amount: float, category: str, day: Optional[date] = None) -> Transaction:
        if amount > self.balance + 1e-9:
            raise InsufficientFundsError("Expense exceeds available balance!")
        tx = Transaction("expense", amount, (day or date.today()).isoformat(), category)
        self.transactions.append(tx)
        return tx

    # ---- streaks ----------------------------------------------------------
    def streak(self, today: Optional[date] = None) -> int:
        """Consecutive days (ending today) on which spending stayed within the daily limit.

        Days with no spending count as "within budget". Counting starts at the
        profile's creation date. Returns 0 if no daily limit is configured.
        """
        if self.daily_limit <= 0:
            return 0
        today = today or date.today()
        start = date.fromisoformat(self.created)
        count, day = 0, today
        while day >= start:
            if self.spent_on(day) > self.daily_limit + 1e-9:
                break
            count += 1
            day -= timedelta(days=1)
        return count

    # ---- (de)serialisation ------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        txs = [Transaction(**t) for t in data.get("transactions", [])]
        return cls(
            name=data["name"],
            currency=data.get("currency", "€"),
            daily_limit=float(data.get("daily_limit", 0.0)),
            created=data.get("created", date.today().isoformat()),
            transactions=txs,
        )


class ProfileStore:
    """Loads/saves all profiles plus global settings (theme, last used profile)."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_DATA_FILE
        self.profiles: Dict[str, Profile] = {}
        self.theme = "light"
        self.last_profile = "User"

    def names(self) -> List[str]:
        return list(self.profiles)

    def get(self, name: Optional[str] = None) -> Profile:
        if name in self.profiles:
            return self.profiles[name]
        return next(iter(self.profiles.values()))

    def create_profile(self, name: str) -> Profile:
        name = name.strip()
        if not name:
            raise ValueError("Profile name cannot be empty.")
        if name in self.profiles:
            raise ValueError(f"A profile named '{name}' already exists.")
        self.profiles[name] = Profile(name=name)
        return self.profiles[name]

    def delete_profile(self, name: str) -> None:
        if len(self.profiles) <= 1:
            raise ValueError("You cannot delete the last remaining profile.")
        self.profiles.pop(name, None)
        if self.last_profile == name:
            self.last_profile = next(iter(self.profiles))

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.theme = raw.get("theme", "light")
            self.last_profile = raw.get("last_profile", "User")
            self.profiles = {p["name"]: Profile.from_dict(p) for p in raw.get("profiles", [])}
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # Corrupt file: keep a backup instead of silently destroying user data.
            self.path.replace(self.path.with_suffix(".json.bak"))
            self.profiles = {}
        if not self.profiles:
            self.create_profile("User")
            self.last_profile = "User"

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "theme": self.theme,
            "last_profile": self.last_profile,
            "profiles": [p.to_dict() for p in self.profiles.values()],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)  # atomic: never leaves a half-written file
