import flet as ft
import flet_datatable2 as ftd
import asyncio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
import statistics
from io import BytesIO
from datetime import datetime
from pymongo import MongoClient

from src.app.components import (
    build_vertical_spacer,
    build_section_header,
    build_stat_card,
    build_avatar_circle,
    show_toast,
    build_dialog_text_field,
    build_search_bar,
    open_confirm_dialog,
    close_dialog,
    ThemeColor,
)

_client = MongoClient("mongodb://localhost:27017/")
_inventory_db = _client["inventory"]
_ai_db = _client["inventoryai"]
_products_col = _inventory_db["products"]
_sales_col = _inventory_db["sales"]
_employees_col = _inventory_db["employees"]
_ai_sales_col = _ai_db["cleaned_inventory"]

CHART_BG = "#0D1120"
CHART_FG = "#A0AACB"
CHART_GRID = "#1E2640"


def _chart_to_b64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110, facecolor=CHART_BG)
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode()
    buf.close()
    plt.close(fig)
    return img


def _dark(ax, fig):
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=CHART_FG, labelsize=8, labelcolor=CHART_FG)
    ax.xaxis.label.set_color(CHART_FG)
    ax.yaxis.label.set_color(CHART_FG)
    for s in ax.spines.values():
        s.set_edgecolor(CHART_GRID)
    ax.grid(color=CHART_GRID, linewidth=0.4, alpha=0.5)
    ax.title.set_color(CHART_FG)


def _fuzzy(query: str, text: str) -> int:
    q, t = query.lower(), text.lower()
    if q in t:
        return 100
    score, qi = 0, 0
    for ch in t:
        if qi < len(q) and ch == q[qi]:
            score += 1
            qi += 1
    return score if qi == len(q) else 0


def _shimmer(width=None, height=18) -> ft.Container:
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
        expand=width is None,
    )


def _get_ai_metrics() -> dict:
    data = list(_ai_sales_col.find())
    if not data:
        return {"profit": 0, "anomaly_count": 0, "avg_profit": 0.0, "clusters": {}}
    profits = [d.get("profit", 0) for d in data]
    anomalies = [d.get("anomaly", 0) for d in data]
    clusters = {}
    for d in data:
        c = d.get("cluster", "?")
        clusters[c] = clusters.get(c, 0) + 1
    return {
        "profit": sum(profits),
        "anomaly_count": int(sum(1 for a in anomalies if a == -1)),
        "avg_profit": statistics.mean(profits) if profits else 0.0,
        "clusters": clusters,
    }


def _build_chart(title: str, fig, ax) -> str:
    ax.set_title(title)
    plt.tight_layout()
    return _chart_to_b64(fig)


def _build_sales_chart() -> str:
    dates: dict = {}
    for d in _sales_col.find():
        k = str(d.get("date", "?"))[:10]
        dates[k] = dates.get(k, 0) + float(d.get("total", 0))
    fig, ax = plt.subplots(figsize=(13, 3.5))
    _dark(ax, fig)
    if sorted_dates := sorted(dates.items()):
        xs, ys = [x[0] for x in sorted_dates], [x[1] for x in sorted_dates]
        ax.fill_between(range(len(xs)), ys, alpha=0.18, color="#7C6FFF")
        ax.plot(range(len(xs)), ys, color="#7C6FFF", linewidth=2.2)
        ax.set_xticks(range(0, len(xs), max(1, len(xs) // 8)))
        ax.set_xticklabels(
            [xs[i] for i in range(0, len(xs), max(1, len(xs) // 8))],
            rotation=30,
            ha="right",
            fontsize=7,
        )
    return _build_chart("Sales Trend", fig, ax)


def _build_profit_chart() -> str:
    months: dict = {}
    for d in _ai_sales_col.find():
        m = d.get("month", "?")
        months[m] = months.get(m, 0) + float(d.get("profit", 0))
    fig, ax = plt.subplots(figsize=(13, 3.5))
    _dark(ax, fig)
    if sorted_m := sorted(months.items()):
        xs, ys = [x[0] for x in sorted_m], [x[1] for x in sorted_m]
        ax.fill_between(range(len(xs)), ys, alpha=0.18, color=ThemeColor.ACCENT_TEAL)
        ax.plot(range(len(xs)), ys, color=ThemeColor.ACCENT_TEAL, linewidth=2.2)
        ax.set_xticks(range(0, len(xs), max(1, len(xs) // 8)))
        ax.set_xticklabels(
            [xs[i] for i in range(0, len(xs), max(1, len(xs) // 8))],
            rotation=30,
            ha="right",
            fontsize=7,
        )
    return _build_chart("Profit Trend", fig, ax)


def _build_stock_chart() -> str:
    data = list(_products_col.find().limit(15))
    names = [p.get("name", "?")[:14] for p in data]
    stock = [int(p.get("current_stock", 0)) for p in data]
    colors = [
        (
            ThemeColor.ACCENT_ROSE
            if s == 0
            else ThemeColor.ACCENT_AMBER if s < 10 else "#FFB347"
        )
        for s in stock
    ]
    fig, ax = plt.subplots(figsize=(13, 3.5))
    _dark(ax, fig)
    ax.bar(range(len(names)), stock, color=colors, alpha=0.88)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=7)
    return _build_chart("Stock Levels", fig, ax)


def _build_revenue_chart() -> str:
    rev: dict = {}
    for d in _sales_col.find():
        pid = d.get("product_id", "?")
        rev[pid] = rev.get(pid, 0) + float(d.get("total", 0))
    top = sorted(rev.items(), key=lambda x: -x[1])[:10]
    fig, ax = plt.subplots(figsize=(13, 3.5))
    _dark(ax, fig)
    if top:
        labels, values = [x[0] for x in top], [x[1] for x in top]
        ax.barh(range(len(labels)), values, color=ThemeColor.ACCENT_VIOLET, alpha=0.85)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
    return _build_chart("Top Revenue by Product", fig, ax)


def _build_db_table(docs: list, search: str = "") -> ftd.DataTable2:
    if not docs:
        return ftd.DataTable2(
            expand=True,
            columns=[ftd.DataColumn2(ft.Text("No data", color=ThemeColor.TEXT_MUTED))],
            rows=[],
            bgcolor=ThemeColor.SURFACE_PRIMARY,
            border_radius=12,
        )
    cols = [k for k in docs[0].keys() if k != "_id"][:8]
    if search.strip():
        scored = [
            (sc, d)
            for d in docs
            if (sc := _fuzzy(search, " ".join(str(d.get(c, "")) for c in cols))) > 0
        ]
        scored.sort(key=lambda x: -x[0])
        docs = [d for _, d in scored]
    rows = [
        ftd.DataRow2(
            cells=[
                ft.DataCell(
                    ft.Text(
                        str(doc.get(c, ""))[:20],
                        size=11,
                        color=ThemeColor.TEXT_SECONDARY,
                        no_wrap=True,
                    )
                )
                for c in cols
            ]
        )
        for doc in docs[:30]
    ]
    return ftd.DataTable2(
        columns=[
            ftd.DataColumn2(
                ft.Text(
                    c, size=11, color=ThemeColor.TEXT_MUTED, weight=ft.FontWeight.W_700
                )
            )
            for c in cols
        ],
        rows=rows,
        bgcolor=ThemeColor.SURFACE_PRIMARY,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        border_radius=12,
        horizontal_lines=ft.BorderSide(0.8, ThemeColor.BORDER_DEFAULT),
        vertical_lines=ft.BorderSide(0, "transparent"),
        heading_row_color=ft.Colors.with_opacity(0.06, ThemeColor.TEXT_PRIMARY),
        heading_row_height=42,
        data_row_height=42,
        column_spacing=10,
        divider_thickness=0,
        show_checkbox_column=False,
        data_row_color={
            ft.ControlState.HOVERED: ft.Colors.with_opacity(
                0.06, ThemeColor.ACCENT_VIOLET
            )
        },
    )


def build_admin_page(flet_page: ft.Page) -> ft.Control:
    def _shimmer_chart_card(title: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.INSERT_CHART,
                                color=ThemeColor.ACCENT_VIOLET,
                                size=16,
                            ),
                            ft.Text(
                                title,
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=8,
                    ),
                    build_vertical_spacer(12),
                    _shimmer(height=200),
                ],
                spacing=0,
            ),
            bgcolor=ThemeColor.CARD_BACKGROUND,
            border_radius=14,
            padding=18,
            border=ft.border.all(
                1, ft.Colors.with_opacity(0.4, ThemeColor.ACCENT_VIOLET)
            ),
        )

    charts_col = ft.Column(
        [
            _shimmer_chart_card("Sales Trend"),
            build_vertical_spacer(12),
            _shimmer_chart_card("Profit Trend"),
            build_vertical_spacer(12),
            _shimmer_chart_card("Stock Levels"),
            build_vertical_spacer(12),
            _shimmer_chart_card("Top Revenue by Product"),
        ],
        spacing=0,
    )

    emp_search_bar = build_search_bar("Search employees…")
    name_field = build_dialog_text_field("Full Name", expand=True)
    email_field = build_dialog_text_field("Email", expand=True)
    employee_list_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)
    _all_employees: list[dict] = []

    def _render_employees(query: str = "") -> None:
        docs = _all_employees
        if query.strip():
            scored = [
                (sc, e)
                for e in docs
                if (
                    sc := _fuzzy(
                        query,
                        f"{e.get('name','')} {e.get('email','')} {e.get('role','')}",
                    )
                )
                > 0
            ]
            scored.sort(key=lambda x: -x[0])
            docs = [d for _, d in scored]
        employee_list_col.controls.clear()
        for idx, emp in enumerate(docs):

            def _make_del(e=emp):
                def _on(_event):
                    dlg = open_confirm_dialog(
                        flet_page,
                        title="Confirm Delete",
                        body_lines=[f"Remove '{e.get('name', '')}' from the system?"],
                        on_confirm=lambda ev: (
                            _employees_col.delete_one({"_id": e["_id"]}),
                            _all_employees.remove(e) if e in _all_employees else None,
                            close_dialog(flet_page, dlg),
                            _render_employees(emp_search_bar.value or ""),
                            show_toast(flet_page, f"'{e.get('name', '')}' removed."),
                        ),
                    )

                return _on

            employee_list_col.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            build_avatar_circle(emp.get("name", "?")[0], idx, 36),
                            ft.Column(
                                [
                                    ft.Text(
                                        emp.get("name", ""),
                                        size=13,
                                        color=ThemeColor.TEXT_PRIMARY,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Text(
                                        emp.get("email", ""),
                                        size=11,
                                        color=ThemeColor.TEXT_MUTED,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    emp.get("role", ""),
                                    size=11,
                                    color=ThemeColor.ACCENT_VIOLET,
                                ),
                                bgcolor=ft.Colors.with_opacity(
                                    0.12, ThemeColor.ACCENT_VIOLET
                                ),
                                border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                icon_color=ThemeColor.ACCENT_ROSE,
                                icon_size=16,
                                tooltip="Remove employee",
                                on_click=_make_del(),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(vertical=6, horizontal=4),
                    border=ft.border.only(
                        bottom=ft.BorderSide(1, ThemeColor.BORDER_SUBTLE)
                    ),
                )
            )
        flet_page.update()

    def _load_employees():
        _all_employees.clear()
        _all_employees.extend(list(_employees_col.find()))
        _render_employees(emp_search_bar.value or "")

    emp_search_bar.on_change = lambda e: _render_employees(e.control.value or "")

    def _handle_add_employee(e):
        name_field.error = (
            None
            if name_field.value and name_field.value.strip()
            else "Name is required"
        )
        email_field.error = (
            None
            if email_field.value and email_field.value.strip()
            else "Email is required"
        )
        flet_page.update()
        if name_field.error or email_field.error:
            return
        _employees_col.insert_one(
            {
                "name": name_field.value.strip(),
                "email": email_field.value.strip(),
                "created_at": str(datetime.now()),
            }
        )
        name_field.value = email_field.value = ""
        name_field.error = email_field.error = None
        _load_employees()
        show_toast(flet_page, "Employee added.")

    _load_employees()

    employee_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.PEOPLE, color=ThemeColor.ACCENT_VIOLET, size=18
                        ),
                        ft.Text(
                            "Quick Employee Management",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=8,
                ),
                build_vertical_spacer(12),
                ft.Row([name_field, email_field], spacing=10, expand=True),
                build_vertical_spacer(6),
                ft.FilledButton(
                    "Add Employee",
                    icon=ft.Icons.PERSON_ADD,
                    on_click=_handle_add_employee,
                    height=44,
                    style=ft.ButtonStyle(
                        bgcolor=ThemeColor.ACCENT_VIOLET,
                        color=ThemeColor.TEXT_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                ),
                build_vertical_spacer(12),
                ft.Container(content=emp_search_bar, expand=True),
                build_vertical_spacer(8),
                employee_list_col,
            ],
            spacing=0,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=14,
        padding=20,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        expand=True,
    )

    alert_controls: list[ft.Control] = []
    low_count = 0
    for p in _products_col.find():
        stock = int(p.get("current_stock", 0))
        safety = int(p.get("safety_stock", 0))
        reorder = int(p.get("reorder_point", 0))
        if stock == 0:
            color, label = ThemeColor.ACCENT_ROSE, "Out of Stock"
            low_count += 1
        elif stock < safety or stock < reorder:
            color, label = ThemeColor.ACCENT_AMBER, "Low Stock"
            low_count += 1
        else:
            continue
        alert_controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(
                                (
                                    ft.Icons.WARNING_AMBER
                                    if stock > 0
                                    else ft.Icons.CANCEL
                                ),
                                color=color,
                                size=16,
                            ),
                            bgcolor=ft.Colors.with_opacity(0.12, color),
                            border_radius=8,
                            padding=6,
                            width=32,
                            height=32,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    p.get("name", ""),
                                    size=13,
                                    color=ThemeColor.TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Text(
                                    f"{label}: {stock} units  |  Safety: {safety}  |  Reorder: {reorder}",
                                    size=11,
                                    color=ThemeColor.TEXT_MUTED,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                label, size=11, color=color, weight=ft.FontWeight.W_600
                            ),
                            bgcolor=ft.Colors.with_opacity(0.12, color),
                            border_radius=6,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                bgcolor=ft.Colors.with_opacity(0.05, color),
                border_radius=10,
                border=ft.border.all(1, ft.Colors.with_opacity(0.2, color)),
            )
        )

    alerts_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.NOTIFICATIONS_ACTIVE,
                            color=ThemeColor.ACCENT_ROSE,
                            size=18,
                        ),
                        ft.Text(
                            "Stock Alerts",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                        ft.Container(expand=True),
                        (
                            ft.Container(
                                content=ft.Text(
                                    str(low_count),
                                    size=12,
                                    color=ThemeColor.ACCENT_ROSE,
                                    weight=ft.FontWeight.W_700,
                                ),
                                bgcolor=ft.Colors.with_opacity(
                                    0.15, ThemeColor.ACCENT_ROSE
                                ),
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=10, vertical=2),
                            )
                            if low_count > 0
                            else ft.Container()
                        ),
                    ],
                    spacing=8,
                ),
                build_vertical_spacer(12),
                ft.Column(
                    (
                        alert_controls
                        if alert_controls
                        else [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.CHECK_CIRCLE,
                                        color=ThemeColor.ACCENT_GREEN,
                                        size=18,
                                    ),
                                    ft.Text(
                                        "All stock levels are healthy.",
                                        size=13,
                                        color=ThemeColor.ACCENT_GREEN,
                                    ),
                                ],
                                spacing=8,
                            ),
                        ]
                    ),
                    scroll=ft.ScrollMode.AUTO,
                    spacing=8,
                ),
            ],
            spacing=0,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=14,
        padding=20,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
    )

    COLLECTIONS = {
        "Products": (_products_col, ThemeColor.ACCENT_VIOLET),
        "Sales": (_sales_col, ThemeColor.ACCENT_GREEN),
        "Employees": (_inventory_db["employees"], ThemeColor.ACCENT_AMBER),
        "Suppliers": (_inventory_db["suppliers"], ThemeColor.ACCENT_TEAL),
        "Purchase Orders": (_inventory_db["purchase_orders"], ThemeColor.ACCENT_ROSE),
        "AI Cleaned Data": (_ai_sales_col, ThemeColor.ACCENT_VIOLET),
    }

    db_sections: list[ft.Control] = []
    for col_name, (col, accent) in COLLECTIONS.items():
        docs = list(col.find().limit(100))
        table_container = ft.Container(_build_db_table(docs, ""))
        search = build_search_bar(f"Search {col_name}…")

        def _make_search_handler(d=docs, tc=table_container):
            def _on_change(e):
                tc.content = (_build_db_table(d, e.control.value or ""),)
                flet_page.update()

            return _on_change

        search.on_change = _make_search_handler()
        db_sections.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    width=8, height=8, border_radius=4, bgcolor=accent
                                ),
                                ft.Text(
                                    col_name,
                                    size=14,
                                    color=ThemeColor.TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(expand=True),
                                ft.Container(
                                    content=ft.Text(
                                        f"{len(docs)} rows", size=11, color=accent
                                    ),
                                    bgcolor=ft.Colors.with_opacity(0.12, accent),
                                    border_radius=6,
                                    padding=ft.padding.symmetric(
                                        horizontal=8, vertical=3
                                    ),
                                ),
                            ],
                            spacing=8,
                        ),
                        build_vertical_spacer(10),
                        ft.Row(
                            [search], expand=True
                        ),  # ft.Container(content=search, expand=True),
                        build_vertical_spacer(10),
                        table_container,
                    ],
                    spacing=0,
                ),
                bgcolor=ThemeColor.SURFACE_PRIMARY,
                border_radius=12,
                padding=16,
                border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
                expand=True,
            )
        )

    db_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.STORAGE, color=ThemeColor.ACCENT_VIOLET, size=18
                        ),
                        ft.Text(
                            "Database Viewer",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=8,
                ),
                build_vertical_spacer(14),
                ft.Column(db_sections, spacing=14),
            ],
            spacing=0,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=14,
        padding=20,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        expand=True,
    )

    content_col = ft.Column(
        [
            build_section_header(
                "Admin Dashboard", "System overview, analytics and management"
            ),
            build_vertical_spacer(18),
            ft.Row(
                [
                    _shimmer(height=100),
                    _shimmer(height=100),
                    _shimmer(height=100),
                    _shimmer(height=100),
                ],
                spacing=14,
                expand=True,
            ),
            build_vertical_spacer(18),
            charts_col,
            build_vertical_spacer(16),
            employee_card,
            build_vertical_spacer(14),
            alerts_card,
            build_vertical_spacer(14),
            db_card,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )

    async def _load_async():
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(None, _get_ai_metrics)

        content_col.controls[2] = ft.Row(
            [
                ft.Container(
                    build_stat_card(
                        ft.Icons.ATTACH_MONEY,
                        "Total Profit",
                        f"₹{metrics['profit']:,.0f}",
                        None,
                        ThemeColor.ACCENT_GREEN,
                    ),
                    width=200,
                ),
                ft.Container(
                    build_stat_card(
                        ft.Icons.BUG_REPORT,
                        "Anomalies",
                        metrics["anomaly_count"],
                        None,
                        ThemeColor.ACCENT_ROSE,
                    ),
                    width=200,
                ),
                ft.Container(
                    build_stat_card(
                        ft.Icons.CALCULATE,
                        "Average Profit",
                        f"₹{metrics['avg_profit']:,.2f}",
                        None,
                        ThemeColor.ACCENT_VIOLET,
                    ),
                    width=200,
                ),
                ft.Container(
                    build_stat_card(
                        ft.Icons.BUBBLE_CHART,
                        "Clusters",
                        len(metrics["clusters"]),
                        None,
                        ThemeColor.ACCENT_AMBER,
                    ),
                    width=200,
                ),
            ],
            spacing=14,
            wrap=True,
        )
        flet_page.update()

        chart_defs = [
            ("Sales Trend", _build_sales_chart, ThemeColor.ACCENT_VIOLET),
            ("Profit Trend", _build_profit_chart, ThemeColor.ACCENT_TEAL),
            ("Stock Levels", _build_stock_chart, ThemeColor.ACCENT_AMBER),
            ("Top Revenue by Product", _build_revenue_chart, ThemeColor.ACCENT_ROSE),
        ]
        new_chart_controls: list[ft.Control] = []
        for i, (title, build_fn, accent) in enumerate(chart_defs):
            b64 = await loop.run_in_executor(None, build_fn)
            card = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.INSERT_CHART, color=accent, size=16),
                                ft.Text(
                                    title,
                                    size=14,
                                    color=ThemeColor.TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=8,
                        ),
                        build_vertical_spacer(12),
                        ft.Image(
                            src=f"data:image/png;base64,{b64}",
                            fit=ft.BoxFit.FIT_WIDTH,
                            expand=True,
                            width=float("inf"),
                        ),
                    ],
                    spacing=0,
                ),
                bgcolor=ThemeColor.CARD_BACKGROUND,
                border_radius=14,
                padding=18,
                border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
                expand=True,
            )
            new_chart_controls.append(card)
            if i < len(chart_defs) - 1:
                new_chart_controls.append(build_vertical_spacer(12))
            charts_col.controls = new_chart_controls[:]
            flet_page.update()

    flet_page.run_task(_load_async)
    return content_col
