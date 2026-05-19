import threading
import flet as ft
import flet_datatable2 as ftd
from datetime import datetime

from src.database.mongo_connection import get_inventory_database
from src.utilities.perf import PerfTimer
from src.app.components import (
    build_csv_import_button,
    build_vertical_spacer,
    build_section_header,
    build_filled_action_button,
    show_toast,
    build_dialog_text_field,
    make_live_validator,
    validate_required,
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
_col = _db["categories"]

_ALL_DOCS: list[dict] = []

_SORT_KEYS = ["_id", "name", "description", "created_at"]
_COL_SPECS = [
    ColSpec("ID", "_id"),
    ColSpec("Name", "name"),
    ColSpec("Description", "description"),
    ColSpec("Created", "created_at"),
    ColSpec("Actions", None),
]


def build_categories_page(flet_page: ft.Page) -> ft.Control:
    global _ALL_DOCS

    t = PerfTimer("categories_page")

    _cat_sort = {"col": 0, "asc": True}
    selected_doc = {"doc": None}
    dlg_is_edit = {"value": False}

    t.checkpoint("init: local state + sort config")

    def _on_sort_applied():
        _apply_search(search_bar.value or "")

    cat_datatable = build_datatable(_COL_SPECS, _cat_sort, _on_sort_applied)
    search_bar = build_search_bar("Search categories…")

    t.checkpoint("ui: build_datatable + search_bar")

    dlg_id_field = build_dialog_text_field("Category ID *", expand=True)
    dlg_name_field = build_dialog_text_field("Category Name *", expand=True)
    dlg_desc_field = build_dialog_text_field("Description", multiline=True, expand=True)

    t.checkpoint("ui: build dialog fields")

    _id_check_timer: list[threading.Timer | None] = [None]

    def _check_cat_id(v: str) -> str | None:
        if not v or not v.strip():
            return "Category ID is required"
        if not dlg_is_edit["value"] and _col.find_one({"_id": v.strip()}):
            return "Category ID already exists"
        return None

    def _debounced_id_validator(e):
        if _id_check_timer[0]:
            _id_check_timer[0].cancel()

        def _run():
            dlg_id_field.error = _check_cat_id(dlg_id_field.value or "")
            flet_page.update()

        t2 = threading.Timer(0.4, _run)
        _id_check_timer[0] = t2
        t2.start()

    dlg_id_field.on_change = _debounced_id_validator
    make_live_validator(
        flet_page, dlg_name_field, lambda v: validate_required(v, "Category name")
    )

    t.checkpoint("init: attach validators")

    _initializing = {"value": True}

    def _load_all() -> None:
        global _ALL_DOCS
        _ALL_DOCS = list(_col.find())

    def _render_table(docs: list[dict]) -> None:
        sorted_docs = sort_docs(docs, _cat_sort, _SORT_KEYS)
        rows = []
        for doc in sorted_docs:

            def _make_edit(d=doc):
                def _on(_):
                    _open_edit_dialog(d)

                return _on

            def _make_del(d=doc):
                def _on(_):
                    _confirm_delete(d)

                return _on

            rows.append(
                ftd.DataRow2(
                    cells=[
                        ft.DataCell(
                            ft.GestureDetector(
                                content=ft.Text(
                                    str(doc.get("_id", "")),
                                    size=12,
                                    color=ThemeColor.ACCENT_VIOLET,
                                    weight=ft.FontWeight.W_600,
                                ),
                                on_tap=_make_edit(),
                                mouse_cursor=ft.MouseCursor.CLICK,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                doc.get("name", ""),
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                (doc.get("description", "") or "")[:50],
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                str(doc.get("created_at", ""))[:10],
                                size=12,
                                color=ThemeColor.TEXT_MUTED,
                            )
                        ),
                        build_action_cell(
                            on_edit=_make_edit(),
                            on_delete=_make_del(),
                            edit_tooltip="Edit category",
                            delete_tooltip="Delete category",
                        ),
                    ]
                )
            )
        refresh_datatable(cat_datatable, rows, _cat_sort)
        if not _initializing["value"]:
            flet_page.update()

    def _apply_search(query: str) -> None:
        if not query.strip():
            _render_table(_ALL_DOCS)
            return
        scored = [
            (sc, d)
            for d in _ALL_DOCS
            if (
                sc := _fuzzy_score(
                    query,
                    f"{d.get('_id','')} {d.get('name','')} {d.get('description','')}",
                )
            )
            > 0
        ]
        scored.sort(key=lambda x: -x[0])
        _render_table([d for _, d in scored])

    search_bar.on_change = lambda e: _apply_search(e.control.value or "")

    def _validate_form() -> bool:
        return validate_all(
            flet_page,
            [
                (dlg_id_field, _check_cat_id),
                (dlg_name_field, lambda v: validate_required(v, "Category name")),
            ],
        )

    def _form_fields() -> list[ft.Control]:
        return [dlg_id_field, dlg_name_field, dlg_desc_field]

    def _open_add_dialog(e) -> None:
        dlg_is_edit["value"] = False
        selected_doc["doc"] = None
        dlg_id_field.value = dlg_name_field.value = dlg_desc_field.value = ""
        dlg_id_field.error = dlg_name_field.error = None
        dlg_id_field.read_only = False

        def _on_submit(_e):
            if not _validate_form():
                return
            _col.insert_one(
                {
                    "_id": dlg_id_field.value.strip(),
                    "name": dlg_name_field.value.strip(),
                    "description": dlg_desc_field.value.strip(),
                    "created_at": datetime.now().strftime("%Y-%m-%d"),
                }
            )
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(
                flet_page,
                f"Category '{dlg_name_field.value.strip()}' added successfully.",
            )

        dlg = open_form_dialog(
            flet_page,
            title="Add Category",
            fields=_form_fields(),
            submit_label="Add Category",
            on_submit=_on_submit,
            width=500,
            height=260,
        )

    def _open_edit_dialog(doc: dict) -> None:
        dlg_is_edit["value"] = True
        selected_doc["doc"] = doc
        dlg_id_field.value = str(doc.get("_id", ""))
        dlg_name_field.value = doc.get("name", "")
        dlg_desc_field.value = doc.get("description", "")
        dlg_id_field.read_only = True
        dlg_id_field.error = dlg_name_field.error = None

        def _on_submit(_e):
            if not _validate_form():
                return
            name = dlg_name_field.value.strip()
            _col.update_one(
                {"_id": selected_doc["doc"]["_id"]},
                {
                    "$set": {
                        "name": name,
                        "description": dlg_desc_field.value.strip(),
                    }
                },
            )
            dlg.open = False
            _load_all()
            _apply_search(search_bar.value or "")
            show_toast(flet_page, f"Category '{name}' updated successfully.")

        dlg = open_form_dialog(
            flet_page,
            title="Edit Category",
            fields=_form_fields(),
            submit_label="Save Changes",
            on_submit=_on_submit,
            width=500,
            height=260,
        )

    def _confirm_delete(doc: dict) -> None:
        dlg = open_confirm_dialog(
            flet_page,
            body_lines=[
                "Are you sure you want to delete the category:",
                f"'{doc.get('name', '')}'?",
                "This action cannot be undone.",
            ],
            on_confirm=lambda e: (
                _col.delete_one({"_id": doc["_id"]}),
                close_dialog(flet_page, dlg),
                _load_all(),
                _apply_search(search_bar.value or ""),
                show_toast(flet_page, f"Category '{doc.get('name', '')}' deleted."),
            ),
        )

    csv_ctrl = CsvImportController(
        flet_page,
        collection=_col,
        on_done=lambda: (_load_all(), _apply_search(search_bar.value or "")),
    )

    def _open_csv_picker(e) -> None:
        csv_ctrl.open(hint_text="Expected columns: _id (or id), name, description")

    _load_all()
    t.checkpoint(f"db: _col.find() → {len(_ALL_DOCS)} docs")

    _render_table(_ALL_DOCS)
    t.checkpoint(f"ui: build {len(_ALL_DOCS)} DataRow2 objects")

    _initializing["value"] = False

    result = ft.Column(
        [
            build_section_header(
                "Category Management",
                "Add, edit and delete product categories",
                [
                    build_csv_import_button(_open_csv_picker),
                    build_filled_action_button(
                        "+ Add Category", on_click_handler=_open_add_dialog
                    ),
                ],
            ),
            build_vertical_spacer(18),
            build_table_card(cat_datatable, search_bar=search_bar),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
    t.checkpoint("ui: assemble final ft.Column")
    t.done()
    return result
