import flet as ft
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import asyncio
from io import BytesIO
from datetime import datetime
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans

from src.app.components.theme import ThemeColor
from src.app.components.primitive_components import (
    build_vertical_spacer,
    build_section_header,
    build_info_banner,
    build_stat_card,
)

_client = MongoClient("mongodb://localhost:27017/")
_raw_db = _client["inventory"]
_clean_db = _client["inventoryai"]

CHART_BG = "#0D1120"
CHART_FG = "#A0AACB"
CHART_GRID = "#1E2640"


def _fig_to_b64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close(fig)
    return data


def _dark(ax, fig) -> None:
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=CHART_FG, labelsize=8, labelcolor=CHART_FG)
    ax.xaxis.label.set_color(CHART_FG)
    ax.yaxis.label.set_color(CHART_FG)
    for spine in ax.spines.values():
        spine.set_edgecolor(CHART_GRID)
    ax.grid(color=CHART_GRID, linewidth=0.4, alpha=0.5)
    ax.title.set_color(CHART_FG)


def _load(name: str) -> pd.DataFrame:
    data = list(_raw_db[name].find())
    return pd.DataFrame(data) if data else pd.DataFrame()


def _drop_ids(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["_id", "_id_x", "_id_y"]:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)
    return df


def _unhashable_to_str(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].astype(str)
    return df


def _safe_merge(
    left, right, on=None, left_on=None, right_on=None, prefix="x"
) -> pd.DataFrame:
    if right.empty:
        return left
    right = right.copy()
    join_cols = set()
    if on:
        join_cols.update([on] if isinstance(on, str) else on)
    if left_on:
        join_cols.add(left_on)
    if right_on:
        join_cols.add(right_on)
    rename_map = {
        c: f"{prefix}_{c}"
        for c in right.columns
        if c in left.columns and c not in join_cols
    }
    right.rename(columns=rename_map, inplace=True)
    return pd.merge(left, right, on=on, left_on=left_on, right_on=right_on, how="left")


def _generate_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["No Data"]
    df["revenue"] = df["total"]
    df["quantity"] = df["qty"]
    df["profit_margin"] = np.where(df["revenue"] == 0, 0, df["profit"] / df["revenue"])
    return [
        f"Total Revenue: ₹{round(df['revenue'].sum(), 2):,}",
        f"Total Profit: ₹{round(df['profit'].sum(), 2):,}",
        f"Units Sold: {int(df['quantity'].sum()):,}",
        f"Average Profit Margin: {round(df['profit_margin'].mean() * 100, 2)}%",
    ]


def _demand_chart(df: pd.DataFrame) -> str:
    df = df.dropna(subset=["month"])
    qty_col = next((c for c in ("qty", "quantity") if c in df.columns), None)
    fig, ax = plt.subplots(figsize=(9, 4))
    _dark(ax, fig)
    if qty_col:
        grouped = df.groupby("month", observed=True)[qty_col].sum().reset_index()
        grouped.columns = ["month", "qty"]
        ax.fill_between(
            range(len(grouped)), grouped["qty"], color="#7C6FFF", alpha=0.18
        )
        ax.plot(
            range(len(grouped)),
            grouped["qty"],
            color="#7C6FFF",
            linewidth=2.5,
            marker="o",
            markersize=4,
        )
        ax.set_xticks(range(len(grouped)))
        ax.set_xticklabels(
            grouped["month"].tolist(), rotation=35, ha="right", fontsize=7
        )
    ax.set_title("Demand Trend" if qty_col else "Demand Trend (no qty data)")
    plt.tight_layout()
    return _fig_to_b64(fig)


def _profit_chart(df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(9, 4))
    _dark(ax, fig)
    sns.histplot(df["profit"].fillna(0), bins=30, ax=ax, color="#00C9A7", alpha=0.8)
    ax.set_title("Profit Distribution")
    ax.set_xlabel("Profit", color=CHART_FG)
    ax.set_ylabel("Count", color=CHART_FG)
    ax.tick_params(axis="both", colors=CHART_FG)
    plt.tight_layout()
    return _fig_to_b64(fig)


def _correlation_chart(df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    _dark(ax, fig)
    num_df = df.select_dtypes(include=np.number).fillna(0)
    hm = sns.heatmap(
        num_df.corr(),
        ax=ax,
        cmap="coolwarm",
        linewidths=0.3,
        linecolor=CHART_GRID,
        annot=False,
    )
    ax.set_title("Correlation Heatmap")
    ax.tick_params(axis="both", colors=CHART_FG, labelcolor=CHART_FG)
    cbar = hm.collections[0].colorbar
    if cbar:
        cbar.ax.yaxis.set_tick_params(color=CHART_FG, labelcolor=CHART_FG)
        cbar.outline.set_edgecolor(CHART_GRID)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=CHART_FG)
    plt.tight_layout()
    return _fig_to_b64(fig)


def _anomaly_chart(df: pd.DataFrame) -> str:
    if "anomaly" not in df.columns:
        df = df.copy()
        df["anomaly"] = 1
    fig, ax = plt.subplots(figsize=(9, 4))
    _dark(ax, fig)
    colors = {1: "#7C6FFF", -1: "#FF4D6D"}
    for label, group in df.groupby("anomaly"):
        ax.scatter(
            group["qty"],
            group["profit"],
            c=colors.get(label, "#A0AACB"),
            label="Normal" if label == 1 else "Anomaly",
            s=18,
            alpha=0.7,
        )
    ax.legend(facecolor=CHART_BG, edgecolor=CHART_GRID, labelcolor=CHART_FG, fontsize=9)
    ax.set_title("Anomaly Detection")
    plt.tight_layout()
    return _fig_to_b64(fig)


_CHARTS = [
    (
        "Demand Chart",
        ft.Icons.SHOW_CHART,
        ThemeColor.ACCENT_VIOLET,
        _demand_chart,
        "Demand Chart",
    ),
    (
        "Profit Chart",
        ft.Icons.PAID,
        ThemeColor.ACCENT_GREEN,
        _profit_chart,
        "Profit Distribution",
    ),
    (
        "Correlation Chart",
        ft.Icons.GRID_ON,
        ThemeColor.ACCENT_AMBER,
        _correlation_chart,
        "Correlation Heatmap",
    ),
    (
        "Anomaly Chart",
        ft.Icons.BUG_REPORT,
        ThemeColor.ACCENT_ROSE,
        _anomaly_chart,
        "Anomaly Detection",
    ),
]


def _card(content: ft.Control) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=16,
        padding=22,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
    )


def _insight_row(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.LIGHTBULB_OUTLINE, color=ThemeColor.ACCENT_VIOLET, size=16
                ),
                ft.Text(text, size=13, color=ThemeColor.TEXT_SECONDARY),
            ],
            spacing=8,
        ),
        padding=ft.padding.symmetric(vertical=5),
    )


def build_data_cleaning_visualization_page(flet_page: ft.Page) -> ft.Control:

    pipeline_has_run = {"value": _clean_db.cleaned_inventory.count_documents({}) > 0}
    active_chart = {"fn": None}

    status_text = ft.Text("", size=14, color=ThemeColor.TEXT_SECONDARY)
    chart_image = ft.Image(src="", fit="contain", expand=True, visible=False)
    chart_label = ft.Text(
        "Chart Output",
        size=15,
        weight=ft.FontWeight.W_600,
        color=ThemeColor.TEXT_PRIMARY,
    )
    insights_column = ft.Column([])
    stats_row = ft.Row([], spacing=16, wrap=True)
    chart_buttons_row = ft.Row([], spacing=10, wrap=True)
    chart_output_container = ft.Container(visible=False)
    insights_container = ft.Container(visible=False)

    progress_bar = ft.ProgressBar(
        expand=True,
        value=0,
        color=ThemeColor.ACCENT_VIOLET,
        bgcolor=ft.Colors.with_opacity(0.15, ThemeColor.ACCENT_VIOLET),
        bar_height=6,
    )
    progress_pct = ft.Text(
        "0%",
        size=12,
        color=ThemeColor.ACCENT_VIOLET,
        weight=ft.FontWeight.W_700,
        width=40,
    )
    progress_step = ft.Text("Initialising…", size=12, color=ThemeColor.TEXT_MUTED)
    loading_ring = ft.ProgressRing(
        width=24, height=24, stroke_width=3, color=ThemeColor.ACCENT_VIOLET
    )

    progress_container = ft.Container(
        visible=False,
        content=ft.Column(
            [
                ft.Row(
                    [
                        loading_ring,
                        ft.Column(
                            [
                                ft.Row(
                                    [progress_bar, progress_pct],
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                progress_step,
                            ],
                            spacing=4,
                            expand=True,
                        ),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ],
            spacing=6,
        ),
        bgcolor=ft.Colors.with_opacity(0.06, ThemeColor.ACCENT_VIOLET),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ThemeColor.ACCENT_VIOLET)),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=18, vertical=14),
    )

    def _set_progress(pct: int, step: str) -> None:
        progress_bar.value = pct / 100
        progress_pct.value = f"{pct}%"
        progress_step.value = step
        progress_container.visible = True
        flet_page.update()

    def _show_chart(chart_fn, title: str) -> None:
        df = pd.DataFrame(list(_clean_db.cleaned_inventory.find({}, {"_id": 0})))
        if df.empty:
            status_text.value = "⚠ No pipeline data found — run the pipeline first."
            flet_page.update()
            return
        active_chart["fn"] = chart_fn
        b64 = chart_fn(df)
        chart_image.src = f"data:image/png;base64,{b64}"
        chart_image.visible = True
        chart_label.value = title
        chart_output_container.visible = True
        chart_output_container.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.INSERT_CHART,
                            color=ThemeColor.ACCENT_VIOLET,
                            size=18,
                        ),
                        chart_label,
                    ],
                    spacing=8,
                ),
                build_vertical_spacer(10),
                chart_image,
            ],
            spacing=0,
        )
        flet_page.update()

    def _build_chart_buttons() -> None:
        btn_style = lambda color: ft.ButtonStyle(
            color=color,
            side=ft.BorderSide(1.5, color),
            shape=ft.RoundedRectangleBorder(radius=12),
            overlay_color=ft.Colors.with_opacity(0.08, color),
        )
        chart_buttons_row.controls = [
            ft.OutlinedButton(
                label,
                icon=icon,
                height=42,
                on_click=lambda e, fn=fn, t=title: _show_chart(fn, t),
                style=btn_style(color),
            )
            for label, icon, color, fn, title in _CHARTS
        ]

    def _show_post_pipeline_ui(merged: pd.DataFrame) -> None:
        insights_column.controls = [_insight_row(i) for i in _generate_insights(merged)]
        insights_container.visible = True
        insights_container.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.ANALYTICS, color=ThemeColor.ACCENT_VIOLET, size=18
                        ),
                        ft.Text(
                            "Pipeline Insights",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=8,
                ),
                build_vertical_spacer(10),
                insights_column,
            ],
            spacing=0,
        )

        anomaly_count = (
            int((merged["anomaly"] == -1).sum()) if "anomaly" in merged.columns else 0
        )
        cluster_count = (
            merged["cluster"].nunique() if "cluster" in merged.columns else 0
        )

        stats_row.controls = [
            ft.Container(
                build_stat_card(
                    ft.Icons.TABLE_CHART,
                    "Rows Cleaned",
                    len(merged),
                    None,
                    ThemeColor.ACCENT_VIOLET,
                ),
                width=200,
            ),
            ft.Container(
                build_stat_card(
                    ft.Icons.BUG_REPORT,
                    "Anomalies",
                    anomaly_count,
                    None,
                    ThemeColor.ACCENT_ROSE,
                ),
                width=200,
            ),
            ft.Container(
                build_stat_card(
                    ft.Icons.BUBBLE_CHART,
                    "Clusters",
                    cluster_count,
                    None,
                    ThemeColor.ACCENT_TEAL,
                ),
                width=200,
            ),
            ft.Container(
                build_stat_card(
                    ft.Icons.CHECK_CIRCLE,
                    "Status",
                    "Done",
                    None,
                    ThemeColor.ACCENT_GREEN,
                ),
                width=200,
            ),
        ]

        _build_chart_buttons()
        pipeline_has_run["value"] = True
        flet_page.update()

    async def _run_pipeline_async() -> None:
        loop = asyncio.get_event_loop()

        def _step_load():
            return tuple(
                (
                    _unhashable_to_str(_load(n))
                    if n in ("products", "sales", "invoices")
                    else _load(n)
                )
                for n in (
                    "products",
                    "sales",
                    "customers",
                    "suppliers",
                    "categories",
                    "employees",
                    "invoices",
                    "purchase_orders",
                )
            )

        try:
            _set_progress(5, "Loading collections from MongoDB…")
            (
                products,
                sales,
                customers,
                suppliers,
                categories,
                employees,
                invoices,
                purchase_orders,
            ) = await loop.run_in_executor(None, _step_load)

            for df in (
                products,
                sales,
                customers,
                suppliers,
                categories,
                employees,
                invoices,
                purchase_orders,
            ):
                if not df.empty:
                    df.drop_duplicates(inplace=True)
                    for col in df.columns:
                        df[col] = df[col].fillna("Unknown")

            sales["date"] = (
                sales["date"].astype(str).fillna("unknown")
                if "date" in sales.columns
                else "unknown"
            )

            _set_progress(25, "Merging 8 collections…")

            def _step_merge():
                m = sales.copy()
                m = _safe_merge(m, products, on="product_id", prefix="prod")
                if "customer_id" in m.columns and not customers.empty:
                    m = _safe_merge(m, customers, on="customer_id", prefix="cust")
                if "supplier_id" in m.columns and not suppliers.empty:
                    m = _safe_merge(m, suppliers, on="supplier_id", prefix="sup")
                if (
                    "employee_id" in m.columns
                    and not employees.empty
                    and "employee_id" in employees.columns
                ):
                    m = _safe_merge(m, employees, on="employee_id", prefix="emp")
                if "category_id" in m.columns and not categories.empty:
                    m = _safe_merge(
                        m,
                        categories,
                        left_on="category_id",
                        right_on="_id",
                        prefix="cat",
                    )
                if "invoice_id" in m.columns and not invoices.empty:
                    m = _safe_merge(m, invoices, on="invoice_id", prefix="inv")
                if not purchase_orders.empty:
                    m = _safe_merge(m, purchase_orders, on="product_id", prefix="po")
                return m

            merged = await loop.run_in_executor(None, _step_merge)

            if "date" in merged.columns:
                merged["date"] = merged["date"].astype(str).fillna("unknown")
                merged["month"] = merged["date"].str[:7]
            else:
                merged["month"] = "unknown"

            if "qty" not in merged.columns:
                merged["qty"] = (
                    merged["quantity"] if "quantity" in merged.columns else 0
                )
            for col in ("selling_price", "cost_price", "qty", "total"):
                if col not in merged:
                    merged[col] = 0
                merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
            merged["profit"] = (
                merged["selling_price"] - merged["cost_price"]
            ) * merged["qty"]

            _set_progress(55, "Running IsolationForest anomaly detection…")
            matrix = merged[["qty", "total", "profit"]].fillna(0)

            def _step_anomaly(m):
                return (
                    IsolationForest(contamination=0.05, random_state=42).fit_predict(m)
                    if len(m) > 10
                    else np.ones(len(m), dtype=int)
                )

            merged["anomaly"] = await loop.run_in_executor(None, _step_anomaly, matrix)

            _set_progress(70, "Clustering with KMeans…")

            def _step_cluster(m):
                try:
                    return KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(
                        m
                    )
                except Exception:
                    return np.zeros(len(m), dtype=int)

            merged["cluster"] = await loop.run_in_executor(None, _step_cluster, matrix)

            _set_progress(85, "Saving to inventoryai.cleaned_inventory…")

            def _step_save(m):
                m["run_timestamp"] = str(datetime.now())
                _clean_db.cleaned_inventory.delete_many({})
                m2 = _drop_ids(m.copy()).replace({np.nan: None})
                _clean_db.cleaned_inventory.insert_many(m2.to_dict("records"))

            await loop.run_in_executor(None, _step_save, merged)

            _set_progress(95, "Generating charts…")
            _show_post_pipeline_ui(merged)
            _set_progress(100, "Pipeline complete!")
            status_text.value = f"Pipeline complete, {len(merged)} records processed."
            progress_container.visible = False
            flet_page.update()
            _show_chart(_demand_chart, "Demand Chart")

        except Exception as err:
            import traceback

            traceback.print_exc()
            progress_container.visible = False
            status_text.value = f"Pipeline error: {err}"
            flet_page.update()

    def _handle_run(e) -> None:
        progress_container.visible = True
        progress_bar.value = 0.03
        progress_pct.value = "0%"
        progress_step.value = "Starting pipeline…"
        status_text.value = "Running pipeline…"
        flet_page.update()
        flet_page.run_task(_run_pipeline_async)

    if pipeline_has_run["value"]:
        _build_chart_buttons()
        df_existing = pd.DataFrame(
            list(_clean_db.cleaned_inventory.find({}, {"_id": 0}).limit(5000))
        )
        if not df_existing.empty:
            try:
                _show_post_pipeline_ui(df_existing)
            except Exception:
                pass
        try:
            _show_chart(_demand_chart, "Demand Chart")
        except Exception:
            pass

    chart_card_wrapper = (
        _card(chart_output_container)
        if pipeline_has_run["value"]
        else ft.Container(
            content=chart_output_container,
            bgcolor=ThemeColor.CARD_BACKGROUND,
            border_radius=16,
            padding=22,
            border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        )
    )

    return ft.Column(
        [
            build_section_header(
                "Data Cleaning & Visualisation",
                "AI pipeline: merge → clean → anomaly detect → cluster",
            ),
            build_vertical_spacer(14),
            build_info_banner(
                ft.Icons.CLEANING_SERVICES,
                "AI Data Pipeline",
                "Merges 8 collections · IsolationForest · KMeans · Saves to inventoryai.cleaned_inventory",
                ThemeColor.ACCENT_VIOLET,
                ft.FilledButton(
                    "Run Full AI Pipeline",
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=_handle_run,
                    height=44,
                    style=ft.ButtonStyle(
                        bgcolor=ThemeColor.ACCENT_VIOLET,
                        color=ThemeColor.TEXT_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                ),
            ),
            build_vertical_spacer(14),
            progress_container,
            build_vertical_spacer(6),
            ft.Row([status_text]),
            build_vertical_spacer(10),
            stats_row,
            build_vertical_spacer(10) if stats_row.controls else ft.Container(),
            chart_buttons_row,
            build_vertical_spacer(14),
            chart_card_wrapper,
            build_vertical_spacer(14),
            _card(insights_container),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
