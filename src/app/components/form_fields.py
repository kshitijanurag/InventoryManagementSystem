import re
from datetime import datetime
from typing import Callable

import flet as ft

from src.app.components.theme import ThemeColor

_FIELD_BASE = dict(
    color=ThemeColor.TEXT_PRIMARY,
    bgcolor=ThemeColor.SURFACE_PRIMARY,
    border_color=ThemeColor.BORDER_SUBTLE,
    focused_border_color=ThemeColor.ACCENT_VIOLET,
    label_style=ft.TextStyle(color=ThemeColor.TEXT_MUTED),
    border_radius=12,
    text_size=14,
    error_style=ft.TextStyle(color=ThemeColor.ACCENT_ROSE, size=11),
    helper=" ",
)

_DROPDOWN_BASE = dict(
    color=ThemeColor.TEXT_PRIMARY,
    bgcolor=ThemeColor.SURFACE_PRIMARY,
    border_color=ThemeColor.BORDER_SUBTLE,
    focused_border_color=ThemeColor.ACCENT_VIOLET,
    label_style=ft.TextStyle(color=ThemeColor.TEXT_MUTED),
    border_radius=12,
    error_style=ft.TextStyle(color=ThemeColor.ACCENT_ROSE, size=11),
    helper_text=" ",
)


def build_dialog_text_field(
    label: str,
    *,
    hint: str = "",
    width: int | None = None,
    expand: bool = False,
    multiline: bool = False,
    password: bool = False,
    disabled: bool = False,
    keyboard_type=None,
    value: str = "",
) -> ft.TextField:
    kw = dict(
        label=label,
        hint_text=hint,
        multiline=multiline,
        password=password,
        can_reveal_password=password,
        disabled=disabled,
        value=value,
        **_FIELD_BASE,
    )
    if width is not None:
        kw["width"] = width
    elif expand:
        kw["expand"] = True
    if keyboard_type:
        kw["keyboard_type"] = keyboard_type
    return ft.TextField(**kw)


def build_dialog_dropdown(
    label: str,
    options: list[ft.DropdownOption],
    *,
    value: str | None = None,
    width: int | None = None,
    expand: bool = False,
    **kwargs,
) -> ft.Dropdown:
    kw = dict(label=label, options=options, value=value, **_DROPDOWN_BASE)
    kw.update(kwargs)
    if width is not None:
        kw["width"] = width
    elif expand:
        kw["expand"] = True
    return ft.Dropdown(**kw)


def build_dialog_switch(
    label: str,
    *,
    value: bool = False,
    active_color: str = ThemeColor.ACCENT_VIOLET,
    on_change: Callable | None = None,
) -> ft.Switch:
    return ft.Switch(
        label=label,
        value=value,
        active_color=active_color,
        label_text_style=ft.TextStyle(color=ThemeColor.TEXT_SECONDARY, size=14),
        on_change=on_change,
    )


def build_date_picker_row(
    flet_page: ft.Page,
    label: str,
    *,
    initial_text: str = "Not selected",
    first_date: datetime | None = None,
    last_date: datetime | None = None,
    on_date_selected: Callable[[datetime], None] | None = None,
    date_format: str = "%d-%m-%Y",
) -> tuple[ft.Row, dict]:
    state = {"date": "", "dt": None}
    display = ft.Text(
        f"{label}: {initial_text}", size=13, color=ThemeColor.TEXT_SECONDARY
    )

    picker = ft.DatePicker(
        first_date=first_date or datetime(2000, 1, 1),
        last_date=last_date or datetime(2100, 12, 31),
    )

    def _on_change(e):
        if e.control.value:
            dt = e.control.value
            state["dt"] = dt
            state["date"] = dt.strftime(date_format)
            display.value = f"{label}: {state['date']}"
            flet_page.update()
            if on_date_selected:
                on_date_selected(dt)

    picker.on_change = _on_change
    flet_page.overlay.append(picker)

    btn = ft.OutlinedButton(
        f"Pick {label}",
        icon=ft.Icons.CALENDAR_TODAY,
        on_click=lambda _: (setattr(picker, "open", True), flet_page.update()),
        style=ft.ButtonStyle(
            color=ThemeColor.ACCENT_VIOLET,
            side=ft.BorderSide(1, ThemeColor.ACCENT_VIOLET),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    row = ft.Row(
        [btn, display], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    return row, state


def validate_required(value: str, field_name: str = "This field") -> str | None:
    if not value or not value.strip():
        return f"{field_name} is required"
    return None


def validate_email(value: str) -> str | None:
    if value and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        return "Enter a valid email address"
    return None


def validate_phone(value: str) -> str | None:
    if value and not re.match(r"^[\d\s\+\-\(\)]{6,20}$", value):
        return "Enter a valid phone number"
    return None


def validate_non_neg_float(value: str) -> str | None:
    if not value:
        return None
    try:
        if float(value) < 0:
            return "Must be a valid number ≥ 0"
    except ValueError:
        return "Must be a valid number ≥ 0"
    return None


def validate_non_neg_int(value: str) -> str | None:
    if not value:
        return None
    try:
        if int(value) < 0:
            return "Must be a whole number ≥ 0"
    except ValueError:
        return "Must be a whole number ≥ 0"
    return None


def validate_int_range(value: str, lo: int, hi: int) -> str | None:
    if not value:
        return None
    try:
        if not (lo <= int(value) <= hi):
            return f"Must be between {lo} and {hi}"
    except ValueError:
        return f"Must be a whole number between {lo} and {hi}"
    return None


def make_live_validator(
    flet_page: ft.Page,
    field: ft.TextField,
    check_fn: Callable[[str], str | None],
) -> None:
    def _handler(e):
        field.error = check_fn(field.value or "")
        flet_page.update()

    field.on_change = _handler


def validate_all(
    flet_page: ft.Page,
    fields_and_checks: list[tuple[ft.TextField, Callable[[str], str | None]]],
) -> bool:
    all_ok = True
    for field, check_fn in fields_and_checks:
        err = check_fn(field.value or "")
        field.error = err
        if err:
            all_ok = False
    flet_page.update()
    return all_ok
