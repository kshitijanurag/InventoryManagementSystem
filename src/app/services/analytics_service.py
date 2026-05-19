from __future__ import annotations

import pandas as pd

from src.database.mongo_connection import get_analytics_database

_cleaned_inventory_dataframe_cache: pd.DataFrame | None = None


def _get_cleaned_inventory_collection():
    return get_analytics_database()["cleaned_inventory"]


def load_cleaned_inventory_dataframe(row_limit: int = 3000) -> pd.DataFrame:
    global _cleaned_inventory_dataframe_cache

    if _cleaned_inventory_dataframe_cache is not None:
        return _cleaned_inventory_dataframe_cache

    raw_documents = list(
        _get_cleaned_inventory_collection().find({}, {"_id": 0}).limit(row_limit)
    )

    if not raw_documents:
        return pd.DataFrame()

    dataframe = pd.DataFrame(raw_documents)

    date_column_candidates = ["date", "order_date", "created_at"]
    resolved_date_column = next(
        (col for col in date_column_candidates if col in dataframe.columns), None
    )
    if resolved_date_column:
        dataframe["sale_date"] = pd.to_datetime(
            dataframe[resolved_date_column], errors="coerce"
        )
    else:
        dataframe["sale_date"] = pd.Timestamp("today")

    numeric_column_names = [
        "qty",
        "quantity",
        "total",
        "selling_price",
        "cost_price",
        "current_stock",
        "profit",
        "turnover_ratio",
        "risk_score",
        "discount",
        "safety_stock",
        "reorder_point",
        "lead_time_days",
    ]
    for column_name in numeric_column_names:
        if column_name in dataframe.columns:
            dataframe[column_name] = pd.to_numeric(
                dataframe[column_name], errors="coerce"
            ).fillna(0)

    quantity_source = "qty" if "qty" in dataframe.columns else "quantity"
    dataframe["quantity"] = dataframe.get(
        quantity_source, pd.Series(0, index=dataframe.index)
    )

    if "total" in dataframe.columns:
        dataframe["revenue"] = dataframe["total"]
    elif "selling_price" in dataframe.columns:
        dataframe["revenue"] = dataframe["selling_price"] * dataframe["quantity"]
    else:
        dataframe["revenue"] = 0

    if "profit" not in dataframe.columns:
        dataframe["profit"] = (
            dataframe.get("selling_price", 0) - dataframe.get("cost_price", 0)
        ) * dataframe["quantity"]

    _cleaned_inventory_dataframe_cache = dataframe
    return dataframe


def compute_monthly_revenue_series(
    dataframe: pd.DataFrame, months_back: int = 6
) -> dict:
    if dataframe.empty or "sale_date" not in dataframe.columns:
        return {"labels": [], "values": []}

    dataframe_with_period = dataframe.copy()
    dataframe_with_period["month_period"] = dataframe_with_period[
        "sale_date"
    ].dt.to_period("M")
    monthly_totals = (
        dataframe_with_period.groupby("month_period", observed=True)["revenue"]
        .sum()
        .sort_index()
        .tail(months_back)
    )

    return {
        "labels": [str(period) for period in monthly_totals.index],
        "values": monthly_totals.tolist(),
    }
