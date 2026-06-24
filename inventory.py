"""
cit411_utils.inventory — Inventory Analysis Helpers
====================================================

Analyse a pandas DataFrame that represents a product-inventory snapshot.

The DataFrame must contain at least these columns:

* ``sku``        — unique product identifier (str)
* ``quantity``   — units on hand (int or float)
* ``unit_price`` — price per unit in USD (float)

Optional but used when present:

* ``product_name``  — human-readable name
* ``category``      — product category
* ``reorder_point`` — trigger quantity for replenishment alert

Typical usage
-------------
>>> import pandas as pd
>>> from cit411_utils.inventory import summarize_inventory, flag_low_stock
>>>
>>> df = pd.read_csv("inventory.csv")
>>> print(summarize_inventory(df))
>>> low = flag_low_stock(df)
>>> print(low[["sku", "quantity", "reorder_point"]])
"""

from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "cit411_utils.inventory requires pandas.  "
        "Install with: pip install pandas"
    ) from exc


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_COLS = {"sku", "quantity", "unit_price"}


def _validate(df: pd.DataFrame) -> None:
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame is missing required columns: {missing}")


# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------

def summarize_inventory(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute summary statistics for an inventory DataFrame.

    Parameters
    ----------
    df:
        Inventory DataFrame with ``sku``, ``quantity``, ``unit_price`` columns.

    Returns
    -------
    dict
        Keys: ``total_skus``, ``total_units``, ``total_value``,
        ``avg_unit_price``, ``max_price_sku``, ``min_price_sku``,
        ``out_of_stock_count``, ``out_of_stock_skus``.

    Examples
    --------
    >>> stats = summarize_inventory(df)
    >>> print(f"Portfolio value: ${stats['total_value']:,.2f}")
    """
    _validate(df)
    df = df.copy()
    df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce").fillna(0)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0)
    df["line_value"] = df["quantity"] * df["unit_price"]

    oos = df[df["quantity"] <= 0]
    max_row = df.loc[df["unit_price"].idxmax()]
    min_row = df.loc[df["unit_price"].idxmin()]

    return {
        "total_skus":        len(df),
        "total_units":       int(df["quantity"].sum()),
        "total_value":       round(float(df["line_value"].sum()), 2),
        "avg_unit_price":    round(float(df["unit_price"].mean()), 2),
        "max_price_sku":     str(max_row["sku"]),
        "max_price":         round(float(max_row["unit_price"]), 2),
        "min_price_sku":     str(min_row["sku"]),
        "min_price":         round(float(min_row["unit_price"]), 2),
        "out_of_stock_count": int(len(oos)),
        "out_of_stock_skus": list(oos["sku"].astype(str)),
    }


def flag_low_stock(
    df: pd.DataFrame,
    *,
    default_reorder_point: int = 10,
) -> pd.DataFrame:
    """
    Return rows whose ``quantity`` is at or below their reorder point.

    Parameters
    ----------
    df:
        Inventory DataFrame.
    default_reorder_point:
        Used when the DataFrame has no ``reorder_point`` column (default: 10).

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only low-stock rows, sorted by
        ``quantity`` ascending.

    Examples
    --------
    >>> low = flag_low_stock(df, default_reorder_point=20)
    >>> print(low[["sku", "quantity"]])
    """
    _validate(df)
    df = df.copy()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)

    if "reorder_point" not in df.columns:
        df["reorder_point"] = default_reorder_point
    else:
        df["reorder_point"] = (
            pd.to_numeric(df["reorder_point"], errors="coerce")
            .fillna(default_reorder_point)
        )

    mask = df["quantity"] <= df["reorder_point"]
    return df[mask].sort_values("quantity").reset_index(drop=True)


def top_movers(
    df: pd.DataFrame,
    n: int = 5,
    *,
    rank_by: str = "line_value",
) -> pd.DataFrame:
    """
    Return the top-N SKUs ranked by line value or quantity.

    Parameters
    ----------
    df:
        Inventory DataFrame.
    n:
        Number of top SKUs to return (default: 5).
    rank_by:
        ``"line_value"`` (qty × price, default) or ``"quantity"``.

    Returns
    -------
    pd.DataFrame
        Top-N rows sorted descending by the chosen metric.

    Raises
    ------
    ValueError
        If ``rank_by`` is not ``"line_value"`` or ``"quantity"``.

    Examples
    --------
    >>> movers = top_movers(df, n=3, rank_by="quantity")
    >>> print(movers[["sku", "quantity"]])
    """
    _validate(df)
    if rank_by not in ("line_value", "quantity"):
        raise ValueError('rank_by must be "line_value" or "quantity"')

    df = df.copy()
    df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce").fillna(0)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0)
    df["line_value"] = df["quantity"] * df["unit_price"]

    return (
        df.sort_values(rank_by, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group inventory by ``category`` column and compute per-group stats.

    Parameters
    ----------
    df:
        Inventory DataFrame that includes a ``category`` column.

    Returns
    -------
    pd.DataFrame
        One row per category with columns: ``category``, ``sku_count``,
        ``total_units``, ``total_value``, ``avg_unit_price``.

    Raises
    ------
    ValueError
        If the DataFrame has no ``category`` column.

    Examples
    --------
    >>> breakdown = category_breakdown(df)
    >>> print(breakdown.to_string(index=False))
    """
    _validate(df)
    if "category" not in df.columns:
        raise ValueError("DataFrame must contain a 'category' column.")

    df = df.copy()
    df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce").fillna(0)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0)
    df["line_value"] = df["quantity"] * df["unit_price"]

    grp = (
        df.groupby("category", as_index=False)
        .agg(
            sku_count   =("sku",        "count"),
            total_units =("quantity",   "sum"),
            total_value =("line_value", "sum"),
            avg_unit_price=("unit_price", "mean"),
        )
    )
    grp["total_value"]    = grp["total_value"].round(2)
    grp["avg_unit_price"] = grp["avg_unit_price"].round(2)
    return grp.sort_values("total_value", ascending=False).reset_index(drop=True)


def inventory_report(df: pd.DataFrame, title: str = "Inventory Report") -> str:
    """
    Generate a formatted Markdown-style inventory report string.

    Parameters
    ----------
    df:
        Inventory DataFrame.
    title:
        Header title for the report.

    Returns
    -------
    str
        Multi-line report suitable for printing or saving to a ``.md`` file.

    Examples
    --------
    >>> print(inventory_report(df, title="WaqarMart — June 2026"))
    """
    stats  = summarize_inventory(df)
    low    = flag_low_stock(df)
    movers = top_movers(df, n=5)

    lines = [
        f"# {title}",
        "",
        "## Summary",
        f"- **Total SKUs:** {stats['total_skus']}",
        f"- **Total Units on Hand:** {stats['total_units']:,}",
        f"- **Portfolio Value:** ${stats['total_value']:,.2f}",
        f"- **Average Unit Price:** ${stats['avg_unit_price']:.2f}",
        f"- **Out-of-Stock SKUs:** {stats['out_of_stock_count']}",
        "",
        "## ⚠️  Low-Stock Alerts",
    ]

    if low.empty:
        lines.append("_No low-stock items._")
    else:
        lines.append(f"| SKU | Qty | Reorder Point |")
        lines.append(f"|-----|-----|---------------|")
        for _, row in low.head(10).iterrows():
            lines.append(f"| {row['sku']} | {int(row['quantity'])} | {int(row['reorder_point'])} |")

    lines += [
        "",
        "## 🏆 Top 5 SKUs by Line Value",
        "| Rank | SKU | Qty | Unit Price | Line Value |",
        "|------|-----|-----|-----------|------------|",
    ]

    for i, row in movers.iterrows():
        lines.append(
            f"| {i+1} | {row['sku']} | {int(row['quantity'])} "
            f"| ${row['unit_price']:.2f} | ${row['line_value']:.2f} |"
        )

    if "category" in df.columns:
        try:
            cat = category_breakdown(df)
            lines += [
                "",
                "## Category Breakdown",
                "| Category | SKUs | Units | Value | Avg Price |",
                "|----------|------|-------|-------|-----------|",
            ]
            for _, row in cat.iterrows():
                lines.append(
                    f"| {row['category']} | {row['sku_count']} | {int(row['total_units'])} "
                    f"| ${row['total_value']:,.2f} | ${row['avg_unit_price']:.2f} |"
                )
        except ValueError:
            pass

    return "\n".join(lines)
