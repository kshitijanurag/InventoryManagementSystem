import flet as ft
import asyncio
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
from io import BytesIO

from sklearn.metrics import mean_absolute_percentage_error
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
from prophet import Prophet
from pymongo import MongoClient

from src.app.components.theme import ThemeColor
from src.app.components.primitive_components import (
    build_vertical_spacer,
    build_section_header,
    build_info_banner,
)
from src.app.components import build_dialog_dropdown, build_loading_container

_client = MongoClient("mongodb://localhost:27017/")
_collection = _client["inventoryai"]["cleaned_inventory"]

CHART_BG = "#0D1120"
CHART_FG = "#A0AACB"
CHART_GRID = "#1E2640"

_FEATURES = [
    "lag_1",
    "lag_7",
    "rolling_7",
    "rolling_30",
    "discount",
    "current_stock",
    "profit",
    "turnover_ratio",
    "risk_score",
]


def _fig_to_b64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    buf.seek(0)
    enc = base64.b64encode(buf.read()).decode()
    buf.close()
    plt.close(fig)
    return enc


def _load_product_data(product_id: str) -> pd.DataFrame:
    rows = list(_collection.find({"product_id": product_id}, {"_id": 0}))
    if not rows:
        prod = _client["inventory"]["products"].find_one({"product_id": product_id})
        if prod:
            import random as _rnd

            _rnd.seed(42)
            rows = [
                {
                    "product_id": product_id,
                    "date": f"2025-{m:02d}-01",
                    "quantity": _rnd.randint(5, 50),
                    "selling_price": float(prod.get("selling_price", 100)),
                    "discount": _rnd.uniform(0, 15),
                    "current_stock": int(prod.get("current_stock", 10)),
                    "profit": _rnd.uniform(10, 200),
                    "turnover_ratio": _rnd.uniform(0.5, 5.0),
                    "risk_score": _rnd.randint(0, 100),
                }
                for m in range(1, 25)
            ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    date_col = next(
        (c for c in ("date", "order_date", "created_at") if c in df.columns), None
    )
    df["sale_date"] = (
        pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT
    )
    df = df.sort_values("sale_date")
    for col in (
        "quantity",
        "discount",
        "current_stock",
        "profit",
        "turnover_ratio",
        "risk_score",
    ):
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)
    df["lag_1"] = df["quantity"].shift(1)
    df["lag_7"] = df["quantity"].shift(7)
    df["rolling_7"] = df["quantity"].rolling(7).mean()
    df["rolling_30"] = df["quantity"].rolling(30).mean()
    df.fillna(0, inplace=True)
    return df


def _tree_model(df: pd.DataFrame, days: int, model) -> tuple[list, float]:
    X, y = df[_FEATURES], df["quantity"]
    split = max(int(len(df) * 0.8), 1)
    model.fit(X[:split], y[:split])
    preds = model.predict(X[split:])
    mape = mean_absolute_percentage_error(y[split:], preds) if len(preds) > 0 else 0
    row = X.iloc[-1:].copy()
    output: list[float] = []
    for _ in range(days):
        p = model.predict(row)[0]
        output.append(p)
        row["lag_1"] = p
        row["rolling_7"] = np.mean(output[-7:])
    return output, mape


def _rf_model(df: pd.DataFrame, days: int) -> tuple[list, float]:
    return _tree_model(
        df, days, RandomForestRegressor(n_estimators=400, random_state=42)
    )


def _xgb_model(df: pd.DataFrame, days: int) -> tuple[list, float]:
    return _tree_model(df, days, xgb.XGBRegressor(n_estimators=300, learning_rate=0.05))


def _prophet_model(df: pd.DataFrame, days: int) -> tuple[list, float]:
    p_df = (
        df[["sale_date", "quantity"]]
        .dropna()
        .rename(columns={"sale_date": "ds", "quantity": "y"})
    )
    model = Prophet()
    model.fit(p_df)
    future = model.make_future_dataframe(periods=days)
    forecast = model.predict(future)
    yhat = forecast["yhat"].values[-days:]
    mape = mean_absolute_percentage_error(p_df["y"], forecast["yhat"][: len(p_df)])
    return list(yhat), mape


def _build_chart(fc: list, days: int, model_name: str) -> str:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.plot(fc, color="#7C6FFF", linewidth=2.5, marker="o", markersize=3)
    ax.fill_between(range(len(fc)), fc, alpha=0.15, color="#7C6FFF")
    ax.set_title(
        f"{model_name} — {days}-Day Demand Forecast",
        color=CHART_FG,
        fontsize=11,
        pad=10,
    )
    ax.tick_params(colors=CHART_FG, labelsize=9)
    for s in ax.spines.values():
        s.set_edgecolor(CHART_GRID)
    ax.grid(color=CHART_GRID, linewidth=0.5, alpha=0.6)
    plt.tight_layout()
    return _fig_to_b64(fig)


def _shimmer_bar(width: int = 200, height: int = 20) -> ft.Container:
    return ft.Container(
        width=width,
        height=height,
        border_radius=6,
        content=ft.ProgressBar(
            value=None,
            color=ft.Colors.with_opacity(0.35, ThemeColor.ACCENT_VIOLET),
            bgcolor=ft.Colors.with_opacity(0.10, ThemeColor.ACCENT_VIOLET),
            bar_height=height,
            border_radius=ft.border_radius.all(6),
        ),
    )


def _stat_card(label: str, value: str | None, color: str) -> ft.Container:
    body = (
        ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=color)
        if value is not None
        else _shimmer_bar(120, 32)
    )
    border_color = (
        ThemeColor.BORDER_DEFAULT
        if value is not None
        else ft.Colors.with_opacity(0.4, ThemeColor.ACCENT_VIOLET)
    )
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(label, size=13, color=ThemeColor.TEXT_MUTED),
                build_vertical_spacer(6 if value is not None else 10),
                body,
            ],
            spacing=0,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=14,
        padding=20,
        border=ft.border.all(1, border_color),
        expand=True,
    )


def _results_section_content(stat_row, insight_text, chart_box) -> ft.Column:
    return ft.Column(
        [
            stat_row,
            build_vertical_spacer(18),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.SHOW_CHART,
                                    color=ThemeColor.ACCENT_VIOLET,
                                    size=18,
                                ),
                                ft.Text(
                                    "Forecast Chart",
                                    size=15,
                                    weight=ft.FontWeight.W_600,
                                    color=ThemeColor.TEXT_PRIMARY,
                                ),
                            ],
                            spacing=8,
                        ),
                        build_vertical_spacer(10),
                        insight_text,
                        build_vertical_spacer(10),
                        chart_box,
                    ],
                    spacing=0,
                ),
                bgcolor=ThemeColor.CARD_BACKGROUND,
                border_radius=16,
                padding=22,
                border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
            ),
        ],
        spacing=0,
    )


def build_forecast_page(flet_page: ft.Page) -> ft.Control:

    product_ids = _collection.distinct("product_id")
    if not product_ids:
        product_ids = [
            p["product_id"]
            for p in _client["inventory"]["products"]
            .find({}, {"product_id": 1, "_id": 0})
            .limit(100)
        ]

    model_dd = build_dialog_dropdown(
        "Model",
        [ft.DropdownOption(m) for m in ["RandomForest", "XGBoost", "Prophet"]],
        value="RandomForest",
        width=200,
    )
    days_dd = build_dialog_dropdown(
        "Forecast Days",
        [ft.DropdownOption(d) for d in ["7", "30", "90"]],
        value="30",
        width=160,
    )

    run_btn = ft.FilledButton(
        "Run Forecast",
        icon=ft.Icons.PLAY_ARROW,
        disabled=True,
        height=48,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DISABLED: ft.Colors.with_opacity(
                    0.35, ThemeColor.ACCENT_VIOLET
                ),
                ft.ControlState.DEFAULT: ThemeColor.ACCENT_VIOLET,
            },
            color=ThemeColor.TEXT_PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )

    def _on_product_change(e) -> None:
        run_btn.disabled = not bool(e.data)
        run_btn.update()

    product_dd = build_dialog_dropdown(
        "Product",
        [ft.DropdownOption(p) for p in product_ids],
        width=270,
        on_select=_on_product_change,
    )

    for _dd in (product_dd, model_dd, days_dd):
        _dd.helper_text = None

    loading_container = build_loading_container("Running forecast model…")
    loading_bar = loading_container._loading_bar
    loading_ring = loading_container._loading_ring
    loading_step = loading_container._loading_label

    stat_row = ft.Row([], spacing=14)
    insight_text = ft.Text("", size=14, color=ThemeColor.TEXT_SECONDARY)
    chart_box = ft.Container(height=320)
    results_section = ft.Container(visible=False)

    def _show_shimmer() -> None:
        stat_row.controls = [
            _stat_card("Expected Demand", None, ThemeColor.ACCENT_VIOLET),
            _stat_card("Recommended Stock", None, ThemeColor.ACCENT_TEAL),
            _stat_card("Model Confidence", None, ThemeColor.ACCENT_GREEN),
            _stat_card("Expected Revenue", None, ThemeColor.ACCENT_GREEN),
        ]
        chart_box.content = ft.Container(
            height=280,
            content=ft.Column(
                [
                    _shimmer_bar(300, 18),
                    build_vertical_spacer(12),
                    _shimmer_bar(500, 200),
                ],
                spacing=0,
            ),
        )
        insight_text.value = ""
        results_section.content = _results_section_content(
            stat_row, insight_text, chart_box
        )
        results_section.visible = True
        flet_page.update()

    def _show_results(
        total, recommended, confidence_pct, revenue, chart_b64, insight_str
    ) -> None:
        conf_color = (
            ThemeColor.ACCENT_GREEN if confidence_pct >= 70 else ThemeColor.ACCENT_AMBER
        )
        stat_row.controls = [
            _stat_card("Expected Demand", str(total), ThemeColor.ACCENT_VIOLET),
            _stat_card("Recommended Stock", str(recommended), ThemeColor.ACCENT_TEAL),
            _stat_card("Model Confidence", f"{confidence_pct:.1f}%", conf_color),
            _stat_card("Expected Revenue", f"₹{revenue:,}", ThemeColor.ACCENT_GREEN),
        ]
        chart_box.content = ft.Image(
            src=f"data:image/png;base64,{chart_b64}",
            fit="contain",
            expand=True,
        )
        insight_text.value = insight_str
        flet_page.update()

    def _compute(product_id: str, model_name: str, days: int):
        df = _load_product_data(product_id)
        if df.empty:
            return None, "No data found for this product."
        try:
            if model_name == "RandomForest":
                fc, mape = _rf_model(df, days)
            elif model_name == "XGBoost":
                fc, mape = _xgb_model(df, days)
            else:
                fc, mape = _prophet_model(df, days)

            total = int(sum(fc))
            price = (
                float(df["selling_price"].iloc[-1])
                if "selling_price" in df.columns
                else 1000.0
            )
            revenue = int(total * price)
            conf = max(0.0, (1 - mape) * 100)
            rec = int(total * 1.2)
            trend = "increasing" if fc[-1] > fc[0] else "stable or decreasing"
            insight = (
                f"Forecast: {total} units over {days} days.  "
                f"Trend: {trend}.  "
                f"Recommended stock: {rec} units.  "
                f"Revenue estimate: ₹{revenue:,}."
            )
            return (
                total,
                rec,
                conf,
                revenue,
                _build_chart(fc, days, model_name),
                insight,
            ), None
        except Exception as err:
            return None, f"Model error: {err}"

    async def _run_async() -> None:
        product_id = product_dd.value
        model_name = model_dd.value or "RandomForest"
        days = int(days_dd.value or 30)

        if not product_id:
            product_dd.error_text = "Please select a product"
            flet_page.update()
            return
        product_dd.error_text = None

        loading_container.visible = True
        loading_step.value = f"Running {model_name} model for {days} days…"
        run_btn.disabled = True
        flet_page.update()
        _show_shimmer()

        loop = asyncio.get_event_loop()
        result, error = await loop.run_in_executor(
            None, _compute, product_id, model_name, days
        )

        loading_container.visible = False
        run_btn.disabled = not bool(product_dd.value)
        if error:
            insight_text.value = f"Error: {error}"
            flet_page.update()
        else:
            _show_results(*result)

    run_btn.on_click = lambda e: flet_page.run_task(_run_async)

    return ft.Column(
        [
            build_section_header(
                "AI Demand Forecast", "RandomForest · XGBoost · Prophet"
            ),
            build_vertical_spacer(14),
            build_info_banner(
                ft.Icons.AUTO_AWESOME,
                "Neural Forecast Engine",
                "Select a product and model, then click Run Forecast to generate AI predictions.",
                ThemeColor.ACCENT_VIOLET,
            ),
            build_vertical_spacer(18),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                product_dd,
                                model_dd,
                                days_dd,
                                run_btn,
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        build_vertical_spacer(12),
                        loading_container,
                    ],
                    spacing=0,
                ),
                bgcolor=ThemeColor.CARD_BACKGROUND,
                border_radius=14,
                padding=ft.padding.symmetric(horizontal=20, vertical=16),
                border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
            ),
            build_vertical_spacer(18),
            results_section,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )
