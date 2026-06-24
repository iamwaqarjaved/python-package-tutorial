"""
tests/test_cit411_utils.py — Unit tests for cit411_utils
=========================================================

Run with:
    pytest -v
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# cleaning tests
# ---------------------------------------------------------------------------
from cit411_utils.cleaning import (
    clean_email,
    clean_numeric,
    clean_phone,
    clean_text,
    clean_csv,
    validate_row,
)


class TestCleanText:
    def test_strips_whitespace(self):
        assert clean_text("  hello  ") == "hello"

    def test_collapses_internal_spaces(self):
        assert clean_text("hello   world") == "hello world"

    def test_truncates(self):
        assert clean_text("abcdef", max_length=3) == "abc"

    def test_converts_non_str(self):
        assert clean_text(42) == "42"


class TestCleanEmail:
    def test_normalizes(self):
        assert clean_email("  Alice@Example.COM  ") == "alice@example.com"

    def test_rejects_no_at(self):
        with pytest.raises(ValueError):
            clean_email("notanemail")

    def test_rejects_multiple_at(self):
        with pytest.raises(ValueError):
            clean_email("a@@b.com")


class TestCleanPhone:
    def test_strips_formatting(self):
        assert clean_phone("(305) 555-1234") == "3055551234"

    def test_formatted_output(self):
        assert clean_phone("3055551234", digits_only=False) == "(305) 555-1234"

    def test_strips_country_code(self):
        assert clean_phone("+13055551234") == "3055551234"

    def test_rejects_short(self):
        with pytest.raises(ValueError):
            clean_phone("305-123")


class TestCleanNumeric:
    def test_strips_currency(self):
        assert clean_numeric("$1,234.56") == 1234.56

    def test_plain_float(self):
        assert clean_numeric(9.99) == 9.99

    def test_rejects_negative_when_disallowed(self):
        with pytest.raises(ValueError):
            clean_numeric("-5.00", allow_negative=False)

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError):
            clean_numeric("abc")


class TestValidateRow:
    def test_valid(self):
        ok, missing = validate_row({"a": "x", "b": "y"}, ["a", "b"])
        assert ok and not missing

    def test_missing_field(self):
        ok, missing = validate_row({"a": "x"}, ["a", "b"])
        assert not ok and "b" in missing

    def test_empty_value(self):
        ok, missing = validate_row({"a": "", "b": "y"}, ["a", "b"])
        assert not ok and "a" in missing


class TestCleanCsv:
    def test_full_pipeline(self, tmp_path):
        infile = tmp_path / "raw.csv"
        outfile = tmp_path / "clean.csv"
        infile.write_text(
            "name,email,phone\n"
            "Alice, alice@example.com ,(305)555-0001\n"
            "Bad,,12345\n",
            encoding="utf-8",
        )
        stats = clean_csv(
            infile,
            outfile,
            required_fields=["name", "email"],
            email_fields=["email"],
            phone_fields=["phone"],
            skip_invalid=True,
        )
        assert stats["total"] == 2
        assert stats["written"] == 1
        assert stats["skipped"] == 1


# ---------------------------------------------------------------------------
# inventory tests
# ---------------------------------------------------------------------------
from cit411_utils.inventory import (
    flag_low_stock,
    inventory_report,
    summarize_inventory,
    top_movers,
)

SAMPLE = pd.DataFrame(
    [
        {"sku": "A1", "quantity": 100, "unit_price": 10.0, "reorder_point": 20, "category": "Cat1"},
        {"sku": "B2", "quantity": 5,   "unit_price":  5.0, "reorder_point": 10, "category": "Cat2"},
        {"sku": "C3", "quantity": 0,   "unit_price": 20.0, "reorder_point": 10, "category": "Cat1"},
    ]
)


class TestSummarizeInventory:
    def test_total_skus(self):
        assert summarize_inventory(SAMPLE)["total_skus"] == 3

    def test_out_of_stock(self):
        s = summarize_inventory(SAMPLE)
        assert s["out_of_stock_count"] == 1
        assert "C3" in s["out_of_stock_skus"]

    def test_total_value(self):
        # 100*10 + 5*5 + 0*20 = 1025.0
        assert summarize_inventory(SAMPLE)["total_value"] == 1025.0

    def test_missing_columns_raises(self):
        with pytest.raises(ValueError):
            summarize_inventory(pd.DataFrame({"sku": ["X"]}))


class TestFlagLowStock:
    def test_flags_below_reorder(self):
        low = flag_low_stock(SAMPLE)
        skus = set(low["sku"])
        assert "B2" in skus  # qty 5 <= reorder 10
        assert "C3" in skus  # qty 0 <= reorder 10

    def test_default_reorder_point(self):
        df = pd.DataFrame({"sku": ["X"], "quantity": [3], "unit_price": [1.0]})
        low = flag_low_stock(df, default_reorder_point=5)
        assert len(low) == 1


class TestTopMovers:
    def test_returns_n(self):
        movers = top_movers(SAMPLE, n=2)
        assert len(movers) == 2

    def test_sorted_by_line_value(self):
        movers = top_movers(SAMPLE, n=3, rank_by="line_value")
        assert movers.iloc[0]["sku"] == "A1"  # 100*10 = 1000

    def test_invalid_rank_by_raises(self):
        with pytest.raises(ValueError):
            top_movers(SAMPLE, rank_by="revenue")


class TestInventoryReport:
    def test_returns_string(self):
        report = inventory_report(SAMPLE)
        assert isinstance(report, str)

    def test_contains_header(self):
        report = inventory_report(SAMPLE, title="Test Report")
        assert "Test Report" in report
