import flet as ft
import asyncio
import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_absolute_percentage_error
from datetime import datetime

from src.app.components.theme import ThemeColor
from src.app.components.primitive_components import (
    build_vertical_spacer,
    build_section_header,
    build_icon_box,
    build_loading_container,
)
from src.app.components import build_dialog_dropdown

_client = MongoClient("mongodb://localhost:27017/")
_collection = _client["inventoryai"]["cleaned_inventory"]
_anomaly_col = _client["inventoryai"]["anomalies"]


def _load_clean_data() -> pd.DataFrame:
    rows = list(_collection.find({}, {"_id": 0}))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "date" in df.columns:
        df["sale_date"] = pd.to_datetime(df["date"], errors="coerce")
    elif "order_date" in df.columns:
        df["sale_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    for c in (
        "quantity",
        "total",
        "discount",
        "current_stock",
        "safety_stock",
        "reorder_point",
        "turnover_ratio",
        "lead_time_days",
        "profit",
        "cost_price",
        "selling_price",
        "risk_score",
    ):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


class RiskEngine:
    @staticmethod
    def safe(v):
        return 0 if (v is None or pd.isna(v) or np.isinf(v)) else float(v)

    @staticmethod
    def _label(score: int) -> tuple[str, str]:
        if score > 70:
            return "High", ThemeColor.ACCENT_ROSE
        if score > 40:
            return "Medium", ThemeColor.ACCENT_AMBER
        return "Low", ThemeColor.ACCENT_GREEN

    @staticmethod
    def stockout_risk(stock, demand, safety, reorder):
        score = min(max(int((demand - stock + reorder - safety) * 2), 0), 100)
        return *RiskEngine._label(score), score

    @staticmethod
    def overstock_risk(stock, demand):
        score = min(int(stock / max(demand, 1) * 25), 100)
        return *RiskEngine._label(score), score

    @staticmethod
    def profit_risk(profit, revenue):
        margin = profit / max(revenue, 1)
        score = 100 - min(int(margin * 100), 100)
        return *RiskEngine._label(score), score

    @staticmethod
    def supplier_risk(lead):
        score = min(int(lead * 5), 100)
        return *RiskEngine._label(score), score

    @staticmethod
    def discount_risk(disc):
        score = min(int(disc * 4), 100)
        return *RiskEngine._label(score), score

    @staticmethod
    def anomaly_detection(hist: list) -> list:
        if len(hist) < 10:
            return []
        pred = IsolationForest(contamination=0.08, random_state=42).fit_predict(
            np.array(hist).reshape(-1, 1)
        )
        return [i for i, p in enumerate(pred) if p == -1]

    @staticmethod
    def forecast_accuracy(vals: list):
        if len(vals) < 5:
            return None
        arr = np.array(vals)
        pred = np.roll(arr, 1)
        pred[0] = arr.mean()
        return round((1 - mean_absolute_percentage_error(arr, pred)) * 100, 2)


def _save_anomaly(product_id: str, qty: float, row: dict) -> None:
    _anomaly_col.insert_one(
        {
            "product_id": product_id,
            "quantity": float(qty),
            "invoice_number": row.get("invoice_number"),
            "sale_date": row.get("sale_date"),
            "detected_at": datetime.utcnow(),
            "message": "Demand anomaly detected",
        }
    )


def _shimmer_bar(height: int = 16, expand: bool = True) -> ft.Container:
    return ft.Container(
        height=height,
        border_radius=6,
        expand=expand,
        content=ft.ProgressBar(
            value=None,
            color=ft.Colors.with_opacity(0.35, ThemeColor.ACCENT_VIOLET),
            bgcolor=ft.Colors.with_opacity(0.10, ThemeColor.ACCENT_VIOLET),
            bar_height=height,
            border_radius=ft.border_radius.all(6),
        ),
    )


def _shimmer_risk_card() -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=38,
                            height=38,
                            border_radius=10,
                            bgcolor=ft.Colors.with_opacity(
                                0.12, ThemeColor.ACCENT_VIOLET
                            ),
                            content=ft.ProgressBar(
                                value=None,
                                color=ft.Colors.with_opacity(
                                    0.3, ThemeColor.ACCENT_VIOLET
                                ),
                                bgcolor="transparent",
                                bar_height=38,
                            ),
                        ),
                        ft.Column(
                            [
                                _shimmer_bar(14),
                                build_vertical_spacer(6),
                                _shimmer_bar(10),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                ),
                build_vertical_spacer(14),
                _shimmer_bar(10),
                build_vertical_spacer(6),
                _shimmer_bar(8),
            ],
            spacing=0,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=14,
        padding=18,
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, ThemeColor.ACCENT_VIOLET)),
        expand=True,
    )


def _shimmer_summary_row() -> ft.Container:
    _dot = lambda w, h: ft.Container(
        width=w,
        height=h,
        border_radius=min(w, h) // 2,
        bgcolor=ft.Colors.with_opacity(0.10, ThemeColor.ACCENT_VIOLET),
    )
    return ft.Container(
        content=ft.Row(
            [
                _dot(32, 32),
                _dot(140, 12),
                ft.Container(expand=True),
                _dot(100, 12),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.03, ThemeColor.TEXT_PRIMARY),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )


def _build_risk_card(
    title: str, label: str, color: str, score: int, icon: str
) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        build_icon_box(icon, color, 18, 10, 10),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=14,
                                    color=ThemeColor.TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Row(
                                    [
                                        ft.Text(
                                            label,
                                            size=12,
                                            color=color,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        ft.Container(
                                            width=8,
                                            height=8,
                                            bgcolor=color,
                                            border_radius=4,
                                        ),
                                    ],
                                    spacing=6,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                build_vertical_spacer(12),
                ft.ProgressBar(
                    value=score / 100,
                    color=color,
                    bgcolor=ft.Colors.with_opacity(0.15, color),
                    bar_height=9,
                    border_radius=ft.border_radius.all(6),
                    expand=True,
                ),
                build_vertical_spacer(6),
                ft.Text(f"{score}% risk", size=11, color=ThemeColor.TEXT_MUTED),
            ],
            spacing=0,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=14,
        padding=18,
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, color)),
        expand=True,
    )


def _icon_chip(icon, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Icon(icon, color=color, size=16),
        bgcolor=ft.Colors.with_opacity(0.12, color),
        border_radius=8,
        padding=6,
        width=32,
        height=32,
        alignment=ft.alignment.Alignment(0, 0),
    )


def _summary_row(
    icon,
    icon_color: str,
    label: str,
    value: str,
    val_color: str = ThemeColor.TEXT_PRIMARY,
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                _icon_chip(icon, icon_color),
                ft.Text(label, size=14, color=ThemeColor.TEXT_MUTED, width=160),
                ft.Text(value, size=14, color=val_color, weight=ft.FontWeight.W_600),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.03, ThemeColor.TEXT_PRIMARY),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )


def _build_summary_card(
    acc,
    stock,
    safety,
    demand,
    r1_label,
    r1_color,
    r2_label,
    r2_color,
    anomaly_count: int,
) -> ft.Container:
    stock_ok = stock >= safety
    demand_high = demand > stock

    acc_color = (
        ThemeColor.ACCENT_VIOLET if acc and acc > 50 else ThemeColor.ACCENT_AMBER
    )
    rows = [
        _summary_row(
            ft.Icons.TRACK_CHANGES,
            ThemeColor.ACCENT_VIOLET,
            "Forecast Accuracy",
            f"{acc}%" if acc is not None else "N/A",
            acc_color,
        ),
        _summary_row(
            ft.Icons.INVENTORY_2,
            ThemeColor.ACCENT_GREEN if stock_ok else ThemeColor.ACCENT_ROSE,
            "Stock Status",
            "OK — Sufficient stock" if stock_ok else "Critical — Below safety level",
            ThemeColor.ACCENT_GREEN if stock_ok else ThemeColor.ACCENT_ROSE,
        ),
        _summary_row(
            ft.Icons.TRENDING_UP if demand_high else ft.Icons.SHOW_CHART,
            ThemeColor.ACCENT_AMBER if demand_high else ThemeColor.ACCENT_TEAL,
            "Demand Trend",
            "High — Demand exceeds stock" if demand_high else "Stable",
            ThemeColor.ACCENT_AMBER if demand_high else ThemeColor.ACCENT_TEAL,
        ),
        _summary_row(ft.Icons.SHIELD, r1_color, "Stockout Risk", r1_label, r1_color),
        _summary_row(
            ft.Icons.WAREHOUSE, r2_color, "Overstock Risk", r2_label, r2_color
        ),
        _summary_row(
            ft.Icons.REPORT_PROBLEM,
            ThemeColor.ACCENT_ROSE if anomaly_count > 0 else ThemeColor.ACCENT_GREEN,
            "Anomalies Detected",
            str(anomaly_count),
            ThemeColor.ACCENT_ROSE if anomaly_count > 0 else ThemeColor.ACCENT_GREEN,
        ),
    ]

    if demand_high:
        act_icon, act_color = ft.Icons.ADD_SHOPPING_CART, ThemeColor.ACCENT_ROSE
        act_text = "Increase stock immediately to meet demand"
    elif not stock_ok:
        act_icon, act_color = ft.Icons.WARNING_AMBER, ThemeColor.ACCENT_AMBER
        act_text = "Reorder soon — below safety stock level"
    else:
        act_icon, act_color = ft.Icons.CHECK_CIRCLE, ThemeColor.ACCENT_GREEN
        act_text = "Optimize inventory — stock levels healthy"

    action_row = ft.Container(
        content=ft.Row(
            [
                ft.Icon(act_icon, color=act_color, size=22),
                ft.Column(
                    [
                        ft.Text(
                            "Recommended Action", size=11, color=ThemeColor.TEXT_MUTED
                        ),
                        ft.Text(
                            act_text,
                            size=14,
                            color=act_color,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.10, act_color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.25, act_color)),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.PSYCHOLOGY, color=ThemeColor.ACCENT_VIOLET, size=22
                        ),
                        ft.Text(
                            "AI Summary",
                            size=16,
                            weight=ft.FontWeight.W_700,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=10,
                ),
                build_vertical_spacer(14),
                ft.Column(rows, spacing=8),
                build_vertical_spacer(12),
                action_row,
            ],
            spacing=0,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=14,
        padding=20,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        expand=True,
    )


def _anomaly_card(qty, sale_date, invoice, is_spike: bool) -> ft.Container:
    color = ThemeColor.ACCENT_ROSE
    reason = (
        "Demand spike — unusually high sales"
        if is_spike
        else "Demand drop — unusually low sales"
    )
    action = "Increase stock to meet demand" if is_spike else "Reduce reorder quantity"

    def _meta(icon, text: str) -> list:
        return [
            ft.Icon(icon, color=ThemeColor.TEXT_MUTED, size=13),
            ft.Text(text, size=12, color=ThemeColor.TEXT_SECONDARY),
        ]

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.REPORT_PROBLEM, color=color, size=20),
                    bgcolor=ft.Colors.with_opacity(0.12, color),
                    border_radius=8,
                    padding=8,
                    width=36,
                    height=36,
                    alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Column(
                    [
                        ft.Text(
                            "Anomaly Detected",
                            size=14,
                            color=ThemeColor.TEXT_PRIMARY,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Row(
                            [
                                *_meta(ft.Icons.NUMBERS, f"Quantity: {qty}"),
                                *_meta(ft.Icons.CALENDAR_TODAY, str(sale_date)[:10]),
                                *_meta(ft.Icons.RECEIPT, str(invoice)),
                            ],
                            spacing=6,
                            wrap=True,
                        ),
                        ft.Row(
                            [
                                *_meta(ft.Icons.INFO_OUTLINE, reason),
                                ft.Icon(ft.Icons.ARROW_FORWARD, color=color, size=13),
                                ft.Text(
                                    action,
                                    size=12,
                                    color=color,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=6,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=ft.Colors.with_opacity(0.07, color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, color)),
        border_radius=12,
        padding=14,
    )


def build_risk_page(flet_page: ft.Page) -> ft.Control:

    df = _load_clean_data()

    risk_cards_row = ft.ResponsiveRow([])
    anomaly_column = ft.Column([], spacing=10)
    summary_container = ft.Container(visible=False)
    results_column = ft.Column(
        [
            risk_cards_row,
            build_vertical_spacer(16),
            summary_container,
            build_vertical_spacer(14),
            anomaly_column,
        ],
        spacing=0,
        visible=False,
    )

    if df.empty:
        return ft.Column(
            [
                build_section_header(
                    "AI Risk Intelligence",
                    "Stockout · Overstock · Profit · Supplier · Discount",
                ),
                build_vertical_spacer(20),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.WARNING_AMBER,
                                color=ThemeColor.ACCENT_AMBER,
                                size=20,
                            ),
                            ft.Text(
                                "No cleaned data found. Run the Data Cleaning pipeline first.",
                                size=14,
                                color=ThemeColor.ACCENT_AMBER,
                            ),
                        ],
                        spacing=10,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.08, ThemeColor.ACCENT_AMBER),
                    border=ft.border.all(
                        1, ft.Colors.with_opacity(0.25, ThemeColor.ACCENT_AMBER)
                    ),
                    border_radius=12,
                    padding=16,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
        )

    product_dropdown = build_dialog_dropdown(
        "Select Product",
        [ft.DropdownOption(p) for p in sorted(df["product_id"].unique())],
        width=320,
    )

    analyze_btn = ft.FilledButton(
        "Analyze",
        icon=ft.Icons.ANALYTICS,
        height=56,
        # disabled=True,          # enabled only once a product is selected
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

    loading_container = build_loading_container("Analysing product risks…")
    loading_bar = loading_container._loading_bar
    loading_ring = loading_container._loading_ring

    def _on_product_change(e) -> None:
        analyze_btn.disabled = not bool(product_dropdown.value)
        flet_page.update()

    product_dropdown.on_change = _on_product_change

    def _show_shimmer_state() -> None:
        risk_cards_row.controls = [
            ft.Column([_shimmer_risk_card()], col={"xs": 12, "sm": 6, "md": 4})
            for _ in range(5)
        ]
        summary_container.visible = True
        summary_container.content = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=22,
                                height=22,
                                border_radius=11,
                                bgcolor=ft.Colors.with_opacity(
                                    0.15, ThemeColor.ACCENT_VIOLET
                                ),
                            ),
                            ft.Container(
                                width=120,
                                height=14,
                                border_radius=6,
                                bgcolor=ft.Colors.with_opacity(
                                    0.15, ThemeColor.ACCENT_VIOLET
                                ),
                            ),
                        ],
                        spacing=10,
                    ),
                    build_vertical_spacer(14),
                    *[_shimmer_summary_row() for _ in range(6)],
                    build_vertical_spacer(12),
                    ft.Container(
                        height=52,
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.08, ThemeColor.ACCENT_VIOLET),
                        content=ft.ProgressBar(
                            value=None,
                            color=ft.Colors.with_opacity(
                                0.25, ThemeColor.ACCENT_VIOLET
                            ),
                            bgcolor="transparent",
                            bar_height=52,
                        ),
                    ),
                ],
                spacing=8,
            ),
            bgcolor=ThemeColor.CARD_BACKGROUND,
            border_radius=14,
            padding=20,
            border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
            expand=True,
        )
        results_column.visible = True
        flet_page.update()

    def _run_analysis():
        pid = product_dropdown.value
        if not pid:
            return None
        product_df = df[df["product_id"] == pid]
        if product_df.empty:
            return None
        latest = product_df.iloc[-1]
        s = RiskEngine.safe
        stock = s(latest.get("current_stock", 0))
        safety = s(latest.get("safety_stock", 0))
        reorder = s(latest.get("reorder_point", 0))
        demand = s(latest.get("quantity", 0))
        disc = s(latest.get("discount", 0))
        lead = s(latest.get("lead_time_days", 0))
        profit = s(latest.get("profit", 0))
        revenue = s(latest.get("total", 0))
        hist = product_df["quantity"].tolist()

        r1 = RiskEngine.stockout_risk(stock, demand, safety, reorder)
        r2 = RiskEngine.overstock_risk(stock, demand)
        r3 = RiskEngine.profit_risk(profit, revenue)
        r4 = RiskEngine.supplier_risk(lead)
        r5 = RiskEngine.discount_risk(disc)
        anomalies = RiskEngine.anomaly_detection(hist)
        acc = RiskEngine.forecast_accuracy(hist)
        avg_demand = float(np.mean(hist)) if hist else 0.0

        for idx in anomalies:
            row = product_df.iloc[idx]
            _save_anomaly(pid, row.get("quantity", 0), row)

        return dict(
            stock=stock,
            safety=safety,
            demand=demand,
            r1=r1,
            r2=r2,
            r3=r3,
            r4=r4,
            r5=r5,
            anomalies=anomalies,
            acc=acc,
            avg_demand=avg_demand,
            product_df=product_df,
        )

    def _apply_results(result: dict | None) -> None:
        if result is None:
            loading_container.visible = False
            flet_page.update()
            return

        r1, r2 = result["r1"], result["r2"]

        risk_cards_row.controls = [
            ft.Column(
                [_build_risk_card("Stockout", *r1, ft.Icons.WARNING)],
                col={"xs": 12, "sm": 6, "md": 4},
            ),
            ft.Column(
                [_build_risk_card("Overstock", *r2, ft.Icons.INVENTORY)],
                col={"xs": 12, "sm": 6, "md": 4},
            ),
            ft.Column(
                [_build_risk_card("Profit", *result["r3"], ft.Icons.PAID)],
                col={"xs": 12, "sm": 6, "md": 4},
            ),
            ft.Column(
                [_build_risk_card("Supplier", *result["r4"], ft.Icons.LOCAL_SHIPPING)],
                col={"xs": 12, "sm": 6, "md": 4},
            ),
            ft.Column(
                [_build_risk_card("Discount", *result["r5"], ft.Icons.PERCENT)],
                col={"xs": 12, "sm": 6, "md": 4},
            ),
        ]

        summary_container.visible = True
        summary_container.content = _build_summary_card(
            result["acc"],
            result["stock"],
            result["safety"],
            result["demand"],
            r1[0],
            r1[1],
            r2[0],
            r2[1],
            len(result["anomalies"]),
        )

        product_df = result["product_df"]
        avg_demand = result["avg_demand"]
        anomaly_column.controls = [
            _anomaly_card(
                product_df.iloc[idx].get("quantity", 0),
                product_df.iloc[idx].get("sale_date", "Unknown"),
                product_df.iloc[idx].get("invoice_number", "N/A"),
                product_df.iloc[idx].get("quantity", 0) > avg_demand,
            )
            for idx in result["anomalies"]
        ]

        results_column.visible = True
        loading_container.visible = False
        flet_page.update()

    async def _handle_analyze_async() -> None:
        results_column.visible = False
        loading_container.visible = True
        flet_page.update()
        _show_shimmer_state()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_analysis)
        loading_container.visible = False
        _apply_results(result)

    def _handle_analyze(e) -> None:
        if not product_dropdown.value:
            return
        flet_page.run_task(_handle_analyze_async)

    analyze_btn.on_click = _handle_analyze

    return ft.Column(
        [
            build_section_header(
                "AI Risk Intelligence",
                "Stockout · Overstock · Profit · Supplier · Discount",
            ),
            build_vertical_spacer(18),
            ft.Container(
                content=ft.Row(
                    [product_dropdown, analyze_btn],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ThemeColor.CARD_BACKGROUND,
                border_radius=14,
                padding=20,
                border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
            ),
            build_vertical_spacer(12),
            loading_container,
            build_vertical_spacer(8),
            results_column,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
