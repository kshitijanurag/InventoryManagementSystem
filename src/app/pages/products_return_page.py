import flet as ft
import random
import flet_datatable2 as ftd
from datetime import datetime
from pymongo import MongoClient

from src.app.components import (
    build_vertical_spacer,
    build_section_header,
    build_status_badge,
    open_confirm_dialog,
    close_dialog,
    show_toast,
    ThemeColor,
)
from src.app.components.datatable2 import _dt2_kwargs

_db = MongoClient("mongodb://localhost:27017/")["inventory"]
_products_col = _db["products"]
_products_return_col = _db["products_return"]
_categories_col = _db["categories"]
_suppliers_col = _db["suppliers"]


def _build_cat_map() -> dict:
    result = {}
    for c in _categories_col.find():
        result[str(c.get("_id", ""))] = c.get("name", "")
        result[str(c.get("category_id", ""))] = c.get("name", "")
    return result


def _build_sup_map() -> dict:
    return {str(s.get("_id", "")): s.get("name", "") for s in _suppliers_col.find()}


def _resolve_cat(doc: dict, cat_map: dict) -> str:
    name = (doc.get("category_name") or "").strip()
    if name:
        return name
    cid = str(doc.get("category_id", ""))
    return cat_map.get(cid, cid) if cid else "—"


def _resolve_sup(doc: dict, sup_map: dict) -> str:
    name = (doc.get("supplier_name") or "").strip()
    if name:
        return name
    sid = str(doc.get("supplier_id", ""))
    return sup_map.get(sid, sid) if sid else "—"


def _generate_return_id() -> str:
    now = datetime.now()
    base = now.strftime("%d%m%Y%H%M%S") + f"{int(now.microsecond / 1000):03d}"
    return base + str(random.randint(100, 999))


def _return_product(product_id: str) -> None:
    product = _products_col.find_one({"product_id": product_id})
    if not product:
        return
    product.pop("_id", None)
    product["status"] = "Processing"
    product["return_id"] = _generate_return_id()
    _products_return_col.insert_one(product)
    _products_col.delete_one({"product_id": product_id})


def _cancel_return(product_id: str) -> None:
    product = _products_return_col.find_one({"product_id": product_id})
    if not product:
        return
    product.pop("_id", None)
    product.pop("status", None)
    product.pop("return_id", None)
    _products_col.insert_one(product)
    _products_return_col.delete_one({"product_id": product_id})


def build_products_return_page(flet_page: ft.Page) -> ft.Control:

    show_status_view = {"value": False}
    catalog_sort = {"col": 0, "asc": True}
    status_sort = {"col": 0, "asc": True}

    def _col_hdr(label: str, sort_state: dict, idx: int) -> ftd.DataColumn2:
        def _on_sort(e):
            sort_state["col"] = idx
            sort_state["asc"] = e.ascending
            _refresh_view()

        return ftd.DataColumn2(
            ft.Text(
                label, size=12, color=ThemeColor.TEXT_MUTED, weight=ft.FontWeight.W_700
            ),
            on_sort=_on_sort,
        )

    catalog_table = ftd.DataTable2(
        expand=True,
        columns=[
            _col_hdr("Product ID", catalog_sort, 1),
            _col_hdr("Name", catalog_sort, 2),
            _col_hdr("Category", catalog_sort, 3),
            _col_hdr("Stock", catalog_sort, 4),
            _col_hdr("Selling Price", catalog_sort, 5),
            _col_hdr("Cost Price", catalog_sort, 6),
            _col_hdr("Supplier", catalog_sort, 7),
            ftd.DataColumn2(
                ft.Text(
                    "Action",
                    size=12,
                    color=ThemeColor.TEXT_MUTED,
                    weight=ft.FontWeight.W_700,
                )
            ),
        ],
        rows=[],
        sort_column_index=0,
        sort_ascending=True,
        **_dt2_kwargs(),
    )

    status_table = ftd.DataTable2(
        expand=True,
        columns=[
            _col_hdr("Product ID", status_sort, 0),
            _col_hdr("Name", status_sort, 1),
            _col_hdr("Category", status_sort, 2),
            _col_hdr("Stock", status_sort, 3),
            _col_hdr("Price", status_sort, 4),
            _col_hdr("Supplier", status_sort, 5),
            _col_hdr("Status", status_sort, 6),
            _col_hdr("Return ID", status_sort, 7),
            ftd.DataColumn2(
                ft.Text(
                    "Action",
                    size=12,
                    color=ThemeColor.TEXT_MUTED,
                    weight=ft.FontWeight.W_700,
                )
            ),
        ],
        rows=[],
        sort_column_index=0,
        sort_ascending=True,
        **_dt2_kwargs(),
    )

    stat_catalog_text = ft.Text(
        "0", size=28, weight=ft.FontWeight.BOLD, color=ThemeColor.TEXT_PRIMARY
    )
    stat_return_text = ft.Text(
        "0", size=28, weight=ft.FontWeight.BOLD, color=ThemeColor.TEXT_PRIMARY
    )

    def _update_stats() -> None:
        stat_catalog_text.value = str(_products_col.count_documents({}))
        stat_return_text.value = str(_products_return_col.count_documents({}))

    def _confirm_return(product_doc: dict) -> None:
        name = product_doc.get("name", product_doc.get("product_id", ""))
        dlg = open_confirm_dialog(
            flet_page,
            title="Confirm Return",
            confirm_label="Confirm Return",
            body_lines=[
                "Are you sure you want to return:",
                f"'{name}'?",
                "The product will be moved from the catalog to the return queue.",
            ],
            on_confirm=lambda e: (
                _return_product(product_doc["product_id"]),
                close_dialog(flet_page, dlg),
                _update_stats(),
                _load_catalog_rows(),
                show_toast(flet_page, f"'{name}' moved to return queue."),
            ),
        )

    def _confirm_cancel(product_doc: dict) -> None:
        name = product_doc.get("name", product_doc.get("product_id", ""))
        dlg = open_confirm_dialog(
            flet_page,
            title="Confirm Cancel Return",
            confirm_label="Cancel Return",
            confirm_color=ThemeColor.ACCENT_AMBER,
            body_lines=[
                "Are you sure you want to cancel the return for:",
                f"'{name}'?",
                "The product will be moved back to the catalog.",
            ],
            on_confirm=lambda e: (
                _cancel_return(product_doc["product_id"]),
                close_dialog(flet_page, dlg),
                _update_stats(),
                _load_status_rows(),
                show_toast(
                    flet_page,
                    f"Return for '{name}' cancelled — product restored to catalog.",
                ),
            ),
        )

    def _sort_docs(docs: list, col: int, asc: bool, keys: list) -> list:
        key = keys[col] if col < len(keys) else keys[0]
        try:
            return sorted(docs, key=lambda d: (d.get(key) or ""), reverse=not asc)
        except Exception:
            return docs

    def _load_catalog_rows() -> None:
        cat_map = _build_cat_map()
        sup_map = _build_sup_map()
        docs = _sort_docs(
            list(_products_col.find()),
            catalog_sort["col"],
            catalog_sort["asc"],
            [
                "product_id",
                "product_id",
                "name",
                "category_id",
                "current_stock",
                "selling_price",
                "cost_price",
                "supplier_id",
            ],
        )
        rows = []
        for doc in docs:
            cat_name = _resolve_cat(doc, cat_map)
            sup_name = _resolve_sup(doc, sup_map)
            sell_price = float(doc.get("selling_price", 0) or 0)
            cost_price = float(doc.get("cost_price", 0) or 0)
            stock = int(doc.get("current_stock", 0) or 0)
            stock_color = (
                ThemeColor.ACCENT_ROSE
                if stock == 0
                else (
                    ThemeColor.ACCENT_AMBER
                    if stock < int(doc.get("reorder_point", 0) or 0)
                    else ThemeColor.ACCENT_GREEN
                )
            )
            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                str(doc.get("product_id", "")),
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                                no_wrap=True,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                doc.get("name", ""),
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(cat_name, size=12, color=ThemeColor.TEXT_MUTED)
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(stock),
                                size=13,
                                color=stock_color,
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"₹{sell_price:,.2f}",
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"₹{cost_price:,.2f}",
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(sup_name, size=12, color=ThemeColor.TEXT_MUTED)
                        ),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.ASSIGNMENT_RETURN_SHARP,
                                icon_color=ThemeColor.ACCENT_ROSE,
                                icon_size=18,
                                tooltip="Return Product",
                                on_click=lambda e, d=doc: _confirm_return(d),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                            )
                        ),
                    ]
                )
            )
        catalog_table.rows = rows
        catalog_table.sort_column_index = catalog_sort["col"]
        catalog_table.sort_ascending = catalog_sort["asc"]
        flet_page.update()

    def _load_status_rows() -> None:
        cat_map = _build_cat_map()
        sup_map = _build_sup_map()
        docs = _sort_docs(
            list(_products_return_col.find()),
            status_sort["col"],
            status_sort["asc"],
            [
                "product_id",
                "name",
                "category_id",
                "current_stock",
                "selling_price",
                "supplier_id",
                "status",
                "return_id",
            ],
        )
        rows = []
        for doc in docs:
            cat_name = _resolve_cat(doc, cat_map)
            sup_name = _resolve_sup(doc, sup_map)
            sell_price = float(doc.get("selling_price", 0) or 0)
            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                str(doc.get("product_id", "")),
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                                no_wrap=True,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                doc.get("name", ""),
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(cat_name, size=12, color=ThemeColor.TEXT_MUTED)
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(doc.get("current_stock", "")),
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"₹{sell_price:,.2f}",
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(sup_name, size=12, color=ThemeColor.TEXT_MUTED)
                        ),
                        ft.DataCell(
                            build_status_badge(
                                doc.get("status", ""), ThemeColor.ACCENT_AMBER
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                doc.get("return_id", ""),
                                size=11,
                                color=ThemeColor.ACCENT_GREEN,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            )
                        ),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.CANCEL_SCHEDULE_SEND_ROUNDED,
                                icon_color=ThemeColor.ACCENT_ROSE,
                                icon_size=18,
                                tooltip="Cancel Return",
                                on_click=lambda e, d=doc: _confirm_cancel(d),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                            )
                        ),
                    ]
                )
            )
        status_table.rows = rows
        status_table.sort_column_index = status_sort["col"]
        status_table.sort_ascending = status_sort["asc"]
        flet_page.update()

    _btn_style = ft.ButtonStyle(
        bgcolor=ThemeColor.ACCENT_VIOLET,
        color=ThemeColor.TEXT_PRIMARY,
        shape=ft.RoundedRectangleBorder(radius=12),
    )
    btn_catalog = ft.FilledButton(
        "Product Catalog", icon=ft.Icons.INVENTORY_2, height=44, style=_btn_style
    )
    btn_status = ft.FilledButton(
        "Status View",
        icon=ft.Icons.CIRCLE_NOTIFICATIONS_SHARP,
        height=44,
        style=_btn_style,
    )

    def _update_buttons() -> None:
        is_status = show_status_view["value"]
        btn_catalog.disabled = not is_status
        btn_status.disabled = is_status
        btn_catalog.opacity = 0.45 if not is_status else 1.0
        btn_status.opacity = 0.45 if is_status else 1.0

    table_container = ft.Container(
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=16,
        padding=22,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        content=ft.Column([], spacing=0),
    )

    def _refresh_view() -> None:
        if show_status_view["value"]:
            _load_status_rows()
            table_container.content = ft.Column(
                [
                    ft.Text(
                        "Return Status — Click ✕ to Cancel Return",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color=ThemeColor.TEXT_PRIMARY,
                    ),
                    build_vertical_spacer(12),
                    status_table,
                ],
                spacing=0,
            )
        else:
            _load_catalog_rows()
            table_container.content = ft.Column(
                [
                    ft.Text(
                        "Product Catalog — Click ↩ to Return",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color=ThemeColor.TEXT_PRIMARY,
                    ),
                    build_vertical_spacer(12),
                    catalog_table,
                ],
                spacing=0,
            )
        flet_page.update()

    btn_catalog.on_click = lambda _: (
        show_status_view.__setitem__("value", False),
        _update_buttons(),
        _refresh_view(),
    )
    btn_status.on_click = lambda _: (
        show_status_view.__setitem__("value", True),
        _update_buttons(),
        _refresh_view(),
    )

    _update_stats()
    _update_buttons()
    _refresh_view()

    return ft.Column(
        [
            build_section_header(
                "Products Return",
                "Manage product return requests",
                [ft.Row([btn_catalog, btn_status], spacing=10)],
            ),
            build_vertical_spacer(18),
            ft.Row(
                [
                    ft.Container(
                        width=180,
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.INVENTORY,
                                    color=ThemeColor.ACCENT_VIOLET,
                                    size=22,
                                ),
                                stat_catalog_text,
                                ft.Text(
                                    "In Catalog",
                                    size=14,
                                    color=ThemeColor.TEXT_SECONDARY,
                                ),
                            ],
                            spacing=4,
                        ),
                        bgcolor=ThemeColor.CARD_BACKGROUND,
                        border_radius=14,
                        padding=20,
                        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
                    ),
                    ft.Container(
                        width=180,
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.ASSIGNMENT_RETURN_SHARP,
                                    color=ThemeColor.ACCENT_ROSE,
                                    size=22,
                                ),
                                stat_return_text,
                                ft.Text(
                                    "In Return",
                                    size=14,
                                    color=ThemeColor.TEXT_SECONDARY,
                                ),
                            ],
                            spacing=4,
                        ),
                        bgcolor=ThemeColor.CARD_BACKGROUND,
                        border_radius=14,
                        padding=20,
                        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
                    ),
                ],
                spacing=16,
            ),
            build_vertical_spacer(14),
            table_container,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
