import pytest

from finance_tracker.receipt_ocr import extract_total, find_amounts


def test_find_amounts_formats():
    assert find_amounts("A 12.50  B 3,20  C 1.234,56  D 1,234.56") == [12.5, 3.2, 1234.56]


def test_dates_and_phone_numbers_are_ignored():
    assert find_amounts("Date 12.04.2024 Tel 2101234567 Total 9.90") == [9.9]


def test_total_prefers_keyword_line_over_max():
    text = "Item 2.50\nSUBTOTAL 40.00\nTOTAL 38.00\nCASH 50.00"
    assert extract_total(text) == 38.0


def test_greek_total_with_accents_and_comma():
    assert extract_total("ΦΠΑ 24% 2,40\nΣΎΝΟΛΟ 12,40\nΜΕΤΡΗΤΑ 20,00") == 12.4


def test_total_on_next_line():
    assert extract_total("TOTAL\n17.35") == 17.35


def test_fallback_to_largest_amount():
    assert extract_total("Coffee 2.50\nCake 4.00") == 4.0


@pytest.mark.parametrize("text", ["", "no numbers here"])
def test_empty_results_do_not_crash(text):
    assert find_amounts(text) == []
    assert extract_total(text) is None
