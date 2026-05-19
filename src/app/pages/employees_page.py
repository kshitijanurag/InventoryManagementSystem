import flet as ft
import flet_datatable2 as ftd
from datetime import datetime
from pymongo import MongoClient

from src.app.components import (
    build_csv_import_button,
    build_vertical_spacer,
    build_section_header,
    build_stat_card,
    build_filled_action_button,
    show_toast,
    build_dialog_text_field,
    build_dialog_dropdown,
    build_date_picker_row,
    make_live_validator,
    validate_required,
    validate_email,
    validate_phone,
    validate_non_neg_float,
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

_collection = MongoClient("mongodb://localhost:27017/")["inventory"]["employees"]
_ALL_EMPLOYEES: list[dict] = []

_SORT_KEYS = ["employee_id", "name", "role", "gender", "salary", "performance_score"]
_COL_SPECS = [
    ColSpec("Employee ID", "employee_id"),
    ColSpec("Name", "name"),
    ColSpec("Role", "role"),
    ColSpec("Gender", "gender"),
    ColSpec("Salary", "salary", numeric=True),
    ColSpec("Performance Score", "performance_score", numeric=True),
    ColSpec("Actions", None),
]


def _to_int(val: str) -> int:
    try:
        return int(val)
    except Exception:
        return 0


def _to_bool(val: str) -> bool:
    return val == "True"


def build_employees_page(flet_page: ft.Page) -> ft.Control:
    global _ALL_EMPLOYEES

    _emp_sort = {"col": 0, "asc": True}
    selected_id = {"value": None}
    dlg_is_edit = {"value": False}

    def _on_sort_applied():
        _apply_search(search_bar.value or "")

    emp_datatable = build_datatable(_COL_SPECS, _emp_sort, _on_sort_applied)
    search_bar = build_search_bar("Search employees…")

    d_emp_id = build_dialog_text_field("Employee ID *", expand=True)
    d_name = build_dialog_text_field("Full Name *", expand=True)
    d_contact = build_dialog_text_field("Phone / Contact", expand=True)
    d_email = build_dialog_text_field("Email", expand=True)
    d_password = build_dialog_text_field("Password", password=True, expand=True)
    d_salary = build_dialog_text_field(
        "Salary", expand=True, keyboard_type=ft.KeyboardType.NUMBER
    )
    d_address = build_dialog_text_field("Address", expand=True)
    d_perf = build_dialog_text_field(
        "Performance Score (0-100)", expand=True, keyboard_type=ft.KeyboardType.NUMBER
    )
    d_sales = build_dialog_text_field(
        "Total Sales", expand=True, keyboard_type=ft.KeyboardType.NUMBER
    )
    d_gender = build_dialog_dropdown(
        "Gender",
        [ft.DropdownOption(o) for o in ["Male", "Female", "Other"]],
        expand=True,
    )
    d_role = build_dialog_dropdown(
        "Role",
        [
            ft.DropdownOption(o)
            for o in ["Employee", "Admin", "Lead", "Manager", "Director", "Expert"]
        ],
        expand=True,
    )
    d_anomaly = build_dialog_dropdown(
        "Anomaly Flag", [ft.DropdownOption(o) for o in ["False", "True"]], expand=True
    )

    dob_row, dob_state = build_date_picker_row(
        flet_page,
        "Date of Birth",
        first_date=datetime(1950, 1, 1),
        last_date=datetime.now(),
        date_format="%d-%m-%Y",
    )

    def _check_emp_id(v: str) -> str | None:
        if not v or not v.strip():
            return "Employee ID is required"
        if not dlg_is_edit["value"] and _collection.find_one(
            {"employee_id": v.strip()}
        ):
            return "Employee ID already exists"
        return None

    make_live_validator(flet_page, d_emp_id, _check_emp_id)
    make_live_validator(flet_page, d_name, lambda v: validate_required(v, "Full name"))
    make_live_validator(flet_page, d_email, validate_email)
    make_live_validator(flet_page, d_contact, validate_phone)
    make_live_validator(flet_page, d_salary, validate_non_neg_float)
    make_live_validator(flet_page, d_perf, lambda v: validate_int_range(v, 0, 100))

    def _load_all() -> None:
        global _ALL_EMPLOYEES
        _ALL_EMPLOYEES = list(_collection.find())

    def _render_table(docs: list[dict]) -> None:
        sorted_docs = sort_docs(docs, _emp_sort, _SORT_KEYS)
        rows = []
        for emp in sorted_docs:

            def _make_edit(e=emp):
                def _on(_):
                    _open_edit_dialog(e)

                return _on

            def _make_del(e=emp):
                def _on(_):
                    _confirm_delete(e)

                return _on

            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                emp.get("employee_id", ""),
                                size=11,
                                color=ThemeColor.TEXT_MUTED,
                                no_wrap=True,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                emp.get("name", ""),
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                emp.get("role", ""),
                                size=12,
                                color=ThemeColor.TEXT_SECONDARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                emp.get("gender", ""),
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(emp.get("salary", "")),
                                size=12,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(emp.get("performance_score", "")),
                                size=12,
                                color=ThemeColor.ACCENT_VIOLET,
                            )
                        ),
                        build_action_cell(
                            on_edit=_make_edit(),
                            on_delete=_make_del(),
                            edit_tooltip="Edit employee",
                            delete_tooltip="Delete employee",
                        ),
                    ]
                )
            )
        refresh_datatable(emp_datatable, rows, _emp_sort)
        flet_page.update()

    def _apply_search(query: str) -> None:
        if not query.strip():
            _render_table(_ALL_EMPLOYEES)
            return
        scored = [
            (sc, e)
            for e in _ALL_EMPLOYEES
            if (
                sc := _fuzzy_score(
                    query,
                    f"{e.get('name','')} {e.get('employee_id','')} {e.get('role','')} {e.get('email','')}",
                )
            )
            > 0
        ]
        scored.sort(key=lambda x: -x[0])
        _render_table([d for _, d in scored])

    search_bar.on_change = lambda e: _apply_search(e.control.value or "")

    def _form_fields() -> list[ft.Control]:
        return [
            ft.Row([d_emp_id, d_name], spacing=12),
            ft.Row([d_gender, d_role], spacing=12),
            ft.Row([d_contact, d_email], spacing=12),
            ft.Row([d_salary, d_perf, d_sales], spacing=12),
            ft.Row([d_anomaly, d_password], spacing=12),
            d_address,
            dob_row,
        ]

    def _clear_fields() -> None:
        for f in [
            d_emp_id,
            d_name,
            d_contact,
            d_email,
            d_password,
            d_salary,
            d_address,
            d_perf,
            d_sales,
        ]:
            f.value = ""
            f.error = None
        d_gender.value = d_role.value = d_anomaly.value = None
        dob_state["date"] = ""

    def _validate_form() -> bool:
        return validate_all(
            flet_page,
            [
                (d_emp_id, _check_emp_id),
                (d_name, lambda v: validate_required(v, "Full name")),
                (d_email, validate_email),
                (d_contact, validate_phone),
                (d_salary, validate_non_neg_float),
                (d_perf, lambda v: validate_int_range(v, 0, 100)),
            ],
        )

    def _collect_payload() -> dict:
        return {
            "employee_id": d_emp_id.value.strip(),
            "name": d_name.value.strip(),
            "gender": d_gender.value,
            "contact": d_contact.value.strip(),
            "dob": dob_state["date"],
            "email": d_email.value.strip(),
            "password": d_password.value,
            "role": d_role.value,
            "salary": _to_int(d_salary.value),
            "address": d_address.value.strip(),
            "performance_score": _to_int(d_perf.value),
            "total_sales": _to_int(d_sales.value),
            "anomaly_flag": _to_bool(d_anomaly.value or "False"),
        }

    def _open_add_dialog(e) -> None:
        dlg_is_edit["value"] = False
        _clear_fields()
        d_emp_id.read_only = False

        def _on_submit(_e):
            if not _validate_form():
                return
            _collection.insert_one(_collect_payload())
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(flet_page, "Employee added successfully.")

        dlg = open_form_dialog(
            flet_page,
            title="Add Employee",
            fields=_form_fields(),
            submit_label="Add Employee",
            on_submit=_on_submit,
            width=620,
            height=420,
        )

    def _open_edit_dialog(emp: dict) -> None:
        dlg_is_edit["value"] = True
        selected_id["value"] = emp["_id"]
        d_emp_id.value = emp.get("employee_id", "")
        d_emp_id.read_only = True
        d_name.value = emp.get("name", "")
        d_gender.value = emp.get("gender") or None
        d_contact.value = str(emp.get("contact", "") or "")
        d_email.value = emp.get("email", "") or ""
        d_password.value = emp.get("password", "") or ""
        d_role.value = emp.get("role") or None
        d_salary.value = str(emp.get("salary", ""))
        d_address.value = emp.get("address", "")
        d_perf.value = str(emp.get("performance_score", ""))
        d_sales.value = str(emp.get("total_sales", ""))
        d_anomaly.value = "True" if emp.get("anomaly_flag") else "False"
        dob_state["date"] = emp.get("dob", "")
        for f in [d_emp_id, d_name, d_email, d_contact, d_salary, d_perf]:
            f.error = None

        def _on_submit(_e):
            if not _validate_form():
                return
            payload = _collect_payload()
            payload.pop("employee_id", None)
            _collection.update_one({"_id": selected_id["value"]}, {"$set": payload})
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(flet_page, "Employee updated successfully.")

        dlg = open_form_dialog(
            flet_page,
            title="Edit Employee",
            fields=_form_fields(),
            submit_label="Save Changes",
            on_submit=_on_submit,
            width=620,
            height=420,
        )

    def _confirm_delete(emp: dict) -> None:
        dlg = open_confirm_dialog(
            flet_page,
            body_lines=[
                "Are you sure you want to delete the employee:",
                f"'{emp.get('name', '')}'?",
                "This action cannot be undone.",
            ],
            on_confirm=lambda e: (
                _collection.delete_one({"_id": emp["_id"]}),
                close_dialog(flet_page, dlg),
                _load_all(),
                _apply_search(search_bar.value or ""),
                show_toast(flet_page, f"Employee '{emp.get('name', '')}' deleted."),
            ),
        )

    csv_ctrl = CsvImportController(
        flet_page,
        collection=_collection,
        on_done=lambda: (_load_all(), _apply_search(search_bar.value or "")),
    )

    def _open_csv_picker(e) -> None:
        csv_ctrl.open(hint_text="Header row required. Existing IDs are skipped.")

    _load_all()
    _render_table(_ALL_EMPLOYEES)
    total = _collection.count_documents({})

    return ft.Column(
        [
            build_section_header(
                "Employee Management",
                "Full staff directory with performance tracking",
                [
                    build_csv_import_button(_open_csv_picker),
                    build_filled_action_button(
                        "+ Add Employee", on_click_handler=_open_add_dialog
                    ),
                ],
            ),
            build_vertical_spacer(14),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.PEOPLE,
                                "Total Employees",
                                total,
                                None,
                                ThemeColor.ACCENT_VIOLET,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    )
                ],
                spacing=16,
            ),
            build_vertical_spacer(14),
            build_table_card(emp_datatable, search_bar=search_bar),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
