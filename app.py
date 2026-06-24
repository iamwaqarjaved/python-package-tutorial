"""
app.py — Consuming Application for cit411_utils
================================================

Demonstrates all three submodules of the cit411_utils package:

    1. cleaning  — normalize a sample CSV file
    2. weather   — fetch current conditions + forecast for Pembroke Pines, FL
    3. inventory — analyse a sample inventory DataFrame and print a report

Run from the project root after installing in editable mode:
    pip install -e .
    python app.py
"""

from __future__ import annotations

import csv
import io
import json
import sys
import textwrap
from pathlib import Path

import pandas as pd

import cit411_utils
from cit411_utils.cleaning  import clean_email, clean_phone, clean_numeric, clean_csv
from cit411_utils.weather   import get_current_weather, get_forecast, weather_report
from cit411_utils.inventory import (
    summarize_inventory,
    flag_low_stock,
    top_movers,
    inventory_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIVIDER = "=" * 60


def section(title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


# ---------------------------------------------------------------------------
# 1. Data Cleaning Demo
# ---------------------------------------------------------------------------

def demo_cleaning() -> None:
    section("MODULE 1 — cit411_utils.cleaning")

    # --- scalar helpers ---
    raw_email = "  WAQAR@Example.COM  "
    raw_phone = "(305) 555-1234"
    raw_price = "$1,299.99"

    print(f"\nclean_email({raw_email!r})")
    print(f"  → {clean_email(raw_email)}")

    print(f"\nclean_phone({raw_phone!r})")
    print(f"  → {clean_phone(raw_phone)}")
    print(f"  → formatted: {clean_phone(raw_phone, digits_only=False)}")

    print(f"\nclean_numeric({raw_price!r})")
    print(f"  → {clean_numeric(raw_price)}")

    # --- CSV cleaning ---
    raw_csv = textwrap.dedent("""\
        name,email,phone,price
        Alice," Alice@Example.COM ","(305) 555-0001","$9.99"
        Bob,"not-an-email","(305) 555-0002","$19.99"
        Charlie,"charlie@test.com","bad-phone","$29.99"
        Dana,"dana@example.com","(305) 555-0004","$39.99"
        Eve,"","(305) 555-0005","$0.00"
    """)

    input_path  = Path("/tmp/demo_raw.csv")
    output_path = Path("/tmp/demo_clean.csv")
    input_path.write_text(raw_csv, encoding="utf-8")

    stats = clean_csv(
        input_path,
        output_path,
        required_fields=["name", "email"],
        email_fields=["email"],
        phone_fields=["phone"],
        numeric_fields=["price"],
        skip_invalid=True,
    )

    print(f"\nclean_csv('{input_path.name}' → '{output_path.name}')")
    print(f"  Stats: {stats}")
    print("\n  Cleaned rows:")
    with output_path.open() as f:
        for line in f:
            print(f"    {line}", end="")


# ---------------------------------------------------------------------------
# 2. Weather Demo
# ---------------------------------------------------------------------------

PEMBROKE_PINES_LAT = 25.9606
PEMBROKE_PINES_LON = -80.3533


def demo_weather() -> None:
    section("MODULE 2 — cit411_utils.weather")

    print("\nFetching current weather for Pembroke Pines, FL …")
    try:
        current = get_current_weather(
            latitude=PEMBROKE_PINES_LAT,
            longitude=PEMBROKE_PINES_LON,
        )
        print(f"\n  Timestamp:    {current['timestamp']}")
        print(f"  Conditions:   {current['weather_desc']}")
        print(f"  Temperature:  {current['temperature']} {current['temperature_unit']}")
        print(f"  Wind speed:   {current['wind_speed']} {current['wind_speed_unit']}")
        print(f"\n  One-liner → {current['description']}")

        print("\nFetching 5-day forecast …")
        report = weather_report(
            latitude=PEMBROKE_PINES_LAT,
            longitude=PEMBROKE_PINES_LON,
            location_name="Pembroke Pines, FL",
            forecast_days=5,
        )
        print("\n" + report)

    except Exception as exc:  # noqa: BLE001
        print(f"  [weather fetch failed — check network] {exc}")


# ---------------------------------------------------------------------------
# 3. Inventory Demo
# ---------------------------------------------------------------------------

SAMPLE_INVENTORY = [
    {"sku": "ELEC-001", "product_name": "Wireless Headphones", "category": "Electronics",
     "quantity": 120, "unit_price": 49.99, "reorder_point": 20},
    {"sku": "ELEC-002", "product_name": "Bluetooth Speaker",   "category": "Electronics",
     "quantity": 8,   "unit_price": 34.99, "reorder_point": 15},
    {"sku": "ELEC-003", "product_name": "USB-C Hub",           "category": "Electronics",
     "quantity": 0,   "unit_price": 24.99, "reorder_point": 10},
    {"sku": "HOME-001", "product_name": "Scented Candle",      "category": "Home",
     "quantity": 250, "unit_price":  8.99, "reorder_point": 50},
    {"sku": "HOME-002", "product_name": "Throw Pillow",        "category": "Home",
     "quantity": 5,   "unit_price": 19.99, "reorder_point": 10},
    {"sku": "BOOK-001", "product_name": "Python Cookbook",     "category": "Books",
     "quantity": 33,  "unit_price": 39.99, "reorder_point": 10},
    {"sku": "BOOK-002", "product_name": "Clean Code",          "category": "Books",
     "quantity": 12,  "unit_price": 29.99, "reorder_point": 10},
    {"sku": "APRL-001", "product_name": "Logo T-Shirt (M)",    "category": "Apparel",
     "quantity": 3,   "unit_price": 24.99, "reorder_point": 10},
    {"sku": "APRL-002", "product_name": "Logo Hoodie (L)",     "category": "Apparel",
     "quantity": 88,  "unit_price": 59.99, "reorder_point": 15},
    {"sku": "APRL-003", "product_name": "Baseball Cap",        "category": "Apparel",
     "quantity": 0,   "unit_price": 14.99, "reorder_point":  5},
]


def demo_inventory() -> None:
    section("MODULE 3 — cit411_utils.inventory")

    df = pd.DataFrame(SAMPLE_INVENTORY)

    # --- Summary ---
    print("\n  summarize_inventory(df):")
    stats = summarize_inventory(df)
    for key, val in stats.items():
        print(f"    {key:<22} {val}")

    # --- Low stock ---
    print("\n  flag_low_stock(df):")
    low = flag_low_stock(df)
    if low.empty:
        print("    No low-stock items.")
    else:
        cols = ["sku", "product_name", "quantity", "reorder_point"]
        print(low[cols].to_string(index=False, justify="left"))

    # --- Top movers ---
    print("\n  top_movers(df, n=3, rank_by='line_value'):")
    movers = top_movers(df, n=3)
    cols = ["sku", "product_name", "quantity", "unit_price", "line_value"]
    print(movers[cols].to_string(index=False, justify="left"))

    # --- Full Markdown report ---
    print("\n  inventory_report(df):\n")
    report = inventory_report(df, title="WaqarMart — Lab 6 Demo Inventory")
    print(report)

    # Save report to file
    report_path = Path("/tmp/inventory_report.md")
    report_path.write_text(report, encoding="utf-8")
    print(f"\n  ✔  Report saved to: {report_path}")


# ---------------------------------------------------------------------------
# 4. Package metadata / help() demo
# ---------------------------------------------------------------------------

def demo_package_info() -> None:
    section("PACKAGE INFO — help(cit411_utils)")
    print(f"\n  cit411_utils.__version__ = {cit411_utils.__version__!r}")
    print(f"  cit411_utils.__author__  = {cit411_utils.__author__!r}")
    print(f"  cit411_utils.__all__     = {cit411_utils.__all__!r}")
    print("\n  Package docstring (shown by help()):")
    print(textwrap.indent(cit411_utils.__doc__ or "", "    "))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 60)
    print("  cit411_utils — Lab 6 Consuming Application")
    print("  CIT 411 | Waqar Javed")
    print("=" * 60)

    demo_package_info()
    demo_cleaning()
    demo_weather()
    demo_inventory()

    print(f"\n{DIVIDER}")
    print("  ✔  All demos complete.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    main()
