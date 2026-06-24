"""
cit411_utils — CIT 411 Lab Utility Package
===========================================

A consolidated Python utility package built during the CIT 411 course (Weeks 2–4).
Provides three functional submodules for common data-engineering tasks:

Submodules
----------
cleaning
    Data-cleaning helpers: normalize emails, strip whitespace, fix phone numbers,
    validate rows, and clean an entire CSV file in one call.

weather
    Weather-fetching helpers: retrieve current conditions and a multi-day forecast
    from the Open-Meteo API (no API key required).

inventory
    Inventory-analysis helpers: compute summary statistics, flag low-stock SKUs,
    find the top N movers, and generate a printable markdown report.

Quick Start
-----------
>>> from cit411_utils.cleaning  import clean_email
>>> from cit411_utils.weather   import get_current_weather
>>> from cit411_utils.inventory import summarize_inventory

>>> clean_email("  Alice@Example.COM  ")
'alice@example.com'

>>> summary = get_current_weather(latitude=25.96, longitude=-80.35)  # Pembroke Pines, FL
>>> print(summary["description"])

>>> import pandas as pd
>>> df = pd.DataFrame({"sku": ["A1","B2"], "quantity": [5, 120], "unit_price": [9.99, 4.49]})
>>> print(summarize_inventory(df))

Author
------
Waqar Javed  <github.com/iamwaqarjaved>

License
-------
MIT
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("cit411_utils")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__author__ = "Waqar Javed"
__all__ = ["cleaning", "weather", "inventory"]
