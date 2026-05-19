import flet as ft
import flet_datatable2 as ftd
from datetime import datetime, timedelta
from pymongo import MongoClient, ReturnDocument

from src.app.components import (
    build_csv_import_button,
    build_vertical_spacer,
    build_section_header,
    build_stat_card,
    build_filled_action_button,
    show_toast,
    build_dialog_text_field,
    build_dialog_dropdown,
    build_dialog_switch,
    build_date_picker_row,
    make_live_validator,
    open_form_dialog,
    open_confirm_dialog,
    close_dialog,
    CsvImportController,
    ColSpec,
    build_datatable,
    build_search_bar,
    build_table_card,
    build_action_cell,
    refresh_datatable,
    sort_docs,
    ThemeColor,
)
from src.utilities.fuzzy_search import _fuzzy_score

_db = MongoClient("mongodb://localhost:27017/")["inventory"]
_products_col = _db["products"]
_suppliers_col = _db["suppliers"]
_purchase_col = _db["purchase_orders"]
_counters_col = _db["counters"]

_ALL_POS: list[dict] = []

_SORT_KEYS = ["_id", "product_id", "supplier_id", "quantity", "order_date", "status"]
_COL_SPECS = [
    ColSpec("Purchase Order ID", "_id"),
    ColSpec("Product", "product_id"),
    ColSpec("Supplier", "supplier_id"),
    ColSpec("Quantity", "quantity", numeric=True),
    ColSpec("Order Date", "order_date"),
    ColSpec("Status", "status"),
    ColSpec("Actions", None),
]
_PO_STATUSES = [
    "Pending",
    "Approved",
    "Delivered",
    "Rejected",
    "Not Available",
    "Cancelled",
]


def _get_next_po_id() -> str:
    counter = _counters_col.find_one_and_update(
        {"_id": "po_counter"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"PO{counter['seq']}"


def _get_product_name(product_id: str) -> str:
    prod = _products_col.find_one({"product_id": product_id})
    return prod.get("name", product_id) if prod else product_id


def _get_supplier_name(supplier_id) -> str:
    try:
        from bson import ObjectId

        sup = _suppliers_col.find_one({"_id": ObjectId(str(supplier_id))})
    except Exception:
        sup = _suppliers_col.find_one({"_id": supplier_id})
    return sup.get("name", str(supplier_id)) if sup else str(supplier_id)


def _status_color(status: str) -> str:
    if status == "Delivered":
        return ThemeColor.ACCENT_GREEN
    if status in ("Rejected", "Not Available"):
        return ThemeColor.ACCENT_ROSE
    return ThemeColor.ACCENT_AMBER


def build_purchase_orders_page(flet_page: ft.Page) -> ft.Control:
    global _ALL_POS

    _po_sort = {"col": 0, "asc": True}
    selected_id = {"value": None}
    dlg_is_edit = {"value": False}

    def _on_sort():
        _apply_search(search_bar.value or "")

    po_datatable = build_datatable(_COL_SPECS, _po_sort, _on_sort)
    search_bar = build_search_bar("Search purchase orders…")

    def _product_options():
        return [
            ft.DropdownOption(
                key=p["product_id"], text=f"{p['product_id']} – {p['name']}"
            )
            for p in _products_col.find({}, {"product_id": 1, "name": 1}).limit(100)
        ]

    def _supplier_options():
        return [
            ft.DropdownOption(key=str(s["_id"]), text=s["name"])
            for s in _suppliers_col.find({}, {"_id": 1, "name": 1}).limit(100)
        ]

    d_product = build_dialog_dropdown("Product *", _product_options(), expand=True)
    d_supplier = build_dialog_dropdown("Supplier *", _supplier_options(), expand=True)
    d_quantity = build_dialog_text_field(
        "Quantity *", expand=True, keyboard_type=ft.KeyboardType.NUMBER
    )
    d_delay = build_dialog_switch("Delayed", active_color=ThemeColor.ACCENT_ROSE)

    order_row, order_state = build_date_picker_row(
        flet_page,
        "Order Date",
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        date_format="%Y-%m-%d",
    )
    delivery_row, delivery_state = build_date_picker_row(
        flet_page,
        "Expected Delivery Date",
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        date_format="%Y-%m-%d",
    )

    order_state["date"] = datetime.now().strftime("%Y-%m-%d")
    order_state["dt"] = datetime.now()

    def _check_qty(v: str) -> str | None:
        if not v:
            return "Quantity is required"
        if not v.isdigit() or int(v) <= 0:
            return "Quantity must be a whole number > 0"
        return None

    make_live_validator(flet_page, d_quantity, _check_qty)

    def _auto_calc_delivery(*_):
        sup = _suppliers_col.find_one({"_id": d_supplier.value})
        if not sup or not order_state.get("dt"):
            return
        lead = int(sup.get("avg_lead_time", 7))
        dt = order_state["dt"] + timedelta(days=lead)
        delivery_state["dt"] = dt
        delivery_state["date"] = dt.strftime("%Y-%m-%d")
        flet_page.update()

    d_supplier.on_change = lambda e: (_auto_calc_delivery(), flet_page.update())

    def _load_all() -> None:
        global _ALL_POS
        _ALL_POS = list(_purchase_col.find().limit(200))

    def _render_table(pos: list[dict]) -> None:
        sorted_pos = sort_docs(pos, _po_sort, _SORT_KEYS)
        rows = []
        for po in sorted_pos:
            product_name = _get_product_name(po.get("product_id", ""))
            supplier_name = _get_supplier_name(po.get("supplier_id", ""))
            status = po.get("status", "Pending")
            sc = _status_color(status)

            def _make_edit(p=po):
                def _on(_):
                    _open_edit_dialog(p)

                return _on

            def _make_del(p=po):
                def _on(_):
                    _confirm_delete(p)

                return _on

            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                str(po["_id"]),
                                size=11,
                                color=ThemeColor.TEXT_MUTED,
                                no_wrap=True,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                product_name, size=13, color=ThemeColor.TEXT_PRIMARY
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                supplier_name, size=12, color=ThemeColor.TEXT_SECONDARY
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(po.get("quantity", "")),
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(po.get("order_date", ""))[:10],
                                size=11,
                                color=ThemeColor.TEXT_MUTED,
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
                        build_action_cell(
                            on_edit=_make_edit(),
                            on_delete=_make_del(),
                            edit_tooltip="Edit order",
                            delete_tooltip="Delete order",
                        ),
                    ]
                )
            )
        refresh_datatable(po_datatable, rows, _po_sort)
        flet_page.update()

    def _apply_search(query: str) -> None:
        if not query.strip():
            _render_table(_ALL_POS)
            return
        scored = [
            (sc, po)
            for po in _ALL_POS
            if (
                sc := _fuzzy_score(
                    query,
                    f"{po['_id']} {po.get('product_id','')} {po.get('supplier_id','')} {po.get('status','')}",
                )
            )
            > 0
        ]
        scored.sort(key=lambda x: -x[0])
        _render_table([d for _, d in scored])

    search_bar.on_change = lambda e: _apply_search(e.control.value or "")

    def _form_fields() -> list[ft.Control]:
        return [
            ft.Row([d_product, d_supplier], spacing=12),
            ft.Row(
                [
                    d_quantity,
                    ft.Container(
                        content=d_delay, padding=ft.padding.only(left=8, top=8)
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            order_row,
            delivery_row,
        ]

    def _validate_form() -> bool:
        ok = True
        if not d_product.value:
            d_product.error_text = "Please select a product"
            ok = False
        else:
            d_product.error_text = None
        if not d_supplier.value:
            d_supplier.error_text = "Please select a supplier"
            ok = False
        else:
            d_supplier.error_text = None
        qty_err = _check_qty(d_quantity.value or "")
        d_quantity.error = qty_err
        if qty_err:
            ok = False
        flet_page.update()
        return ok

    def _clear_fields() -> None:
        d_product.value = d_supplier.value = None
        d_quantity.value = ""
        d_delay.value = False
        d_product.error_text = d_supplier.error_text = None
        d_quantity.error = None
        order_state["date"] = datetime.now().strftime("%Y-%m-%d")
        order_state["dt"] = datetime.now()
        delivery_state["date"] = ""
        delivery_state["dt"] = None

    def _collect_payload() -> dict:
        order_dt = datetime.combine(
            (
                order_state["dt"].date()
                if order_state.get("dt")
                else datetime.now().date()
            ),
            datetime.min.time(),
        )
        delivery_dt = (
            datetime.combine(delivery_state["dt"].date(), datetime.min.time())
            if delivery_state.get("dt")
            else order_dt + timedelta(days=7)
        )
        return {
            "product_id": d_product.value,
            "supplier_id": d_supplier.value,
            "quantity": int(d_quantity.value),
            "order_date": order_dt,
            "expected_delivery": delivery_dt,
            "delay_flag": bool(d_delay.value),
        }

    def _open_add_dialog(e) -> None:
        dlg_is_edit["value"] = False
        selected_id["value"] = None
        _clear_fields()

        def _on_submit(_e):
            if not _validate_form():
                return
            payload = _collect_payload()
            payload["_id"] = _get_next_po_id()
            payload["status"] = "Pending"
            _purchase_col.insert_one(payload)
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(flet_page, "Purchase order created.")

        dlg = open_form_dialog(
            flet_page,
            title="New Purchase Order",
            fields=_form_fields(),
            submit_label="Create Order",
            on_submit=_on_submit,
            width=600,
            height=320,
        )

    def _open_edit_dialog(po: dict) -> None:
        dlg_is_edit["value"] = True
        selected_id["value"] = po["_id"]
        d_product.value = str(po.get("product_id") or "")
        d_supplier.value = str(po.get("supplier_id") or "")
        d_quantity.value = str(po.get("quantity", ""))
        d_delay.value = bool(po.get("delay_flag", False))
        d_product.error_text = d_supplier.error_text = None
        d_quantity.error = None
        try:
            od = po.get("order_date")
            if od:
                dt = (
                    od
                    if hasattr(od, "date")
                    else datetime.strptime(str(od)[:10], "%Y-%m-%d")
                )
                order_state["dt"] = dt
                order_state["date"] = (
                    dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(od)[:10]
                )
            dd = po.get("expected_delivery")
            if dd:
                dt2 = (
                    dd
                    if hasattr(dd, "date")
                    else datetime.strptime(str(dd)[:10], "%Y-%m-%d")
                )
                delivery_state["dt"] = dt2
                delivery_state["date"] = (
                    dt2.strftime("%Y-%m-%d")
                    if hasattr(dt2, "strftime")
                    else str(dd)[:10]
                )
        except Exception:
            pass

        def _on_submit(_e):
            if not _validate_form():
                return
            _purchase_col.update_one(
                {"_id": selected_id["value"]}, {"$set": _collect_payload()}
            )
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(flet_page, "Purchase order updated.")

        dlg = open_form_dialog(
            flet_page,
            title="Edit Purchase Order",
            fields=_form_fields(),
            submit_label="Save Changes",
            on_submit=_on_submit,
            width=600,
            height=320,
        )

    def _confirm_delete(po: dict) -> None:
        prod = _products_col.find_one({"product_id": po.get("product_id", "")})
        product_name = prod["name"] if prod else po.get("product_id", "")
        supplier_name = _get_supplier_name(po.get("supplier_id", ""))
        dlg = open_confirm_dialog(
            flet_page,
            title="Confirm Delete",
            body_lines=[
                "Are you sure you want to delete this purchase order?",
                f"Order ID: {po['_id']}  |  Product: {product_name}  |  Supplier: {supplier_name}",
                "This action cannot be undone.",
            ],
            on_confirm=lambda e: (
                _purchase_col.delete_one({"_id": po["_id"]}),
                close_dialog(flet_page, dlg),
                _load_all(),
                _apply_search(search_bar.value or ""),
                show_toast(flet_page, f"Purchase order '{po['_id']}' deleted."),
            ),
        )

    csv_ctrl = CsvImportController(
        flet_page,
        collection=_purchase_col,
        on_done=lambda: (_load_all(), _apply_search(search_bar.value or "")),
    )

    def _open_csv_picker(e) -> None:
        csv_ctrl.open(hint_text="Header row required. Existing IDs are skipped.")

    _load_all()
    _render_table(_ALL_POS)
    total = _purchase_col.count_documents({})
    pending = _purchase_col.count_documents({"status": "Pending"})
    delivered = _purchase_col.count_documents({"status": "Delivered"})

    return ft.Column(
        [
            build_section_header(
                "Purchase Orders",
                "Procurement lifecycle management",
                [
                    build_csv_import_button(_open_csv_picker),
                    build_filled_action_button(
                        "+ New Order", on_click_handler=_open_add_dialog
                    ),
                ],
            ),
            build_vertical_spacer(14),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.RECEIPT,
                                "Total Orders",
                                total,
                                None,
                                ThemeColor.ACCENT_VIOLET,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.HOURGLASS_EMPTY,
                                "Pending",
                                pending,
                                None,
                                ThemeColor.ACCENT_AMBER,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.CHECK,
                                "Delivered",
                                delivered,
                                None,
                                ThemeColor.ACCENT_GREEN,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                ],
                spacing=16,
            ),
            build_vertical_spacer(14),
            build_table_card(po_datatable, search_bar=search_bar),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
