from typing import Callable

import flet as ft
import flet_datatable2 as ftd

from src.app.components.theme import ThemeColor
from src.app.components.datatable2 import _dt2_kwargs


class ColSpec:
    __slots__ = ("label", "sort_key", "numeric", "width")

    def __init__(
        self,
        label: str,
        sort_key: str | None = None,
        *,
        numeric: bool = False,
        width: int | None = None,
    ):
        self.label = label
        self.sort_key = sort_key
        self.numeric = numeric
        self.width = width


def build_sortable_col(
    label: str,
    col_index: int,
    sort_state: dict,
    on_sort_applied: Callable,
    *,
    numeric: bool = False,
) -> ftd.DataColumn2:
    def _on_sort(e):
        sort_state["col"] = col_index
        sort_state["asc"] = e.ascending
        on_sort_applied()

    return ftd.DataColumn2(
        ft.Text(
            label,
            size=12,
            color=ThemeColor.TEXT_MUTED,
            weight=ft.FontWeight.W_700,
        ),
        on_sort=_on_sort,
        numeric=numeric,
    )


def build_datatable(
    col_specs: list[ColSpec],
    sort_state: dict,
    on_sort_applied: Callable,
) -> ftd.DataTable2:
    columns: list[ftd.DataColumn2] = []

    for i, spec in enumerate(col_specs):
        is_last = i == len(col_specs) - 1
        if spec.sort_key is None or is_last:
            col = ftd.DataColumn2(
                ft.Text(
                    spec.label,
                    size=12,
                    color=ThemeColor.TEXT_MUTED,
                    weight=ft.FontWeight.W_700,
                ),
                numeric=spec.numeric,
            )
        else:
            col = build_sortable_col(
                spec.label, i, sort_state, on_sort_applied, numeric=spec.numeric
            )
        if spec.width:
            col.fixed_width = spec.width
        columns.append(col)

    return ftd.DataTable2(
        expand=True,
        columns=columns,
        rows=[],
        sort_column_index=0,
        sort_ascending=True,
        **_dt2_kwargs(),
    )


def refresh_datatable(
    table: ftd.DataTable2,
    rows: list[ftd.DataRow2],
    sort_state: dict,
) -> None:
    table.rows = rows
    table.sort_column_index = sort_state["col"]
    table.sort_ascending = sort_state["asc"]


def sort_docs(
    docs: list[dict],
    sort_state: dict,
    sort_keys: list[str],
) -> list[dict]:
    col = sort_state["col"]
    key = sort_keys[col] if col < len(sort_keys) else sort_keys[0]
    return sorted(
        docs,
        key=lambda d: str(d.get(key, "") or "").lower(),
        reverse=not sort_state["asc"],
    )


def build_search_bar(
    hint: str = "Search…",
    *,
    on_change: Callable | None = None,
    value: str = "",
) -> ft.SearchBar:
    bar = ft.SearchBar(
        expand=True,
        bar_hint_text=hint,
        bar_bgcolor=ThemeColor.SURFACE_PRIMARY,
        bar_border_side=ft.BorderSide(1, ThemeColor.BORDER_SUBTLE),
        bar_hint_text_style=ft.TextStyle(color=ThemeColor.TEXT_MUTED, size=14),
        bar_text_style=ft.TextStyle(color=ThemeColor.TEXT_PRIMARY, size=14),
        bar_elevation=0,
        bar_shape=ft.RoundedRectangleBorder(radius=12),
        view_bgcolor=ThemeColor.CARD_BACKGROUND,
        value=value,
    )
    if on_change:
        bar.on_change = on_change
    return bar


def build_table_card(
    table: ftd.DataTable2,
    *,
    search_bar: ft.SearchBar | None = None,
    extra_toolbar_controls: list[ft.Control] | None = None,
) -> ft.Container:
    toolbar_items: list[ft.Control] = []
    if search_bar:
        toolbar_items.append(search_bar)
    if extra_toolbar_controls:
        toolbar_items.extend(extra_toolbar_controls)

    col_children: list[ft.Control] = []
    if toolbar_items:
        col_children.append(ft.Row(toolbar_items, spacing=12))
        col_children.append(ft.Container(height=14))
    col_children.append(table)

    return ft.Container(
        content=ft.Column(col_children, spacing=0),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=16,
        padding=22,
        expand=True,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
    )


def build_action_cell(
    *,
    on_edit: Callable | None = None,
    on_delete: Callable | None = None,
    edit_tooltip: str = "Edit",
    delete_tooltip: str = "Delete",
    extra_buttons: list[ft.Control] | None = None,
) -> ft.DataCell:
    buttons: list[ft.Control] = []

    if on_edit:
        buttons.append(
            ft.IconButton(
                ft.Icons.EDIT,
                icon_color=ThemeColor.ACCENT_VIOLET,
                icon_size=16,
                tooltip=edit_tooltip,
                on_click=on_edit,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            )
        )

    if on_delete:
        buttons.append(
            ft.IconButton(
                ft.Icons.DELETE,
                icon_color=ThemeColor.ACCENT_ROSE,
                icon_size=16,
                tooltip=delete_tooltip,
                on_click=on_delete,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            )
        )

    if extra_buttons:
        buttons.extend(extra_buttons)

    return ft.DataCell(ft.Row(buttons, spacing=4))
