import os
import flet as ft
import flet_datatable2 as ftd
from datetime import datetime
from pymongo import ReturnDocument
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4

from src.database.mongo_connection import get_inventory_database
from src.app.components import (
    build_vertical_spacer,
    build_glow_status_dot,
    build_section_header,
    show_toast,
    build_dialog_text_field,
    build_dialog_dropdown,
    build_date_picker_row,
    make_live_validator,
    validate_required,
    validate_email,
    validate_phone,
    open_form_dialog,
    open_confirm_dialog,
    close_dialog,
    ColSpec,
    build_datatable,
    build_search_bar,
    refresh_datatable,
    sort_docs,
    ThemeColor,
)
from src.app.components.datatable2 import _dt2_kwargs
from src.utilities.fuzzy_search import _fuzzy_score

_db = get_inventory_database()
_products_col = _db["products"]
_customers_col = _db["customers"]
_sales_col = _db["sales"]
_invoices_col = _db["invoices"]
_counters_col = _db["counters"]


def _get_next_id(counter_name: str, prefix: str, base: int) -> str:
    c = _counters_col.find_one_and_update(
        {"_id": counter_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if c["seq"] < base:
        _counters_col.update_one({"_id": counter_name}, {"$set": {"seq": base}})
        return f"{prefix}{base}"
    return f"{prefix}{c['seq']}"


def _update_stock(product_id: str, qty: int) -> None:
    p = _products_col.find_one({"product_id": product_id})
    if p:
        _products_col.update_one(
            {"product_id": product_id},
            {
                "$set": {
                    "current_stock": max(0, int(p.get("current_stock", 0)) - qty),
                    "updated_at": datetime.utcnow(),
                }
            },
        )


def _generate_pdf(
    invoice_number,
    bill_date,
    total,
    discount_pct,
    gst_pct,
    net,
    payment_method,
    customer_name,
    customer_contact,
    customer_email,
    employee_id,
    cart_items,
) -> str:
    pdf_path = os.path.join(
        os.path.expanduser("~"), "Downloads", f"{invoice_number}.pdf"
    )
    try:
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )
        ss = getSampleStyleSheet()
        title = ParagraphStyle(
            "title",
            parent=ss["Title"],
            fontSize=20,
            spaceAfter=4,
            textColor=rl_colors.HexColor("#5B4CFF"),
        )
        sub = ParagraphStyle(
            "sub", parent=ss["Normal"], fontSize=9, textColor=rl_colors.grey
        )
        bold = ParagraphStyle(
            "bold",
            parent=ss["Normal"],
            fontSize=10,
            leading=14,
            fontName="Helvetica-Bold",
        )
        norm = ParagraphStyle("norm", parent=ss["Normal"], fontSize=10, leading=14)
        right = ParagraphStyle(
            "right",
            parent=ss["Normal"],
            fontSize=11,
            leading=16,
            alignment=2,
            fontName="Helvetica-Bold",
        )

        elems = [
            Paragraph("Inventory Manager", title),
            Paragraph("Smart Billing System", sub),
            Spacer(1, 8 * mm),
            HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor("#5B4CFF")),
            Spacer(1, 5 * mm),
            Table(
                [
                    [
                        Paragraph(f"<b>Invoice:</b> {invoice_number}", norm),
                        Paragraph(f"<b>Date:</b> {bill_date}", norm),
                    ],
                    [
                        Paragraph(f"<b>Customer:</b> {customer_name}", norm),
                        Paragraph(f"<b>Payment:</b> {payment_method}", norm),
                    ],
                    [
                        Paragraph(f"<b>Contact:</b> {customer_contact}", norm),
                        Paragraph(f"<b>Email:</b> {customer_email}", norm),
                    ],
                    [Paragraph(f"<b>Employee ID:</b> {employee_id}", norm), ""],
                ],
                colWidths=["50%", "50%"],
            ),
            Spacer(1, 5 * mm),
            HRFlowable(width="100%", thickness=0.5, color=rl_colors.lightgrey),
            Spacer(1, 4 * mm),
        ]

        table_data = [
            [
                Paragraph("<b>#</b>", bold),
                Paragraph("<b>Product</b>", bold),
                Paragraph("<b>Price</b>", bold),
                Paragraph("<b>Qty</b>", bold),
                Paragraph("<b>Subtotal</b>", bold),
            ]
        ]
        for i, item in enumerate(cart_items, 1):
            subtotal = item["price"] * item["qty"]
            table_data.append(
                [
                    Paragraph(str(i), norm),
                    Paragraph(item["name"], norm),
                    Paragraph(f"₹{item['price']:,.2f}", norm),
                    Paragraph(str(item["qty"]), norm),
                    Paragraph(f"₹{subtotal:,.2f}", norm),
                ]
            )

        items_table = Table(table_data, colWidths=["8%", "42%", "18%", "10%", "22%"])
        items_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#5B4CFF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [rl_colors.HexColor("#F8F8FF"), rl_colors.white],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.4, rl_colors.lightgrey),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elems.append(items_table)
        elems.append(Spacer(1, 5 * mm))

        gst_amount = net * gst_pct / 100
        grand = net + gst_amount
        totals = Table(
            [
                ["", Paragraph("Subtotal:", norm), Paragraph(f"₹{total:,.2f}", right)],
                [
                    "",
                    Paragraph(f"Discount ({discount_pct}%):", norm),
                    Paragraph(f"-₹{total*discount_pct/100:,.2f}", right),
                ],
                [
                    "",
                    Paragraph(f"GST ({gst_pct}%):", norm),
                    Paragraph(f"+₹{gst_amount:,.2f}", right),
                ],
                [
                    "",
                    Paragraph("<b>Grand Total:</b>", bold),
                    Paragraph(f"<b>₹{grand:,.2f}</b>", right),
                ],
            ],
            colWidths=["50%", "25%", "25%"],
        )
        totals.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (1, 3), (-1, 3), 1, rl_colors.HexColor("#5B4CFF")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elems += [
            totals,
            Spacer(1, 8 * mm),
            HRFlowable(width="100%", thickness=0.5, color=rl_colors.lightgrey),
            Spacer(1, 3 * mm),
            Paragraph("Thank you for your business!", sub),
        ]
        doc.build(elems)
        return pdf_path
    except Exception as err:
        print(f"[PDF] Error: {err}")
        return ""


def build_sales_page(flet_page: ft.Page) -> ft.Control:

    cart: list[dict] = []
    all_products: list[dict] = []
    prod_sort = {"col": 0, "asc": True}
    bill_date_val = {"date": datetime.now().strftime("%Y-%m-%d")}
    last_pdf_path = {"path": ""}

    f_cust_name = build_dialog_text_field("Customer Name *", expand=True)
    f_cust_contact = build_dialog_text_field("Contact / Phone *", expand=True)
    f_cust_email = build_dialog_text_field("Email *", expand=True)
    f_cust_address = build_dialog_text_field("Address *", expand=True)
    f_emp_id = build_dialog_text_field("Employee ID", expand=True, disabled=False)
    f_notes = build_dialog_text_field("Notes / Remarks", expand=True)
    f_discount = build_dialog_text_field(
        "Discount %", value="0", width=120, keyboard_type=ft.KeyboardType.NUMBER
    )
    f_gst = build_dialog_text_field(
        "GST %", value="0", width=100, keyboard_type=ft.KeyboardType.NUMBER
    )

    _emp_docs = list(
        _db["employees"].find({}, {"name": 1, "employee_id": 1}).limit(100)
    )
    _emp_id_map = {
        str(e.get("employee_id", str(e.get("_id", "")))): str(e.get("employee_id", ""))
        for e in _emp_docs
    }
    emp_dd = build_dialog_dropdown(
        "Select Employee *",
        [
            ft.DropdownOption(
                key=str(e.get("employee_id", str(e.get("_id", "")))),
                text=f"{e.get('name','?')}  ({e.get('employee_id','?')})",
            )
            for e in _emp_docs
        ],
        expand=True,
    )

    def _on_emp_select(e):
        selected_key = emp_dd.value or ""
        emp_dd.error_text = None if selected_key else "Please select an employee"
        emp_id_val = _emp_id_map.get(selected_key, selected_key)
        f_emp_id.value = emp_id_val
        f_emp_id.read_only = True
        f_emp_id.bgcolor = ft.Colors.with_opacity(0.04, ThemeColor.TEXT_PRIMARY)
        flet_page.update()

    emp_dd.on_change = _on_emp_select

    def _num_check(v, allow_float=False):
        if not v:
            return None
        try:
            val = float(v) if allow_float else int(v)
            return None if val >= 0 else "Must be 0–100"
        except Exception:
            return "Must be a valid number"

    make_live_validator(
        flet_page, f_cust_name, lambda v: validate_required(v, "Customer name")
    )
    make_live_validator(flet_page, f_cust_contact, validate_phone)
    make_live_validator(flet_page, f_cust_email, validate_email)
    make_live_validator(
        flet_page, f_cust_address, lambda v: validate_required(v, "Address")
    )
    make_live_validator(flet_page, f_discount, lambda v: _num_check(v, True))
    make_live_validator(flet_page, f_gst, lambda v: _num_check(v, True))

    bill_date_display = ft.Text(
        f"Bill Date: {bill_date_val['date']}", size=13, color=ThemeColor.TEXT_SECONDARY
    )

    def _on_bill_date(dt: datetime):
        bill_date_val["date"] = dt.strftime("%Y-%m-%d")
        bill_date_display.value = f"Bill Date: {bill_date_val['date']}"
        flet_page.update()

    bill_date_row, _ = build_date_picker_row(
        flet_page,
        "Bill Date",
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_date_selected=_on_bill_date,
    )

    payment_dd = build_dialog_dropdown(
        "Payment Method",
        [
            ft.DropdownOption(m)
            for m in ["Cash", "Card", "UPI", "Net Banking", "Cheque"]
        ],
        value="Cash",
        width=160,
    )

    cart_table = ftd.DataTable2(
        expand=True,
        columns=[
            ftd.DataColumn2(
                ft.Text(
                    h, size=11, color=ThemeColor.TEXT_MUTED, weight=ft.FontWeight.W_700
                )
            )
            for h in ["#", "Product", "Price", "Quantity", "Subtotal", "Actions"]
        ],
        rows=[],
        **_dt2_kwargs(),
    )

    total_text = ft.Text("Subtotal: ₹0.00", size=13, color=ThemeColor.TEXT_SECONDARY)
    discount_line = ft.Text("Discount: ₹0.00", size=13, color=ThemeColor.ACCENT_AMBER)
    gst_line = ft.Text("GST: ₹0.00", size=13, color=ThemeColor.TEXT_SECONDARY)
    net_text = ft.Text(
        "Grand Total: ₹0.00",
        size=20,
        weight=ft.FontWeight.BOLD,
        color=ThemeColor.ACCENT_VIOLET,
    )

    pdf_section = ft.Container(visible=False)
    pdf_outer = ft.Container(visible=False)
    clear_cart_btn = ft.Ref[ft.OutlinedButton]()

    empty_cart_msg = ft.Container(
        visible=True,
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.SHOPPING_CART_OUTLINED,
                    color=ThemeColor.TEXT_MUTED,
                    size=56,
                ),
                build_vertical_spacer(10),
                ft.Text(
                    "Your cart is empty",
                    size=17,
                    color=ThemeColor.TEXT_MUTED,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Click the  icon next to any product to add it to the cart.",
                    size=13,
                    color=ThemeColor.TEXT_MUTED,
                ),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(vertical=48),
        alignment=ft.alignment.Alignment(0, 0),
    )

    def _show_pdf(pdf_path: str) -> None:
        import subprocess
        import sys

        try:
            if sys.platform == "win32":
                os.startfile(pdf_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pdf_path])
            else:
                subprocess.Popen(["xdg-open", pdf_path])
        except Exception:
            pass
        pdf_section.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.PICTURE_AS_PDF,
                            color=ThemeColor.ACCENT_ROSE,
                            size=20,
                        ),
                        ft.Text(
                            "Invoice Generated",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=8,
                ),
                build_vertical_spacer(8),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.CHECK_CIRCLE,
                                        color=ThemeColor.ACCENT_GREEN,
                                        size=16,
                                    ),
                                    ft.Text(
                                        "PDF saved and opened in your default viewer.",
                                        size=13,
                                        color=ThemeColor.ACCENT_GREEN,
                                    ),
                                ],
                                spacing=8,
                            ),
                            build_vertical_spacer(6),
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.FOLDER_OPEN,
                                        color=ThemeColor.TEXT_MUTED,
                                        size=14,
                                    ),
                                    ft.Text(
                                        pdf_path,
                                        size=11,
                                        color=ThemeColor.TEXT_MUTED,
                                        selectable=True,
                                        expand=True,
                                    ),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=0,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.05, ThemeColor.ACCENT_GREEN),
                    border=ft.border.all(
                        1, ft.Colors.with_opacity(0.2, ThemeColor.ACCENT_GREEN)
                    ),
                    border_radius=10,
                    padding=12,
                ),
                build_vertical_spacer(8),
                ft.OutlinedButton(
                    "Open PDF Again",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda e: _show_pdf(pdf_path),
                    style=ft.ButtonStyle(
                        color=ThemeColor.ACCENT_VIOLET,
                        side=ft.BorderSide(1, ThemeColor.ACCENT_VIOLET),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                ),
            ],
            spacing=0,
        )
        pdf_section.visible = True
        flet_page.update()

    def _recalc():
        subtotal = sum(i["price"] * i["qty"] for i in cart)
        disc_pct = float(f_discount.value or 0)
        gst_pct = float(f_gst.value or 0)
        after_disc = subtotal - subtotal * disc_pct / 100
        grand = after_disc + after_disc * gst_pct / 100
        return subtotal, disc_pct, gst_pct, grand

    def _refresh_cart() -> None:
        subtotal, disc_pct, gst_pct, grand = _recalc()
        rows = []
        for idx, item in enumerate(cart):
            sub = item["price"] * item["qty"]

            def _make_edit(i=idx):
                return lambda e: _open_edit_cart_dialog(i)

            def _make_remove(i=idx):
                return lambda e: _confirm_remove(i)

            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(str(idx + 1), size=12, color=ThemeColor.TEXT_MUTED)
                        ),
                        ft.DataCell(
                            ft.Text(
                                item["name"],
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"₹{item['price']:,.2f}",
                                size=12,
                                color=ThemeColor.TEXT_SECONDARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    str(item["qty"]),
                                    size=13,
                                    color=ThemeColor.ACCENT_TEAL,
                                    weight=ft.FontWeight.W_600,
                                ),
                                bgcolor=ft.Colors.with_opacity(
                                    0.10, ThemeColor.ACCENT_TEAL
                                ),
                                border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"₹{sub:,.2f}",
                                size=13,
                                color=ThemeColor.ACCENT_GREEN,
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        ft.Icons.EDIT,
                                        icon_color=ThemeColor.ACCENT_VIOLET,
                                        icon_size=16,
                                        tooltip="Edit",
                                        on_click=_make_edit(),
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=8)
                                        ),
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color=ThemeColor.ACCENT_ROSE,
                                        icon_size=16,
                                        tooltip="Remove",
                                        on_click=_make_remove(),
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=8)
                                        ),
                                    ),
                                ],
                                spacing=2,
                            )
                        ),
                    ]
                )
            )
        cart_table.rows = rows
        has_items = bool(cart)
        cart_table.visible = has_items
        empty_cart_msg.visible = not has_items
        if clear_cart_btn.current:
            clear_cart_btn.current.disabled = not has_items
            clear_cart_btn.current.style = ft.ButtonStyle(
                color=ThemeColor.ACCENT_ROSE if has_items else ThemeColor.TEXT_MUTED,
                side=ft.BorderSide(
                    1.5,
                    ThemeColor.ACCENT_ROSE if has_items else ThemeColor.BORDER_SUBTLE,
                ),
                shape=ft.RoundedRectangleBorder(radius=14),
            )
        disc_amt = subtotal * disc_pct / 100
        gst_amt = (subtotal - disc_amt) * gst_pct / 100
        total_text.value = f"Subtotal: ₹{subtotal:,.2f}"
        discount_line.value = f"Discount ({disc_pct}%): -₹{disc_amt:,.2f}"
        gst_line.value = f"GST ({gst_pct}%): +₹{gst_amt:,.2f}"
        net_text.value = f"Grand Total: ₹{grand:,.2f}"
        flet_page.update()

    def _open_edit_cart_dialog(idx: int) -> None:
        item = cart[idx]
        qty_f = build_dialog_text_field(
            "Quantity",
            value=str(item["qty"]),
            width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        price_f = build_dialog_text_field(
            "Unit Price",
            value=str(item["price"]),
            width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _on_save(_e):
            try:
                new_qty = int(qty_f.value)
                if new_qty <= 0:
                    raise ValueError
            except Exception:
                qty_f.error = "Enter valid quantity > 0"
                flet_page.update()
                return
            cart[idx]["qty"] = new_qty
            cart[idx]["price"] = float(price_f.value)
            dlg.open = False
            _refresh_cart()
            show_toast(flet_page, f"'{item['name']}' updated in cart.")

        dlg = open_form_dialog(
            flet_page,
            title=f"Edit — {item['name']}",
            fields=[ft.Row([qty_f, price_f], spacing=12)],
            submit_label="Save",
            on_submit=_on_save,
            width=380,
            height=110,
        )

    def _confirm_remove(idx: int) -> None:
        name = cart[idx]["name"]
        dlg = open_confirm_dialog(
            flet_page,
            title="Remove from Cart",
            confirm_label="Remove",
            body_lines=[f"Remove '{name}' from the cart?"],
            on_confirm=lambda e: (
                cart.pop(idx),
                close_dialog(flet_page, dlg),
                _refresh_cart(),
                show_toast(flet_page, f"'{name}' removed from cart."),
            ),
        )

    def _open_add_to_cart(product: dict) -> None:
        try:
            stock = int(product.get("current_stock", 0))
        except Exception:
            stock = 0
        stock_color = (
            ThemeColor.ACCENT_ROSE
            if stock == 0
            else ThemeColor.ACCENT_AMBER if stock < 10 else ThemeColor.ACCENT_GREEN
        )
        qty_f = build_dialog_text_field(
            "Quantity", value="1", width=130, keyboard_type=ft.KeyboardType.NUMBER
        )
        price_f = build_dialog_text_field(
            "Unit Price",
            value=str(product.get("selling_price", 0)),
            width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _on_add(_e):
            try:
                qty = int(qty_f.value)
                if qty <= 0:
                    raise ValueError
            except Exception:
                qty_f.error = "Enter valid quantity > 0"
                flet_page.update()
                return
            if qty > stock:
                qty_f.error = f"Only {stock} in stock"
                flet_page.update()
                return
            price = float(price_f.value)
            for item in cart:
                if item["product_id"] == product["product_id"]:
                    item["qty"] += qty
                    item["price"] = price
                    dlg.open = False
                    _refresh_cart()
                    show_toast(
                        flet_page, f"'{product['name']}' quantity updated in cart."
                    )
                    return
            cart.append(
                {
                    "product_id": product["product_id"],
                    "name": product["name"],
                    "price": price,
                    "qty": qty,
                }
            )
            dlg.open = False
            _refresh_cart()
            show_toast(flet_page, f"'{product['name']}' added to cart.")

        dlg = open_form_dialog(
            flet_page,
            title=f"Add to Cart — {product['name']}",
            submit_label="Add to Cart",
            submit_color=ThemeColor.ACCENT_GREEN,
            fields=[
                ft.Row(
                    [
                        ft.Icon(ft.Icons.INVENTORY_2, color=stock_color, size=16),
                        ft.Text(
                            f"Available stock: {stock}", size=13, color=stock_color
                        ),
                    ],
                    spacing=6,
                ),
                build_vertical_spacer(6),
                ft.Row([qty_f, price_f], spacing=12),
            ],
            on_submit=_on_add,
            width=360,
            height=160,
        )

    _PROD_COL_SPECS = [
        ColSpec("ID", "product_id"),
        ColSpec("Name", "name"),
        ColSpec("Category", "category_name"),
        ColSpec("Price", "selling_price", numeric=True),
        ColSpec("Stock", "current_stock", numeric=True),
        ColSpec("Action", None),
    ]
    _PROD_SORT_KEYS = [
        "product_id",
        "name",
        "category_name",
        "selling_price",
        "current_stock",
    ]

    def _on_prod_sort():
        _render_products(all_products)

    product_table = build_datatable(_PROD_COL_SPECS, prod_sort, _on_prod_sort)

    def _render_products(docs: list[dict]) -> None:
        sorted_docs = sort_docs(docs, prod_sort, _PROD_SORT_KEYS)
        rows = []
        for p in sorted_docs:
            try:
                stock = int(p.get("current_stock", 0))
            except:
                stock = 0
            sc = (
                ThemeColor.ACCENT_ROSE
                if stock == 0
                else ThemeColor.ACCENT_AMBER if stock < 10 else ThemeColor.ACCENT_GREEN
            )
            cat = (p.get("category_name") or "").strip() or "—"
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
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(ft.Text(cat, size=11, color=ThemeColor.TEXT_MUTED)),
                        ft.DataCell(
                            ft.Text(
                                f"₹{float(p.get('selling_price', 0)):,.2f}",
                                size=13,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    build_glow_status_dot(sc, 8),
                                    ft.Text(
                                        str(stock),
                                        size=12,
                                        color=sc,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                ],
                                spacing=5,
                            )
                        ),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.ADD_SHOPPING_CART,
                                icon_color=ThemeColor.ACCENT_GREEN,
                                icon_size=18,
                                tooltip="Add to cart",
                                on_click=lambda e, prod=p: _open_add_to_cart(prod),
                                disabled=(stock == 0),
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                            )
                        ),
                    ]
                )
            )
        refresh_datatable(product_table, rows, prod_sort)
        flet_page.update()

    def _load_products(query: str = "") -> None:
        all_products.clear()
        all_products.extend(list(_products_col.find().limit(200)))
        if query.strip():
            scored = [
                (sc, p)
                for p in all_products
                if (
                    sc := _fuzzy_score(
                        query,
                        f"{p.get('name','')} {p.get('product_id','')} {p.get('category_name','')}",
                    )
                )
                > 0
            ]
            scored.sort(key=lambda x: -x[0])
            _render_products([d for _, d in scored])
        else:
            _render_products(all_products)

    search_bar = build_search_bar("Search products by name, ID, category…")
    search_bar.on_change = lambda e: _load_products(e.control.value or "")

    def _handle_generate_bill(e) -> None:
        if not cart:
            show_toast(flet_page, "Cart is empty.", is_error=True)
            return
        f_cust_name.error = validate_required(f_cust_name.value, "Customer name")
        f_cust_contact.error = validate_phone(f_cust_contact.value)
        f_cust_email.error = validate_email(f_cust_email.value)
        f_cust_address.error = validate_required(f_cust_address.value, "Address")
        emp_dd.error_text = None if emp_dd.value else "Please select an employee"
        flet_page.update()
        if any(
            [
                f_cust_name.error,
                f_cust_contact.error,
                f_cust_email.error,
                f_cust_address.error,
                emp_dd.error_text,
            ]
        ):
            return

        subtotal, disc_pct, gst_pct, grand = _recalc()
        invoice_id = _get_next_id("invoice", "INV", 11000)
        invoice_number = f"INV{int(datetime.now().timestamp())}"
        customer_id = _get_next_id("customer", "C", 501)

        _customers_col.insert_one(
            {
                "customer_id": customer_id,
                "name": f_cust_name.value.strip(),
                "contact": f_cust_contact.value.strip(),
                "email": f_cust_email.value.strip(),
                "address": f_cust_address.value.strip(),
                "created_at": bill_date_val["date"],
            }
        )
        for item in cart:
            _sales_col.insert_one(
                {
                    "sale_id": _get_next_id("sale", "s", 35136),
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "product_id": item["product_id"],
                    "customer_id": customer_id,
                    "employee_id": f_emp_id.value.strip(),
                    "quantity": item["qty"],
                    "qty": item["qty"],
                    "total": item["price"] * item["qty"],
                    "date": bill_date_val["date"],
                    "payment_method": payment_dd.value,
                }
            )
            _update_stock(item["product_id"], item["qty"])

        gst_amt = (subtotal - subtotal * disc_pct / 100) * gst_pct / 100
        _invoices_col.insert_one(
            {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "customer_id": customer_id,
                "employee_id": f_emp_id.value.strip(),
                "items": cart.copy(),
                "subtotal": subtotal,
                "discount_pct": disc_pct,
                "gst_pct": gst_pct,
                "gst_amount": gst_amt,
                "net": grand,
                "payment_method": payment_dd.value,
                "bill_date": bill_date_val["date"],
                "created_at": datetime.utcnow(),
            }
        )

        pdf_path = _generate_pdf(
            invoice_number,
            bill_date_val["date"],
            subtotal,
            disc_pct,
            gst_pct,
            grand,
            payment_dd.value,
            f_cust_name.value.strip(),
            f_cust_contact.value.strip(),
            f_cust_email.value.strip(),
            f_emp_id.value.strip(),
            cart.copy(),
        )

        cart.clear()
        for f in [
            f_cust_name,
            f_cust_contact,
            f_cust_email,
            f_cust_address,
            f_emp_id,
            f_notes,
        ]:
            f.value = ""
        f_discount.value = "0"
        f_gst.value = "0"
        emp_dd.value = None
        emp_dd.error_text = None
        for f in [
            f_cust_name,
            f_cust_contact,
            f_cust_email,
            f_cust_address,
            f_discount,
            f_gst,
        ]:
            f.error = None
        _refresh_cart()
        _load_products()
        show_toast(flet_page, f"Bill generated! Invoice: {invoice_number}")
        if pdf_path:
            _show_pdf(pdf_path)
            pdf_outer.visible = True
            flet_page.update()

    def _handle_clear_cart(e) -> None:
        if not cart:
            return
        dlg = open_confirm_dialog(
            flet_page,
            title="Clear Cart",
            confirm_label="Clear",
            body_lines=["Remove all items from the cart?"],
            on_confirm=lambda e: (
                cart.clear(),
                close_dialog(flet_page, dlg),
                _refresh_cart(),
                show_toast(flet_page, "Cart cleared."),
            ),
        )

    _load_products()
    cart_table.visible = False

    pdf_outer.content = ft.Container(
        content=pdf_section,
        bgcolor=ft.Colors.with_opacity(0.03, ThemeColor.TEXT_PRIMARY),
        border_radius=12,
        border=ft.border.all(1, ThemeColor.BORDER_SUBTLE),
        padding=16,
    )

    def _section_header_row(icon, label):
        return ft.Row(
            [
                ft.Icon(icon, color=ThemeColor.ACCENT_VIOLET, size=20),
                ft.Text(
                    label,
                    size=16,
                    weight=ft.FontWeight.W_700,
                    color=ThemeColor.TEXT_PRIMARY,
                ),
            ],
            spacing=8,
        )

    def _sub_card(content):
        return ft.Container(
            content=content,
            bgcolor=ft.Colors.with_opacity(0.03, ThemeColor.TEXT_PRIMARY),
            border_radius=12,
            padding=16,
            border=ft.border.all(1, ThemeColor.BORDER_SUBTLE),
        )

    products_panel = ft.Container(
        content=ft.Column(
            [
                _section_header_row(ft.Icons.INVENTORY_2, "Products"),
                build_vertical_spacer(10),
                ft.Row([search_bar], expand=False),
                build_vertical_spacer(10),
                product_table,
            ],
            spacing=0,
        ),
        padding=20,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=16,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
    )

    billing_panel = ft.Container(
        content=ft.Column(
            [
                _section_header_row(ft.Icons.RECEIPT_LONG, "Billing"),
                build_vertical_spacer(14),
                _sub_card(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.PERSON,
                                        color=ThemeColor.ACCENT_TEAL,
                                        size=15,
                                    ),
                                    ft.Text(
                                        "Customer Details",
                                        size=13,
                                        weight=ft.FontWeight.W_600,
                                        color=ThemeColor.TEXT_SECONDARY,
                                    ),
                                ],
                                spacing=6,
                            ),
                            build_vertical_spacer(10),
                            ft.Row(
                                [f_cust_name, f_cust_contact, f_cust_email], spacing=12
                            ),
                            build_vertical_spacer(8),
                            f_cust_address,
                        ],
                        spacing=0,
                    )
                ),
                build_vertical_spacer(12),
                _sub_card(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.ARTICLE,
                                        color=ThemeColor.ACCENT_VIOLET,
                                        size=15,
                                    ),
                                    ft.Text(
                                        "Bill Details",
                                        size=13,
                                        weight=ft.FontWeight.W_600,
                                        color=ThemeColor.TEXT_SECONDARY,
                                    ),
                                ],
                                spacing=6,
                            ),
                            build_vertical_spacer(10),
                            ft.Row([emp_dd, f_emp_id], spacing=12),
                            build_vertical_spacer(8),
                            ft.Row(
                                [payment_dd, bill_date_row],
                                spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            build_vertical_spacer(8),
                            ft.Row([f_discount, f_gst, f_notes], spacing=12),
                        ],
                        spacing=0,
                    )
                ),
            ],
            spacing=0,
        ),
        padding=20,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=16,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
    )

    cart_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.SHOPPING_CART,
                            color=ThemeColor.ACCENT_GREEN,
                            size=20,
                        ),
                        ft.Text(
                            "Cart",
                            size=16,
                            weight=ft.FontWeight.W_700,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            "Click the cart icon on any product to add items",
                            size=12,
                            color=ThemeColor.TEXT_MUTED,
                            italic=True,
                        ),
                    ],
                    spacing=8,
                ),
                build_vertical_spacer(14),
                empty_cart_msg,
                cart_table,
                build_vertical_spacer(14),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [total_text, ft.Container(expand=True), discount_line]
                            ),
                            ft.Row([gst_line, ft.Container(expand=True), net_text]),
                        ],
                        spacing=8,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.04, ThemeColor.TEXT_PRIMARY),
                    border_radius=12,
                    padding=ft.padding.symmetric(horizontal=20, vertical=14),
                ),
                build_vertical_spacer(14),
                ft.Row(
                    [
                        ft.FilledButton(
                            "Generate Bill",
                            icon=ft.Icons.RECEIPT_LONG,
                            on_click=_handle_generate_bill,
                            height=52,
                            expand=True,
                            style=ft.ButtonStyle(
                                bgcolor=ThemeColor.ACCENT_VIOLET,
                                color=ThemeColor.TEXT_PRIMARY,
                                shape=ft.RoundedRectangleBorder(radius=14),
                            ),
                        ),
                        ft.OutlinedButton(
                            "Clear Cart",
                            ref=clear_cart_btn,
                            icon=ft.Icons.DELETE_SWEEP,
                            on_click=_handle_clear_cart,
                            height=52,
                            disabled=True,
                            style=ft.ButtonStyle(
                                color=ThemeColor.TEXT_MUTED,
                                side=ft.BorderSide(1.5, ThemeColor.BORDER_SUBTLE),
                                shape=ft.RoundedRectangleBorder(radius=14),
                            ),
                        ),
                    ],
                    spacing=12,
                ),
                build_vertical_spacer(14),
                pdf_outer,
            ],
            spacing=0,
        ),
        padding=20,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=16,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
    )

    return ft.Column(
        [
            build_section_header(
                "Smart Billing System", "Products · Cart · Invoice · PDF"
            ),
            build_vertical_spacer(16),
            products_panel,
            build_vertical_spacer(14),
            billing_panel,
            build_vertical_spacer(14),
            cart_panel,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )
