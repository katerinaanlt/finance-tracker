import json
from datetime import date, timedelta

import pytest

from finance_tracker.models import InsufficientFundsError, Profile, ProfileStore, validate_amount


def test_validate_amount_accepts_comma_and_dot():
    assert validate_amount("12,50") == 12.5
    assert validate_amount(" 3.1 ") == 3.1


@pytest.mark.parametrize("bad", ["", "abc", "0", "-5", "nan", "inf"])
def test_validate_amount_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        validate_amount(bad)


def test_balance_and_categories():
    p = Profile("t")
    p.add_income(100)
    p.add_expense(12, "Food")
    p.add_expense(15, "Entertainment")
    p.add_expense(8, "Food")
    assert p.balance == 65
    assert p.expenses_by_category() == {"Food": 20, "Entertainment": 15}


def test_expense_cannot_exceed_balance():
    p = Profile("t")
    p.add_income(50)
    p.add_expense(30, "Bills")
    # Regression: the prototype subtracted existing expenses twice, so this valid
    # 20 EUR expense (balance is exactly 20) would have been rejected.
    p.add_expense(20, "Food")
    with pytest.raises(InsufficientFundsError):
        p.add_expense(0.01, "Food")


def test_streak_counts_consecutive_days_within_limit():
    today = date(2024, 12, 10)
    p = Profile("t", daily_limit=20, created=(today - timedelta(days=5)).isoformat())
    p.add_income(1000, today - timedelta(days=5))
    p.add_expense(50, "Shopping", today - timedelta(days=3))  # over the limit
    p.add_expense(10, "Food", today - timedelta(days=1))
    assert p.streak(today) == 3  # days -2, -1, 0
    p.add_expense(25, "Food", today)
    assert p.streak(today) == 0


def test_streak_disabled_without_limit():
    assert Profile("t").streak() == 0


def test_store_roundtrip_and_profiles(tmp_path):
    path = tmp_path / "data.json"
    store = ProfileStore(path)
    store.load()
    assert store.names() == ["User"]
    store.create_profile("Maria").add_income(10)
    store.theme = "dark"
    store.save()

    again = ProfileStore(path)
    again.load()
    assert again.names() == ["User", "Maria"]
    assert again.get("Maria").balance == 10
    assert again.theme == "dark"
    with pytest.raises(ValueError):
        again.create_profile("Maria")


def test_cannot_delete_last_profile(tmp_path):
    store = ProfileStore(tmp_path / "d.json")
    store.load()
    with pytest.raises(ValueError):
        store.delete_profile("User")


def test_corrupt_file_is_backed_up(tmp_path):
    path = tmp_path / "data.json"
    path.write_text("{ not json")
    store = ProfileStore(path)
    store.load()
    assert store.names() == ["User"]
    assert (tmp_path / "data.json.bak").exists()
