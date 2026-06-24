"""
cit411_utils.cleaning — Data-Cleaning Helpers
==============================================

Functions for normalizing and validating raw CSV/tabular data.

All functions are pure (no side-effects) and raise ``ValueError`` for inputs
that are irrecoverably malformed, so callers can choose how to handle errors.

Typical usage
-------------
>>> from cit411_utils.cleaning import clean_email, clean_phone, clean_csv
>>> clean_email("  Alice@Example.COM  ")
'alice@example.com'
>>> clean_phone("(305) 555-1234")
'3055551234'
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def clean_text(value: Any, *, max_length: int | None = None) -> str:
    """
    Strip leading/trailing whitespace and collapse internal runs of whitespace.

    Parameters
    ----------
    value:
        Any value — converted to ``str`` first.
    max_length:
        If given, truncate the result to this many characters.

    Returns
    -------
    str
        Cleaned string.

    Examples
    --------
    >>> clean_text("  hello   world  ")
    'hello world'
    >>> clean_text("toolongvalue", max_length=5)
    'toolong'[:5] == 'toolong'[:5]
    """
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    if max_length is not None:
        text = text[:max_length]
    return text


def clean_email(email: Any) -> str:
    """
    Lowercase and strip an e-mail address.

    Parameters
    ----------
    email:
        Raw e-mail string (leading/trailing whitespace is ignored).

    Returns
    -------
    str
        Normalized e-mail address in lowercase.

    Raises
    ------
    ValueError
        If the cleaned value does not contain exactly one ``@``.

    Examples
    --------
    >>> clean_email("  Alice@Example.COM  ")
    'alice@example.com'
    """
    cleaned = clean_text(email).lower()
    if cleaned.count("@") != 1:
        raise ValueError(f"Invalid e-mail address: {email!r}")
    return cleaned


def clean_phone(phone: Any, *, digits_only: bool = True) -> str:
    """
    Normalize a US phone number to 10 digits (or formatted string).

    Parameters
    ----------
    phone:
        Raw phone string — parentheses, dashes, dots, and spaces are removed.
    digits_only:
        If ``True`` (default), return only the 10-digit string.
        If ``False``, return in ``(NXX) NXX-XXXX`` format.

    Returns
    -------
    str
        Normalized phone number.

    Raises
    ------
    ValueError
        If the result is not exactly 10 digits.

    Examples
    --------
    >>> clean_phone("(305) 555-1234")
    '3055551234'
    >>> clean_phone("305.555.1234", digits_only=False)
    '(305) 555-1234'
    """
    digits = re.sub(r"\D", "", str(phone))
    # strip leading country code 1
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(f"Expected 10 digits, got {len(digits)}: {phone!r}")
    if digits_only:
        return digits
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def clean_numeric(value: Any, *, allow_negative: bool = True) -> float:
    """
    Convert a value to float, stripping currency symbols and commas.

    Parameters
    ----------
    value:
        Raw value, e.g. ``"$1,234.56"`` or ``1234.56``.
    allow_negative:
        If ``False``, raise ``ValueError`` for negative results.

    Returns
    -------
    float

    Raises
    ------
    ValueError
        If the value cannot be converted.

    Examples
    --------
    >>> clean_numeric("$1,234.56")
    1234.56
    """
    cleaned = re.sub(r"[^\d.\-]", "", str(value))
    try:
        result = float(cleaned)
    except ValueError:
        raise ValueError(f"Cannot convert to numeric: {value!r}")
    if not allow_negative and result < 0:
        raise ValueError(f"Negative value not allowed: {result}")
    return result


# ---------------------------------------------------------------------------
# Row / CSV helpers
# ---------------------------------------------------------------------------

def validate_row(
    row: dict[str, Any],
    required_fields: list[str],
) -> tuple[bool, list[str]]:
    """
    Check that a CSV row contains all required fields with non-empty values.

    Parameters
    ----------
    row:
        A single row as a ``dict`` (e.g. from ``csv.DictReader``).
    required_fields:
        Field names that must be present and non-empty.

    Returns
    -------
    tuple[bool, list[str]]
        ``(is_valid, list_of_missing_fields)``

    Examples
    --------
    >>> validate_row({"name": "Alice", "email": ""}, ["name", "email"])
    (False, ['email'])
    """
    missing = [
        f for f in required_fields
        if not str(row.get(f, "")).strip()
    ]
    return (len(missing) == 0, missing)


def clean_csv(
    input_path: str | Path,
    output_path: str | Path,
    *,
    required_fields: list[str] | None = None,
    email_fields: list[str] | None = None,
    phone_fields: list[str] | None = None,
    numeric_fields: list[str] | None = None,
    skip_invalid: bool = True,
) -> dict[str, int]:
    """
    Read a CSV file, clean specified columns, and write cleaned rows.

    Parameters
    ----------
    input_path:
        Path to the source CSV file.
    output_path:
        Path where the cleaned CSV will be written.
    required_fields:
        Rows missing any of these fields (or with empty values) are flagged.
    email_fields:
        Column names to run through :func:`clean_email`.
    phone_fields:
        Column names to run through :func:`clean_phone`.
    numeric_fields:
        Column names to run through :func:`clean_numeric`.
    skip_invalid:
        If ``True`` (default), invalid rows are skipped; otherwise they are
        written as-is with an ``_error`` column added.

    Returns
    -------
    dict[str, int]
        Summary counters: ``total``, ``written``, ``skipped``, ``errors``.

    Examples
    --------
    >>> stats = clean_csv("raw.csv", "clean.csv",
    ...     required_fields=["name","email"],
    ...     email_fields=["email"])
    >>> print(stats)
    {'total': 100, 'written': 97, 'skipped': 3, 'errors': 3}
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    email_fields  = email_fields  or []
    phone_fields  = phone_fields  or []
    numeric_fields = numeric_fields or []
    required_fields = required_fields or []

    counters = {"total": 0, "written": 0, "skipped": 0, "errors": 0}

    with input_path.open(newline="", encoding="utf-8-sig") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        if not skip_invalid:
            fieldnames.append("_error")

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            counters["total"] += 1
            errors: list[str] = []

            # Required-field validation
            valid, missing = validate_row(row, required_fields)
            if not valid:
                errors.append(f"missing: {missing}")

            # Field cleaning
            for field in email_fields:
                if field in row and row[field]:
                    try:
                        row[field] = clean_email(row[field])
                    except ValueError as exc:
                        errors.append(str(exc))

            for field in phone_fields:
                if field in row and row[field]:
                    try:
                        row[field] = clean_phone(row[field])
                    except ValueError as exc:
                        errors.append(str(exc))

            for field in numeric_fields:
                if field in row and row[field]:
                    try:
                        row[field] = clean_numeric(row[field])
                    except ValueError as exc:
                        errors.append(str(exc))

            if errors:
                counters["errors"] += 1
                if skip_invalid:
                    counters["skipped"] += 1
                    continue
                row["_error"] = "; ".join(errors)

            writer.writerow(row)
            counters["written"] += 1

    return counters
