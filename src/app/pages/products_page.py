import flet as ft
import flet_datatable2 as ftd

from src.app.components import (
    build_csv_import_button,
    build_vertical_spacer,
    build_section_header,
    build_stat_card,
    build_filled_action_button,
    build_glow_status_dot,
    show_toast,
    build_dialog_text_field,
    build_dialog_dropdown,
    make_live_validator,
    validate_required,
    validate_non_neg_float,
    validate_non_neg_int,
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
    sort_docs,
    ThemeColor,
)
from src.utilities.fuzzy_search import _fuzzy_score
from src.database.mongo_connection import get_inventory_database
from datetime import datetime

_db = get_inventory_database()
_product_col = _db["products"]
_categories_col = _db["categories"]
_suppliers_col = _db["suppliers"]

_cached_products = None


def _get_all_products() -> list:
    return list(_product_col.find({}, {"_id": 0}))


def _build_cat_map(db_categories: list) -> dict:
    result = {}
    for c in db_categories:
        result[str(c.get("_id", ""))] = c.get("name", "")
        result[str(c.get("category_id", ""))] = c.get("name", "")
    return result


def _build_sup_map(db_suppliers: list) -> dict:
    return {str(s.get("_id", "")): s.get("name", "") for s in db_suppliers}


def _resolve_category(product: dict, cat_map: dict) -> str:
    name = product.get("category_name", "").strip()
    if name:
        return name
    cid = product.get("category_id", "")
    return cat_map.get(str(cid), cid) if cid else "—"


def _resolve_supplier(product: dict, sup_map: dict) -> str:
    name = product.get("supplier_name", "").strip()
    if name:
        return name
    sid = product.get("supplier_id", "")
    return sup_map.get(str(sid), sid) if sid else "—"


def _stock_color(p: dict) -> str:
    stock = int(p.get("current_stock", 0))
    reorder = int(p.get("reorder_point", 0))
    if stock == 0:
        return ThemeColor.ACCENT_ROSE
    if stock < reorder:
        return ThemeColor.ACCENT_AMBER
    return ThemeColor.ACCENT_GREEN


def _to_int(val) -> int:
    try:
        return int(val)
    except:
        return 0


def _to_float(val) -> float:
    try:
        return float(val)
    except:
        return 0.0


def _is_abc(v: str) -> bool:
    return not v or v.upper() in ("A", "B", "C")


def _is_xyz(v: str) -> bool:
    return not v or v.upper() in ("X", "Y", "Z")


def _open_add_product_dialog(
    flet_page, refresh_callback, db_categories, db_suppliers, cat_map, sup_map
):

    def _ff(label, ktype=None, w=280):
        return build_dialog_text_field(label, width=w, keyboard_type=ktype)

    f_product_id = _ff("Product ID")
    f_name = _ff("Product Name")
    f_sku = _ff("SKU")
    f_cost_price = _ff("Cost Price", ft.KeyboardType.NUMBER)
    f_selling_price = _ff("Selling Price", ft.KeyboardType.NUMBER)
    f_stock = _ff("Current Stock", ft.KeyboardType.NUMBER)
    f_safety_stock = _ff("Safety Stock", ft.KeyboardType.NUMBER)
    f_lead_time = _ff("Lead Time Days", ft.KeyboardType.NUMBER)
    f_reorder = _ff("Reorder Point", ft.KeyboardType.NUMBER)
    f_abc = _ff("ABC Class (A/B/C)")
    f_xyz = _ff("XYZ Class (X/Y/Z)")
    f_turnover = _ff("Turnover Ratio", ft.KeyboardType.NUMBER)
    f_risk = _ff("Risk Score", ft.KeyboardType.NUMBER)

    f_category = build_dialog_dropdown(
        "Category",
        [
            ft.DropdownOption(key=str(c.get("_id", "")), text=str(c.get("name", "")))
            for c in db_categories
        ],
        width=280,
    )
    f_supplier = build_dialog_dropdown(
        "Supplier",
        [
            ft.DropdownOption(key=str(s.get("_id", "")), text=str(s.get("name", "")))
            for s in db_suppliers
        ],
        width=280,
    )

    make_live_validator(
        flet_page, f_product_id, lambda v: validate_required(v, "Product ID")
    )
    make_live_validator(
        flet_page, f_name, lambda v: validate_required(v, "Product Name")
    )
    make_live_validator(flet_page, f_cost_price, validate_non_neg_float)
    make_live_validator(flet_page, f_selling_price, validate_non_neg_float)
    make_live_validator(flet_page, f_stock, validate_non_neg_int)
    make_live_validator(flet_page, f_safety_stock, validate_non_neg_int)
    make_live_validator(flet_page, f_lead_time, validate_non_neg_int)
    make_live_validator(flet_page, f_reorder, validate_non_neg_int)
    make_live_validator(flet_page, f_turnover, validate_non_neg_float)
    make_live_validator(flet_page, f_risk, validate_non_neg_float)
    make_live_validator(
        flet_page, f_abc, lambda v: None if _is_abc(v) else "Must be A, B, or C"
    )
    make_live_validator(
        flet_page, f_xyz, lambda v: None if _is_xyz(v) else "Must be X, Y, or Z"
    )

    def _on_submit(_e):
        ok = validate_all(
            flet_page,
            [
                (f_product_id, lambda v: validate_required(v, "Product ID")),
                (f_name, lambda v: validate_required(v, "Product Name")),
                (f_cost_price, validate_non_neg_float),
                (f_selling_price, validate_non_neg_float),
                (f_stock, validate_non_neg_int),
                (f_safety_stock, validate_non_neg_int),
                (f_lead_time, validate_non_neg_int),
                (f_reorder, validate_non_neg_int),
                (f_turnover, validate_non_neg_float),
                (f_risk, validate_non_neg_float),
                (f_abc, lambda v: None if _is_abc(v) else "Must be A, B, or C"),
                (f_xyz, lambda v: None if _is_xyz(v) else "Must be X, Y, or Z"),
            ],
        )
        if not ok:
            return
        category_id = f_category.value or ""
        supplier_id = f_supplier.value or ""
        category_name = cat_map.get(category_id, category_id)
        supplier_name = sup_map.get(supplier_id, supplier_id)
        _product_col.insert_one(
            {
                "product_id": f_product_id.value.strip(),
                "name": f_name.value.strip(),
                "sku": f_sku.value.strip(),
                "category_id": category_id,
                "category_name": category_name,
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "cost_price": _to_int(f_cost_price.value),
                "selling_price": _to_int(f_selling_price.value),
                "current_stock": _to_int(f_stock.value),
                "safety_stock": _to_int(f_safety_stock.value),
                "lead_time_days": _to_int(f_lead_time.value),
                "reorder_point": _to_int(f_reorder.value),
                "abc_class": f_abc.value.strip(),
                "xyz_class": f_xyz.value.strip(),
                "turnover_ratio": _to_int(f_turnover.value),
                "risk_score": _to_int(f_risk.value),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
        )
        dlg.open = False
        flet_page.update()
        refresh_callback()
        show_toast(flet_page, f"Product '{f_name.value.strip()}' added successfully.")

    dlg = open_form_dialog(
        flet_page,
        title="Add New Product",
        fields=[
            ft.Row([f_product_id, f_name], spacing=12),
            ft.Row([f_sku, f_category], spacing=12),
            ft.Row([f_supplier, f_cost_price], spacing=12),
            ft.Row([f_selling_price, f_stock], spacing=12),
            ft.Row([f_safety_stock, f_lead_time], spacing=12),
            ft.Row([f_reorder, f_abc], spacing=12),
            ft.Row([f_xyz, f_turnover], spacing=12),
            ft.Row([f_risk], spacing=12),
        ],
        submit_label="Add Product",
        on_submit=_on_submit,
        width=620,
        height=440,
    )


def _open_edit_product_dialog(
    flet_page, product, db_categories, db_suppliers, cat_map, sup_map, refresh_callback
):

    f_name = build_dialog_text_field(
        "Product Name", value=product.get("name", ""), expand=True
    )
    f_stock = build_dialog_text_field(
        "Stock",
        value=str(product.get("current_stock", 0)),
        expand=True,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    f_price = build_dialog_text_field(
        "Selling Price",
        value=str(product.get("selling_price", 0)),
        expand=True,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    f_reorder = build_dialog_text_field(
        "Reorder Level",
        value=str(product.get("reorder_point", 0)),
        expand=True,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    f_lead_time = build_dialog_text_field(
        "Lead Time Days",
        value=str(product.get("lead_time_days", 7)),
        expand=True,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    f_turnover = build_dialog_text_field(
        "Turnover Ratio",
        value=str(product.get("turnover_ratio", 1)),
        expand=True,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    raw_cat_id = str(product.get("category_id", "") or "")
    cat_option_keys = [str(c.get("_id", "")) for c in db_categories]
    current_cat_id = (
        raw_cat_id
        if raw_cat_id in cat_option_keys
        else next(
            (
                str(c.get("_id", ""))
                for c in db_categories
                if str(c.get("category_id", "")) == raw_cat_id
                or c.get("name", "") == product.get("category_name", "")
            ),
            "",
        )
    )
    f_category = build_dialog_dropdown(
        "Category",
        [
            ft.DropdownOption(key=str(c.get("_id", "")), text=str(c.get("name", "")))
            for c in db_categories
        ],
        value=current_cat_id or None,
        expand=True,
    )

    raw_sup_id = str(product.get("supplier_id", "") or "")
    sup_option_keys = [str(s.get("_id", "")) for s in db_suppliers]
    current_sup_id = (
        raw_sup_id
        if raw_sup_id in sup_option_keys
        else next(
            (
                str(s.get("_id", ""))
                for s in db_suppliers
                if s.get("name", "") == product.get("supplier_name", "")
            ),
            "",
        )
    )
    f_supplier = build_dialog_dropdown(
        "Supplier",
        [
            ft.DropdownOption(key=str(s.get("_id", "")), text=str(s.get("name", "")))
            for s in db_suppliers
        ],
        value=current_sup_id or None,
        expand=True,
    )

    def _on_save(_e):
        category_id = f_category.value or current_cat_id
        supplier_id = f_supplier.value or current_sup_id
        _product_col.update_one(
            {"product_id": product["product_id"]},
            {
                "$set": {
                    "name": f_name.value,
                    "category_id": category_id,
                    "category_name": cat_map.get(category_id, category_id),
                    "current_stock": int(f_stock.value or 0),
                    "selling_price": float(f_price.value or 0),
                    "reorder_point": int(f_reorder.value or 0),
                    "lead_time_days": int(f_lead_time.value or 7),
                    "turnover_ratio": int(f_turnover.value or 1),
                    "supplier_id": supplier_id,
                    "supplier_name": sup_map.get(supplier_id, supplier_id),
                }
            },
        )
        dlg.open = False
        flet_page.update()
        refresh_callback()
        show_toast(flet_page, f"Product '{f_name.value}' updated successfully.")

    dlg = open_form_dialog(
        flet_page,
        title="Edit Product",
        fields=[
            f_name,
            ft.Row([f_category, f_supplier], spacing=12),
            ft.Row([f_stock, f_price], spacing=12),
            ft.Row([f_reorder, f_lead_time], spacing=12),
            ft.Row([f_turnover], spacing=12),
        ],
        submit_label="Save Changes",
        on_submit=_on_save,
        width=500,
        height=420,
    )


def build_products_page(
    flet_page,
    filtered_products=None,
    search_value="",
    selected_category="All Categories",
):
    global _cached_products

    _prod_sort = {"col": 0, "asc": True}
    db_categories = list(
        _categories_col.find({}, {"name": 1, "category_id": 1}).limit(50)
    )
    db_suppliers = list(_suppliers_col.find({}, {"name": 1}).limit(50))
    cat_map = _build_cat_map(db_categories)
    sup_map = _build_sup_map(db_suppliers)

    if _cached_products is None:
        _cached_products = _get_all_products()
    products = _cached_products if filtered_products is None else filtered_products

    _COL_SPECS = [
        ColSpec("ID", "product_id"),
        ColSpec("Name", "name"),
        ColSpec("Category", "category_id"),
        ColSpec("Stock", "current_stock", numeric=True),
        ColSpec("Price", "selling_price", numeric=True),
        ColSpec("Supplier", "supplier_id"),
        ColSpec("Actions", None),
    ]
    _SORT_KEYS = [
        "product_id",
        "name",
        "category_id",
        "current_stock",
        "selling_price",
        "supplier_id",
    ]

    def _on_sort():
        _apply_filters(search_bar.value or "")

    product_datatable = build_datatable(_COL_SPECS, _prod_sort, _on_sort)
    search_bar = build_search_bar("Search by Name / ID / SKU…", value=search_value)

    def _build_rows(docs: list) -> list:
        sorted_docs = sort_docs(docs, _prod_sort, _SORT_KEYS)
        rows = []
        for p in sorted_docs:
            ic = _stock_color(p)
            cat_name = _resolve_category(p, cat_map)
            sup_name = _resolve_supplier(p, sup_map)

            def _make_edit(prod=p):
                def _on(_):
                    def _after():
                        global _cached_products
                        _cached_products = _get_all_products()
                        _refresh_table(_cached_products)

                    _open_edit_product_dialog(
                        flet_page,
                        prod,
                        db_categories,
                        db_suppliers,
                        cat_map,
                        sup_map,
                        _after,
                    )

                return _on

            def _make_del(prod=p):
                def _on(_):
                    _confirm_delete(prod)

                return _on

            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                p.get("product_id", ""),
                                size=11,
                                color=ThemeColor.TEXT_MUTED,
                                no_wrap=True,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                p.get("name", ""),
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(cat_name, size=12, color=ThemeColor.TEXT_MUTED)
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    build_glow_status_dot(ic, 10),
                                    ft.Text(
                                        str(p.get("current_stock", 0)),
                                        size=13,
                                        color=ic,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                ],
                                spacing=7,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"₹{float(p.get('selling_price', 0)):,.2f}",
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(sup_name, size=12, color=ThemeColor.TEXT_SECONDARY)
                        ),
                        build_action_cell(
                            on_edit=_make_edit(),
                            on_delete=_make_del(),
                            edit_tooltip="Edit product",
                            delete_tooltip="Delete product",
                        ),
                    ]
                )
            )
        return rows

    def _refresh_table(docs: list) -> None:
        product_datatable.rows = _build_rows(docs)
        product_datatable.sort_column_index = _prod_sort["col"]
        product_datatable.sort_ascending = _prod_sort["asc"]
        flet_page.update()

    def _confirm_delete(product: dict) -> None:
        dlg = open_confirm_dialog(
            flet_page,
            body_lines=[
                "Are you sure you want to delete the product:",
                f"'{product.get('name', '')}'?",
                "This action cannot be undone.",
            ],
            on_confirm=lambda e: _do_delete(product, dlg),
        )

    def _do_delete(product: dict, dlg) -> None:
        global _cached_products
        name = product.get("name", "")
        _product_col.delete_one({"product_id": product["product_id"]})
        close_dialog(flet_page, dlg)
        _cached_products = _get_all_products()
        _refresh_table(_cached_products)
        show_toast(flet_page, f"Product '{name}' deleted.")

    def _apply_filters(search_text: str) -> None:
        filtered = _cached_products
        if search_text.strip():
            scored = [
                (sc, p)
                for p in filtered
                if (
                    sc := _fuzzy_score(
                        search_text,
                        f"{p.get('name','')} {p.get('product_id','')} {p.get('sku','')} "
                        f"{_resolve_category(p, cat_map)} {_resolve_supplier(p, sup_map)}",
                    )
                )
                > 0
            ]
            scored.sort(key=lambda x: -x[0])
            filtered = [p for _, p in scored]
        _refresh_table(filtered)

    search_bar.on_change = lambda e: _apply_filters(e.control.value.strip())

    def _handle_add_product(e) -> None:
        def _after():
            global _cached_products
            _cached_products = _get_all_products()
            _refresh_table(_cached_products)

        _open_add_product_dialog(
            flet_page, _after, db_categories, db_suppliers, cat_map, sup_map
        )

    def _refresh_after_csv():
        global _cached_products
        _cached_products = _get_all_products()
        _refresh_table(_cached_products)

    csv_ctrl = CsvImportController(
        flet_page, collection=_product_col, on_done=_refresh_after_csv
    )

    def _open_csv_picker(e) -> None:
        csv_ctrl.open(hint_text="Header row required. Existing IDs are skipped.")

    _refresh_table(products)

    total = len(products)
    in_stock = sum(1 for p in products if int(p.get("current_stock", 0)) > 0)
    low_stock = sum(
        1
        for p in products
        if 0 < int(p.get("current_stock", 0)) < int(p.get("reorder_point", 0))
    )
    out_of_stock = sum(1 for p in products if int(p.get("current_stock", 0)) == 0)

    return ft.Column(
        [
            build_section_header(
                "Products Management",
                "Manage your product catalog",
                [
                    build_csv_import_button(_open_csv_picker),
                    build_filled_action_button(
                        "Add Product", ft.Icons.ADD, _handle_add_product
                    ),
                ],
            ),
            build_vertical_spacer(22),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.INVENTORY,
                                "Total Products",
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
                                ft.Icons.CHECK_CIRCLE,
                                "In Stock",
                                in_stock,
                                None,
                                ThemeColor.ACCENT_GREEN,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.WARNING,
                                "Low Stock",
                                low_stock,
                                None,
                                ThemeColor.ACCENT_AMBER,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.CANCEL,
                                "Out of Stock",
                                out_of_stock,
                                None,
                                ThemeColor.ACCENT_ROSE,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                ],
                spacing=16,
            ),
            build_vertical_spacer(18),
            build_table_card(product_datatable, search_bar=search_bar),
        ],
        expand=True,
        spacing=0,
    )
