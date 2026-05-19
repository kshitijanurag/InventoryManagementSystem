import threading
import flet as ft
import flet_datatable2 as ftd
from datetime import datetime

from src.database.mongo_connection import get_inventory_database
from src.app.components import (
    build_csv_import_button,
    build_vertical_spacer,
    build_section_header,
    build_stat_card,
    build_filled_action_button,
    show_toast,
    build_dialog_text_field,
    build_dialog_dropdown,
    make_live_validator,
    validate_required,
    validate_email,
    validate_phone,
    validate_int_range,
    validate_all,
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

_db = get_inventory_database()
_suppliers_col = _db["suppliers"]
_products_col = _db["products"]
_po_col = _db["purchase_orders"]

_ALL_SUPPLIERS: list[dict] = []
_ALL_POS: list[dict] = []

_SUP_SORT_KEYS = [
    "_id",
    "name",
    "contact",
    "email",
    "avg_lead_time",
    "reliability_score",
]
_SUP_COLS = [
    ColSpec("ID", "_id"),
    ColSpec("Name", "name"),
    ColSpec("Contact", "contact"),
    ColSpec("Email", "email"),
    ColSpec("Lead Time (days)", "avg_lead_time", numeric=True),
    ColSpec("Reliability Score", "reliability_score", numeric=True),
    ColSpec("Actions", None),
]

_PO_SORT_KEYS = ["_id", "product_id", "supplier_id", "quantity", "status"]
_PO_COLS = [
    ColSpec("Purchase Order ID", "_id"),
    ColSpec("Product", "product_id"),
    ColSpec("Supplier", "supplier_id"),
    ColSpec("Quantity", "quantity", numeric=True),
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


def _build_lookup_maps(po_docs: list[dict]) -> tuple[dict, dict]:
    product_ids = {po.get("product_id") for po in po_docs if po.get("product_id")}
    supplier_ids = {po.get("supplier_id") for po in po_docs if po.get("supplier_id")}

    product_map: dict = {}
    if product_ids:
        for p in _products_col.find(
            {"product_id": {"$in": list(product_ids)}}, {"product_id": 1, "name": 1}
        ):
            product_map[p["product_id"]] = p.get("name", p["product_id"])

    supplier_map: dict = {}
    if supplier_ids:
        from bson import ObjectId

        oid_ids, str_ids = [], []
        for sid in supplier_ids:
            try:
                oid_ids.append(ObjectId(str(sid)))
            except Exception:
                str_ids.append(sid)
        query_parts = []
        if oid_ids:
            query_parts.append({"_id": {"$in": oid_ids}})
        if str_ids:
            query_parts.append({"_id": {"$in": str_ids}})
        q = (
            {"$or": query_parts}
            if len(query_parts) > 1
            else (query_parts[0] if query_parts else {})
        )
        for s in _suppliers_col.find(q, {"name": 1}):
            supplier_map[str(s["_id"])] = s.get("name", str(s["_id"]))

    return product_map, supplier_map


def _status_color(status: str) -> str:
    if status == "Delivered":
        return ThemeColor.ACCENT_GREEN
    if status in ("Rejected", "Not Available", "Cancelled"):
        return ThemeColor.ACCENT_ROSE
    return ThemeColor.ACCENT_AMBER


def build_suppliers_page(flet_page: ft.Page) -> ft.Control:
    global _ALL_SUPPLIERS, _ALL_POS

    _sup_sort = {"col": 0, "asc": True}
    _po_sort = {"col": 0, "asc": True}
    selected_supplier = {"doc": None}
    dlg_is_edit = {"value": False}

    def _on_sup_sort():
        _apply_search(search_bar.value or "")

    def _on_po_sort():
        _render_po_table()

    supplier_datatable = build_datatable(_SUP_COLS, _sup_sort, _on_sup_sort)
    po_datatable = build_datatable(_PO_COLS, _po_sort, _on_po_sort)
    search_bar = build_search_bar("Search suppliers…")

    d_name = build_dialog_text_field("Supplier Name *", expand=True)
    d_contact = build_dialog_text_field("Contact / Phone", expand=True)
    d_email = build_dialog_text_field("Email", expand=True)
    d_address = build_dialog_text_field("Address", expand=True)
    d_lead = build_dialog_text_field(
        "Average Lead Time (days)", expand=True, keyboard_type=ft.KeyboardType.NUMBER
    )
    d_reliability = build_dialog_text_field(
        "Reliability Score (1–10)", expand=True, keyboard_type=ft.KeyboardType.NUMBER
    )

    make_live_validator(
        flet_page, d_name, lambda v: validate_required(v, "Supplier name")
    )
    make_live_validator(flet_page, d_email, validate_email)
    make_live_validator(flet_page, d_contact, validate_phone)
    make_live_validator(
        flet_page,
        d_lead,
        lambda v: validate_int_range(v, 1, 365)
        and None
        or ("Lead time must be 1–365 days" if v else None),
    )
    make_live_validator(
        flet_page,
        d_reliability,
        lambda v: validate_int_range(v, 1, 10)
        and None
        or ("Score must be 1–10" if v else None),
    )

    _initializing = {"value": True}

    def _load_all() -> None:
        global _ALL_SUPPLIERS
        _ALL_SUPPLIERS = list(_suppliers_col.find().limit(200))

    def _load_all_pos() -> None:
        global _ALL_POS
        _ALL_POS = list(_po_col.find().limit(500))

    def _render_supplier_table(docs: list[dict]) -> None:
        sorted_docs = sort_docs(docs, _sup_sort, _SUP_SORT_KEYS)
        rows = []
        for s in sorted_docs:
            reliability = s.get("reliability_score", 0)
            rel_color = (
                ThemeColor.ACCENT_GREEN
                if int(reliability) >= 8
                else (
                    ThemeColor.ACCENT_AMBER
                    if int(reliability) >= 5
                    else ThemeColor.ACCENT_ROSE
                )
            )
            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                str(s.get("_id", ""))[:18],
                                size=11,
                                color=ThemeColor.TEXT_MUTED,
                                no_wrap=True,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                s.get("name", ""),
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(s.get("contact", "")),
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                s.get("email", ""), size=12, color=ThemeColor.TEXT_MUTED
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(s.get("avg_lead_time", "")),
                                size=12,
                                color=ThemeColor.ACCENT_VIOLET,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(reliability),
                                size=12,
                                color=rel_color,
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        build_action_cell(
                            on_edit=lambda e, d=s: _open_edit_dialog(d),
                            on_delete=lambda e, d=s: _confirm_delete(d),
                            edit_tooltip="Edit supplier",
                            delete_tooltip="Delete supplier",
                        ),
                    ]
                )
            )
        refresh_datatable(supplier_datatable, rows, _sup_sort)
        if not _initializing["value"]:
            flet_page.update()

    def _apply_search(query: str) -> None:
        if not query.strip():
            _render_supplier_table(_ALL_SUPPLIERS)
            return
        scored = [
            (sc, s)
            for s in _ALL_SUPPLIERS
            if (
                sc := _fuzzy_score(
                    query,
                    f"{s.get('name','')} {s.get('email','')} {s.get('contact','')}",
                )
            )
            > 0
        ]
        scored.sort(key=lambda x: -x[0])
        _render_supplier_table([d for _, d in scored])

    search_bar.on_change = lambda e: _apply_search(e.control.value or "")

    def _render_po_table() -> None:
        po_docs = sort_docs(list(_po_col.find().limit(100)), _po_sort, _PO_SORT_KEYS)
        product_map, supplier_map = _build_lookup_maps(po_docs)

        rows = []
        for po in po_docs:
            status = po.get("status", "Pending")
            sc = _status_color(status)
            prod_name = product_map.get(
                po.get("product_id", ""), po.get("product_id", "")
            )
            sup_name = supplier_map.get(
                str(po.get("supplier_id", "")), str(po.get("supplier_id", ""))
            )
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
                            ft.Text(prod_name, size=12, color=ThemeColor.TEXT_SECONDARY)
                        ),
                        ft.DataCell(
                            ft.Text(sup_name, size=12, color=ThemeColor.TEXT_MUTED)
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(po.get("quantity", "")),
                                size=12,
                                color=ThemeColor.TEXT_PRIMARY,
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
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.EDIT_NOTE,
                                icon_color=ThemeColor.ACCENT_VIOLET,
                                icon_size=18,
                                tooltip="Update order status",
                                on_click=lambda e, p=po: _open_po_update_dialog(p),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                            )
                        ),
                    ]
                )
            )
        refresh_datatable(po_datatable, rows, _po_sort)
        if not _initializing["value"]:
            flet_page.update()

    def _open_po_update_dialog(po: dict) -> None:
        product_map, supplier_map = _build_lookup_maps([po])
        product_name = product_map.get(
            po.get("product_id", ""), po.get("product_id", "")
        )
        supplier_name = supplier_map.get(
            str(po.get("supplier_id", "")), str(po.get("supplier_id", ""))
        )

        dlg_qty = build_dialog_text_field(
            "Delivered Quantity",
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            value=str(po.get("quantity", "")),
        )
        dlg_status = build_dialog_dropdown(
            "Update Status",
            [ft.DropdownOption(s) for s in _PO_STATUSES],
            value=po.get("status"),
            expand=True,
        )
        make_live_validator(
            flet_page,
            dlg_qty,
            lambda v: (
                None if v and v.isdigit() and int(v) >= 0 else "Enter a valid number"
            ),
        )

        _info = dict(size=13, color=ThemeColor.TEXT_MUTED)
        _val = dict(size=13, color=ThemeColor.TEXT_PRIMARY, weight=ft.FontWeight.W_500)

        info_box = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Order ID:", **_info),
                            ft.Text(str(po["_id"]), **_val),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [ft.Text("Product:", **_info), ft.Text(product_name, **_val)],
                        spacing=8,
                    ),
                    ft.Row(
                        [ft.Text("Supplier:", **_info), ft.Text(supplier_name, **_val)],
                        spacing=8,
                    ),
                ],
                spacing=6,
            ),
            bgcolor=ft.Colors.with_opacity(0.04, ThemeColor.TEXT_PRIMARY),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )

        def _on_save(_e):
            ok = True
            if not dlg_status.value:
                dlg_status.error_text = "Please select a status"
                ok = False
            else:
                dlg_status.error_text = None
            try:
                new_qty = int(dlg_qty.value)
                dlg_qty.error = None
            except Exception:
                dlg_qty.error = "Enter a valid number"
                ok = False
                new_qty = 0
            if not ok:
                flet_page.update()
                return
            new_status = dlg_status.value
            _po_col.update_one(
                {"_id": po["_id"]},
                {
                    "$set": {
                        "quantity": new_qty,
                        "status": new_status,
                        "delay_flag": new_status != "Delivered",
                    }
                },
            )
            if new_status == "Delivered":
                p = _products_col.find_one({"product_id": po["product_id"]})
                if p:
                    _products_col.update_one(
                        {"product_id": po["product_id"]},
                        {
                            "$set": {
                                "current_stock": int(p.get("current_stock", 0))
                                + new_qty,
                                "updated_at": datetime.utcnow(),
                            }
                        },
                    )
            upd_dlg.open = False
            _load_all_pos()
            _render_po_table()
            show_toast(flet_page, f"Order status updated to '{new_status}'.")

        upd_dlg = open_form_dialog(
            flet_page,
            title="Update Purchase Order",
            fields=[
                info_box,
                build_vertical_spacer(10),
                ft.Row([dlg_qty, dlg_status], spacing=12),
            ],
            submit_label="Save",
            on_submit=_on_save,
            width=520,
            height=220,
        )

    po_search_results = ft.Column([], spacing=0)
    po_search_container = ft.Container(
        content=po_search_results,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border=ft.border.all(1, ThemeColor.BORDER_SUBTLE),
        border_radius=10,
        visible=False,
        padding=ft.padding.symmetric(vertical=4),
    )
    po_id_search = ft.TextField(
        label="Search Purchase Order ID…",
        color=ThemeColor.TEXT_PRIMARY,
        bgcolor=ThemeColor.SURFACE_PRIMARY,
        border_color=ThemeColor.BORDER_SUBTLE,
        focused_border_color=ThemeColor.ACCENT_VIOLET,
        label_style=ft.TextStyle(color=ThemeColor.TEXT_MUTED),
        border_radius=12,
        text_size=14,
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
    )

    _po_search_timer: list[threading.Timer | None] = [None]

    def _do_po_search(query: str) -> None:
        po_search_results.controls.clear()
        if not query:
            po_search_container.visible = False
            flet_page.update()
            return

        product_map, supplier_map = _build_lookup_maps(_ALL_POS)

        matches = []
        for po in _ALL_POS:
            prod_name = product_map.get(po.get("product_id", ""), "")
            if query in str(po["_id"]).lower() or query in prod_name.lower():
                matches.append(
                    (
                        po,
                        prod_name,
                        supplier_map.get(str(po.get("supplier_id", "")), ""),
                    )
                )
            if len(matches) >= 8:
                break

        if not matches:
            po_search_container.visible = False
            flet_page.update()
            return

        for po, prod_name, sup_name in matches:
            status = po.get("status", "Pending")
            sc = _status_color(status)

            def _make_pick(p=po):
                def _on(_e):
                    po_search_container.visible = False
                    po_id_search.value = ""
                    flet_page.update()
                    _open_po_update_dialog(p)

                return _on

            po_search_results.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        str(po["_id"]),
                                        size=11,
                                        color=ThemeColor.ACCENT_VIOLET,
                                        no_wrap=True,
                                    ),
                                    ft.Text(
                                        f"{prod_name} — {sup_name}",
                                        size=12,
                                        color=ThemeColor.TEXT_MUTED,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    status,
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                    color=sc,
                                ),
                                bgcolor=ft.Colors.with_opacity(0.12, sc),
                                border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    on_click=_make_pick(),
                    ink=True,
                    border_radius=8,
                )
            )
        po_search_container.visible = True
        flet_page.update()

    def _on_po_search_change(e):
        query = (e.control.value or "").strip().lower()
        if _po_search_timer[0]:
            _po_search_timer[0].cancel()
        t = threading.Timer(0.25, lambda: _do_po_search(query))
        _po_search_timer[0] = t
        t.start()

    po_id_search.on_change = _on_po_search_change

    def _validate_supplier() -> bool:
        return validate_all(
            flet_page,
            [
                (d_name, lambda v: validate_required(v, "Supplier name")),
                (d_email, validate_email),
                (d_contact, validate_phone),
                (
                    d_lead,
                    lambda v: validate_int_range(v, 1, 365)
                    and None
                    or ("Lead time must be 1–365 days" if v else None),
                ),
                (
                    d_reliability,
                    lambda v: validate_int_range(v, 1, 10)
                    and None
                    or ("Score must be 1–10" if v else None),
                ),
            ],
        )

    def _form_fields() -> list[ft.Control]:
        return [
            ft.Row([d_name], spacing=3, tight=True),
            ft.Row([d_contact, d_email], spacing=3, tight=True),
            ft.Row([d_address], spacing=3, tight=True),
            ft.Row([d_lead, d_reliability], spacing=3, tight=True),
        ]

    def _clear_fields() -> None:
        for f in [d_name, d_contact, d_email, d_address, d_lead, d_reliability]:
            f.value = ""
            f.error = None

    def _collect_payload() -> dict:
        return {
            "name": d_name.value.strip(),
            "contact": d_contact.value.strip(),
            "email": d_email.value.strip(),
            "address": d_address.value.strip(),
            "avg_lead_time": int(d_lead.value or 7),
            "reliability_score": int(d_reliability.value or 5),
        }

    def _open_add_dialog(e) -> None:
        dlg_is_edit["value"] = False
        selected_supplier["doc"] = None
        _clear_fields()

        def _on_submit(_e):
            if not _validate_supplier():
                return
            payload = _collect_payload()
            payload["created_at"] = datetime.utcnow()
            _suppliers_col.insert_one(payload)
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(flet_page, "Supplier added successfully.")

        dlg = open_form_dialog(
            flet_page,
            title="Add Supplier",
            fields=_form_fields(),
            submit_label="Add Supplier",
            on_submit=_on_submit,
            width=580,
            height=280,
        )

    def _open_edit_dialog(doc: dict) -> None:
        dlg_is_edit["value"] = True
        selected_supplier["doc"] = doc
        d_name.value = doc.get("name", "")
        d_contact.value = str(doc.get("contact", ""))
        d_email.value = doc.get("email", "")
        d_address.value = doc.get("address", "")
        d_lead.value = str(doc.get("avg_lead_time", ""))
        d_reliability.value = str(doc.get("reliability_score", ""))
        for f in [d_name, d_contact, d_email, d_address, d_lead, d_reliability]:
            f.error = None

        def _on_submit(_e):
            if not _validate_supplier():
                return
            _suppliers_col.update_one(
                {"_id": selected_supplier["doc"]["_id"]}, {"$set": _collect_payload()}
            )
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(flet_page, "Supplier updated successfully.")

        dlg = open_form_dialog(
            flet_page,
            title="Edit Supplier",
            fields=_form_fields(),
            submit_label="Save Changes",
            on_submit=_on_submit,
            width=580,
            height=280,
        )

    def _confirm_delete(doc: dict) -> None:
        dlg = open_confirm_dialog(
            flet_page,
            body_lines=[
                "Are you sure you want to delete the supplier:",
                f"'{doc.get('name', '')}'?",
                "This action cannot be undone.",
            ],
            on_confirm=lambda e: (
                _suppliers_col.delete_one({"_id": doc["_id"]}),
                close_dialog(flet_page, dlg),
                _load_all(),
                _apply_search(search_bar.value or ""),
                show_toast(flet_page, f"Supplier '{doc.get('name', '')}' deleted."),
            ),
        )

    csv_ctrl = CsvImportController(
        flet_page,
        collection=_suppliers_col,
        on_done=lambda: (_load_all(), _apply_search(search_bar.value or "")),
    )

    def _open_csv_picker(e) -> None:
        csv_ctrl.open(hint_text="Header row required. Existing IDs are skipped.")

    _load_all()
    _load_all_pos()
    _render_supplier_table(_ALL_SUPPLIERS)
    _render_po_table()
    _initializing["value"] = False

    total_suppliers = _suppliers_col.count_documents({})
    total_pos = _po_col.count_documents({})

    return ft.Column(
        [
            build_section_header(
                "Suppliers Management",
                "Manage your supplier network and order approvals",
                [
                    build_csv_import_button(_open_csv_picker),
                    build_filled_action_button(
                        "+ Add Supplier", on_click_handler=_open_add_dialog
                    ),
                ],
            ),
            build_vertical_spacer(18),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.LOCAL_SHIPPING,
                                "Total Suppliers",
                                total_suppliers,
                                None,
                                ThemeColor.ACCENT_VIOLET,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.RECEIPT,
                                "Purchase Orders",
                                total_pos,
                                None,
                                ThemeColor.ACCENT_GREEN,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.ACCESS_TIME,
                                "Avg Lead Time",
                                "8 days",
                                None,
                                ThemeColor.ACCENT_AMBER,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.STAR,
                                "Avg Reliability",
                                "7.5",
                                None,
                                ThemeColor.ACCENT_ROSE,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                ],
                spacing=16,
            ),
            build_vertical_spacer(16),
            build_table_card(supplier_datatable, search_bar=search_bar),
            build_vertical_spacer(14),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Supplier Order Approval",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            "Search by PO ID or product name, or click the edit icon in the table below.",
                            size=12,
                            color=ThemeColor.TEXT_MUTED,
                        ),
                        build_vertical_spacer(10),
                        ft.Stack(
                            [ft.Column([po_id_search, po_search_container], spacing=4)]
                        ),
                        build_vertical_spacer(12),
                        po_datatable,
                    ],
                    spacing=0,
                ),
                bgcolor=ThemeColor.CARD_BACKGROUND,
                border_radius=16,
                padding=22,
                border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
