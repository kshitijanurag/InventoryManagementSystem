import flet as ft
from src.app.components.theme import ThemeColor


def _dt2_kwargs() -> dict:
    return dict(
        bgcolor=ThemeColor.SURFACE_PRIMARY,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        border_radius=14,
        horizontal_lines=ft.BorderSide(0.8, ThemeColor.BORDER_DEFAULT),
        vertical_lines=ft.BorderSide(
            0.4, ft.Colors.with_opacity(0.06, ThemeColor.TEXT_PRIMARY)
        ),
        heading_row_color=ft.Colors.with_opacity(0.06, ThemeColor.TEXT_PRIMARY),
        heading_row_height=48,
        data_row_height=54,
        column_spacing=14,
        divider_thickness=0,
        show_checkbox_column=False,
        data_row_color={
            ft.ControlState.HOVERED: ft.Colors.with_opacity(
                0.07, ThemeColor.ACCENT_VIOLET
            ),
            ft.ControlState.SELECTED: ft.Colors.with_opacity(
                0.12, ThemeColor.ACCENT_VIOLET
            ),
        },
    )
