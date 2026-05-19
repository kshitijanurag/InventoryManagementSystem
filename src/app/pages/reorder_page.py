import threading
import time
from datetime import datetime, timedelta

import flet as ft
import flet_datatable2 as ftd

from sklearn.linear_model import LinearRegression
import numpy as np

from src.database.mongo_connection import get_inventory_database
from src.utilities.perf import PerfTimer
from src.app.components import (
    build_vertical_spacer,
    build_section_header,
    build_outlined_action_button,
    build_card,
    build_status_badge,
    build_icon_box,
    build_loading_container,
    build_progress_bar,
    show_toast,
    ColSpec,
    build_datatable,
    build_search_bar,
    build_table_card,
    refresh_datatable,
    sort_docs,
    ThemeColor,
)

_db = get_inventory_database()
_products_col = _db["products"]
_po_col = _db["purchase_orders"]
_counters_col = _db["counters"]
_auto_po_col = _db["auto_purchase_history"]


def _get_next_po_id() -> str:
    counter = _counters_col.find_one_and_update(
        {"_id": "po_counter"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return f"PO{counter['seq']}"


def _train_model() -> LinearRegression | None:
    X, y = [], []
    for d in _products_col.find():
        try:
            stock = int(d.get("current_stock", 0))
            reorder = int(d.get("reorder_point", 0))
            lead = int(d.get("lead_time_days", 1))
            turnover = max(int(d.get("turnover_ratio", 1)), 1)
            X.append([stock, reorder, lead, turnover])
            y.append(max(reorder * 2, 10))
        except Exception:
            continue
    if not X:
        return None
    model = LinearRegression()
    model.fit(np.array(X), np.array(y))
    return model


def _status_color(status: str) -> str:
    return {
        "Auto": ThemeColor.ACCENT_VIOLET,
        "Delivered": ThemeColor.ACCENT_GREEN,
        "Pending": ThemeColor.ACCENT_AMBER,
        "Rejected": ThemeColor.ACCENT_ROSE,
        "Cancelled": ThemeColor.ACCENT_ROSE,
    }.get(status, ThemeColor.TEXT_MUTED)


def build_reorder_page(flet_page: ft.Page) -> ft.Control:
    t = PerfTimer("reorder_page")

    _state: dict = {
        "ai_active": False,
        "model": None,
    }

    _stat_auto_val = ft.Text(
        "0", size=32, weight=ft.FontWeight.BOLD, color=ThemeColor.TEXT_PRIMARY
    )
    _stat_low_val = ft.Text(
        "0", size=32, weight=ft.FontWeight.BOLD, color=ThemeColor.TEXT_PRIMARY
    )
    _stat_scan_val = ft.Text(
        "—", size=22, weight=ft.FontWeight.BOLD, color=ThemeColor.TEXT_PRIMARY
    )
    _stat_model_val = ft.Text(
        "—", size=16, weight=ft.FontWeight.W_600, color=ThemeColor.TEXT_PRIMARY
    )

    _banner_title = ft.Text(
        "AI Engine — Standby",
        size=15,
        weight=ft.FontWeight.W_600,
        color=ThemeColor.TEXT_PRIMARY,
    )
    _banner_subtitle = ft.Text(
        "Enable the switch to start automated reordering.",
        size=12,
        color=ThemeColor.TEXT_MUTED,
    )
    _banner_dot = ft.Container(
        width=12, height=12, border_radius=6, bgcolor=ThemeColor.TEXT_MUTED
    )

    _loading = build_loading_container("Training AI model…")

    _ai_switch = ft.Switch(
        value=False,
        active_color=ThemeColor.ACCENT_VIOLET,
    )

    _low_stock_rows = ft.Column([], spacing=6)

    _po_sort = {"col": 0, "asc": False}
    _PO_COLS = [
        ColSpec("PO ID", "_id", width=110),
        ColSpec("Product", "product"),
        ColSpec("Qty", "predicted_qty", numeric=True, width=80),
        ColSpec("Confidence", "confidence", numeric=True, width=100),
        ColSpec("Status", "status", width=110),
        ColSpec("Created", "created_at"),
    ]
    _auto_table = build_datatable(_PO_COLS, _po_sort, lambda: _refresh_auto_table())
    _auto_table_search = build_search_bar("Search auto orders…")

    _all_auto_pos: list[dict] = []
    _refs: dict = {"history_card": None}

    def _refresh_low_stock() -> int:
        products = list(
            _products_col.find({}, {"name": 1, "current_stock": 1, "reorder_point": 1})
        )
        low = []
        for p in products:
            try:
                stock = int(p.get("current_stock", 0))
                reorder = int(p.get("reorder_point", 0))
                if stock < reorder:
                    pct = max(0, int((stock / reorder) * 100)) if reorder else 0
                    low.append((p.get("name", "?"), stock, reorder, pct))
            except Exception:
                continue

        controls: list[ft.Control] = []
        for name, stock, reorder, pct in sorted(low, key=lambda x: x[3]):
            bar_color = (
                ThemeColor.ACCENT_ROSE
                if pct < 25
                else ThemeColor.ACCENT_AMBER if pct < 60 else ThemeColor.ACCENT_GREEN
            )
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.WARNING_AMBER_ROUNDED,
                                        size=14,
                                        color=bar_color,
                                    ),
                                    ft.Text(
                                        name,
                                        size=13,
                                        color=ThemeColor.TEXT_PRIMARY,
                                        weight=ft.FontWeight.W_500,
                                        expand=True,
                                    ),
                                    ft.Text(
                                        f"{stock} / {reorder}",
                                        size=12,
                                        color=ThemeColor.TEXT_MUTED,
                                    ),
                                    build_status_badge(
                                        f"{pct}%", bar_color, is_filled_style=False
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            build_vertical_spacer(4),
                            build_progress_bar(
                                pct, bar_color=bar_color, bar_height_px=5
                            ),
                        ],
                        spacing=0,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.04, bar_color),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.14, bar_color)),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                )
            )

        _low_stock_rows.controls = controls or [
            ft.Text(
                "✓  All items are above reorder thresholds.",
                size=13,
                color=ThemeColor.ACCENT_GREEN,
            )
        ]
        return len(low)

    def _refresh_auto_table(query: str = "") -> None:
        nonlocal _all_auto_pos
        _all_auto_pos = list(_auto_po_col.find().sort("created_at", -1).limit(200))
        docs = _all_auto_pos
        if query:
            q = query.lower()
            docs = [
                d
                for d in docs
                if q in d.get("product", "").lower()
                or q in str(d.get("_id", "")).lower()
            ]

        sorted_docs = sort_docs(
            docs,
            _po_sort,
            ["_id", "product", "predicted_qty", "confidence", "status", "created_at"],
        )
        rows = []
        for po in sorted_docs:
            status = po.get("status", "Auto")
            sc = _status_color(status)
            conf = po.get("confidence")
            conf_text = f"{conf:.0f}%" if conf is not None else "—"
            ts = str(po.get("created_at", ""))[:16]
            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                str(po.get("_id", "")),
                                size=12,
                                color=ThemeColor.ACCENT_VIOLET,
                                weight=ft.FontWeight.W_600,
                                no_wrap=True,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                po.get("product", ""),
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(po.get("predicted_qty", "")),
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                                text_align=ft.TextAlign.RIGHT,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                conf_text,
                                size=12,
                                color=ThemeColor.ACCENT_TEAL,
                                text_align=ft.TextAlign.RIGHT,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    status,
                                    size=11,
                                    color=sc,
                                    weight=ft.FontWeight.W_700,
                                    no_wrap=True,
                                ),
                                bgcolor=ft.Colors.with_opacity(0.12, sc),
                                border_radius=8,
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            )
                        ),
                        ft.DataCell(ft.Text(ts, size=11, color=ThemeColor.TEXT_MUTED)),
                    ]
                )
            )
        refresh_datatable(_auto_table, rows, _po_sort)
        if _refs["history_card"] is not None:
            _refs["history_card"].visible = len(rows) > 0

    _auto_table_search.on_change = lambda e: (
        _refresh_auto_table(e.control.value or ""),
        flet_page.update(),
    )

    def _manual_refresh(e) -> None:
        low = _refresh_low_stock()
        _refresh_auto_table()
        _stat_low_val.value = str(low)
        _stat_auto_val.value = str(_auto_po_col.count_documents({}))
        flet_page.update()
        show_toast(flet_page, "Data refreshed.")

    def _engine_loop() -> None:
        model: LinearRegression | None = _state["model"]

        while _state["ai_active"]:
            now_str = datetime.now().strftime("%H:%M:%S")
            auto_count = int(_auto_po_col.count_documents({}))
            low_count = 0

            for p in _products_col.find():
                try:
                    stock = int(p.get("current_stock", 0))
                    reorder = int(p.get("reorder_point", 0))
                    lead = int(p.get("lead_time_days", 1))
                    turnover = max(int(p.get("turnover_ratio", 1)), 1)

                    if stock < reorder:
                        low_count += 1

                    days_remaining = stock / turnover
                    if not (stock < reorder and days_remaining < lead):
                        continue

                    if _po_col.find_one(
                        {"product_id": p["product_id"], "status": "Auto"}
                    ):
                        continue

                    if model:
                        pred_qty = max(
                            1, int(model.predict([[stock, reorder, lead, turnover]])[0])
                        )
                        margin = reorder - stock
                        confidence = min(99.0, 60.0 + (margin / max(reorder, 1)) * 39.0)
                    else:
                        pred_qty = max(reorder * 2, 10)
                        confidence = 60.0

                    po_id = _get_next_po_id()
                    _po_col.insert_one(
                        {
                            "_id": po_id,
                            "product_id": p["product_id"],
                            "supplier_id": p.get("supplier_id"),
                            "quantity": pred_qty,
                            "order_date": datetime.now(),
                            "expected_delivery": datetime.now() + timedelta(days=lead),
                            "status": "Auto",
                        }
                    )
                    _auto_po_col.insert_one(
                        {
                            "po_id": po_id,
                            "product": p.get("name", "Unknown"),
                            "predicted_qty": pred_qty,
                            "confidence": round(confidence, 1),
                            "status": "Auto",
                            "created_at": datetime.now(),
                        }
                    )
                    auto_count += 1

                except Exception:
                    continue

            _lc, _ac, _ns = low_count, auto_count, now_str

            async def _push():
                _refresh_low_stock()
                _refresh_auto_table()
                _stat_low_val.value = str(_lc)
                _stat_auto_val.value = str(_ac)
                _stat_scan_val.value = _ns
                try:
                    flet_page.update()
                except Exception:
                    pass

            flet_page.run_task(_push)
            time.sleep(8)

    def _toggle_ai(e) -> None:
        if _ai_switch.value:
            _loading.visible = True
            _banner_title.value = "Training AI model…"
            _banner_subtitle.value = "Analysing stock data, please wait."
            _banner_dot.bgcolor = ThemeColor.ACCENT_AMBER
            flet_page.update()

            def _start_in_thread():
                model = _train_model()
                _state["model"] = model
                _state["ai_active"] = True

                score_text = (
                    "LinearRegression fitted."
                    if model
                    else "No training data — using rule-based fallback."
                )

                async def _activate():
                    _loading.visible = False
                    _banner_title.value = "AI Engine — Active"
                    _banner_subtitle.value = f"Scanning every 8 s · {score_text}"
                    _banner_dot.bgcolor = ThemeColor.ACCENT_GREEN
                    _stat_model_val.value = score_text
                    try:
                        flet_page.update()
                    except Exception:
                        pass

                flet_page.run_task(_activate)
                _engine_loop()

            threading.Thread(target=_start_in_thread, daemon=True).start()

        else:
            _state["ai_active"] = False
            _loading.visible = False
            _banner_title.value = "AI Engine — Stopped"
            _banner_subtitle.value = "Toggle the switch to resume automated reordering."
            _banner_dot.bgcolor = ThemeColor.ACCENT_ROSE
            flet_page.update()
            show_toast(flet_page, "AI reorder engine stopped.")

    _ai_switch.on_change = _toggle_ai

    t.checkpoint("init: controls built")

    low_count = _refresh_low_stock()
    t.checkpoint(f"db: low-stock scan → {low_count} items")

    _refresh_auto_table()
    t.checkpoint("db: auto-PO history loaded")

    auto_total = _auto_po_col.count_documents({})
    _stat_low_val.value = str(low_count)
    _stat_auto_val.value = str(auto_total)
    t.checkpoint("db: count_documents")

    def _stat_card(
        icon: str, label: str, val_node: ft.Text, sub_node: ft.Text, color: str
    ) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            build_icon_box(icon, color, 20, 10, 10),
                            ft.Container(expand=True),
                        ]
                    ),
                    build_vertical_spacer(12),
                    ft.Container(
                        content=val_node, height=46, alignment=ft.Alignment.CENTER_LEFT
                    ),
                    build_vertical_spacer(2),
                    ft.Text(label, size=14, color=ThemeColor.TEXT_SECONDARY),
                    sub_node,
                ],
                spacing=3,
            ),
            bgcolor=ThemeColor.CARD_BACKGROUND,
            border_radius=16,
            padding=22,
            border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
            expand=True,
        )

    stats_row = ft.ResponsiveRow(
        [
            ft.Column(
                [
                    _stat_card(
                        ft.Icons.AUTORENEW,
                        "Auto POs Generated",
                        _stat_auto_val,
                        ft.Text(
                            "since system start", size=12, color=ThemeColor.TEXT_MUTED
                        ),
                        ThemeColor.ACCENT_VIOLET,
                    )
                ],
                col={"xs": 6, "md": 3},
            ),
            ft.Column(
                [
                    _stat_card(
                        ft.Icons.WARNING_AMBER_ROUNDED,
                        "Low-Stock Items",
                        _stat_low_val,
                        ft.Text(
                            "below reorder point", size=12, color=ThemeColor.TEXT_MUTED
                        ),
                        ThemeColor.ACCENT_ROSE,
                    )
                ],
                col={"xs": 6, "md": 3},
            ),
            ft.Column(
                [
                    _stat_card(
                        ft.Icons.ACCESS_TIME,
                        "Last Scan",
                        _stat_scan_val,
                        ft.Text(
                            "engine cycle timestamp",
                            size=12,
                            color=ThemeColor.TEXT_MUTED,
                        ),
                        ThemeColor.ACCENT_AMBER,
                    )
                ],
                col={"xs": 6, "md": 3},
            ),
            ft.Column(
                [
                    _stat_card(
                        ft.Icons.PSYCHOLOGY,
                        "Model Status",
                        _stat_model_val,
                        ft.Text(
                            "sklearn LinearRegression",
                            size=12,
                            color=ThemeColor.TEXT_MUTED,
                        ),
                        ThemeColor.ACCENT_TEAL,
                    )
                ],
                col={"xs": 6, "md": 3},
            ),
        ],
        spacing=16,
    )

    banner = ft.Container(
        content=ft.Row(
            [
                ft.Stack(
                    [
                        ft.Container(
                            width=46,
                            height=46,
                            border_radius=23,
                            bgcolor=ft.Colors.with_opacity(
                                0.10, ThemeColor.ACCENT_VIOLET
                            ),
                            border=ft.border.all(
                                1,
                                ft.Colors.with_opacity(0.22, ThemeColor.ACCENT_VIOLET),
                            ),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.PSYCHOLOGY,
                                color=ThemeColor.ACCENT_VIOLET,
                                size=22,
                            ),
                        ),
                        ft.Container(
                            right=0,
                            bottom=0,
                            width=16,
                            height=16,
                            border_radius=8,
                            bgcolor=ThemeColor.CARD_BACKGROUND,
                            alignment=ft.Alignment.CENTER,
                            content=_banner_dot,
                        ),
                    ]
                ),
                ft.Column([_banner_title, _banner_subtitle], spacing=3, expand=True),
                ft.Column(
                    [
                        ft.Text("Auto Reorder", size=12, color=ThemeColor.TEXT_MUTED),
                        _ai_switch,
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.05, ThemeColor.ACCENT_VIOLET),
        border=ft.border.all(1, ft.Colors.with_opacity(0.18, ThemeColor.ACCENT_VIOLET)),
        border_radius=14,
        padding=18,
    )

    low_stock_card = build_card(
        ft.Column(
            [
                ft.Row(
                    [
                        build_icon_box(
                            ft.Icons.INVENTORY_2, ThemeColor.ACCENT_ROSE, 18, 10, 10
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Low Stock Monitor",
                                    size=15,
                                    weight=ft.FontWeight.W_600,
                                    color=ThemeColor.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Items currently below their reorder point",
                                    size=12,
                                    color=ThemeColor.TEXT_MUTED,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        build_outlined_action_button(
                            "Refresh",
                            button_icon=ft.Icons.REFRESH,
                            on_click_handler=_manual_refresh,
                            is_small_size=True,
                            button_color=ThemeColor.ACCENT_TEAL,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                build_vertical_spacer(14),
                _low_stock_rows,
            ],
            spacing=0,
        )
    )

    _history_card_container = ft.Container(
        visible=False,
        content=build_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            build_icon_box(
                                ft.Icons.RECEIPT_LONG,
                                ThemeColor.ACCENT_VIOLET,
                                18,
                                10,
                                10,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Auto Reorder History",
                                        size=15,
                                        weight=ft.FontWeight.W_600,
                                        color=ThemeColor.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "Purchase orders generated by the AI engine",
                                        size=12,
                                        color=ThemeColor.TEXT_MUTED,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    build_vertical_spacer(14),
                    build_table_card(_auto_table, search_bar=_auto_table_search),
                ],
                spacing=0,
            )
        ),
    )

    _refs["history_card"] = _history_card_container
    _history_card_container.visible = len(_all_auto_pos) > 0
    t.checkpoint("ui: layout assembled")
    t.done()

    return ft.Column(
        [
            build_section_header(
                "Smart Reorder System",
                "AI-powered automatic purchase order generation",
                [
                    build_outlined_action_button(
                        "Refresh",
                        button_icon=ft.Icons.REFRESH,
                        on_click_handler=_manual_refresh,
                        is_small_size=True,
                    ),
                ],
            ),
            build_vertical_spacer(18),
            banner,
            build_vertical_spacer(8),
            _loading,
            build_vertical_spacer(8),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.INFO_OUTLINE,
                            size=16,
                            color=ft.Colors.with_opacity(0.7, ThemeColor.ACCENT_TEAL),
                        ),
                        ft.Text(
                            "A Purchase Order is auto-created when: "
                            "stock < reorder point  AND  (stock ÷ daily turnover) < lead time days.  "
                            "Duplicate POs for the same product are skipped. Engine scans every 8 s.",
                            size=12,
                            color=ThemeColor.TEXT_MUTED,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor=ft.Colors.with_opacity(0.04, ThemeColor.ACCENT_TEAL),
                border=ft.border.all(
                    1, ft.Colors.with_opacity(0.14, ThemeColor.ACCENT_TEAL)
                ),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
            ),
            build_vertical_spacer(8),
            stats_row,
            build_vertical_spacer(16),
            low_stock_card,
            build_vertical_spacer(14),
            _history_card_container,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
