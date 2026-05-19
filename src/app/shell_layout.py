from __future__ import annotations
from datetime import datetime

import flet as ft

from src.app.components.primitive_components import (
    build_nav_section_label,
    build_horizontal_divider,
)
from src.app.components.theme import (
    ThemeColor,
    NAVIGATION_ITEM_DEFINITIONS,
    NAVIGATION_GROUP_STRUCTURE,
    SIDEBAR_WIDTH_PX,
    NAV_ITEM_HEIGHT_PX,
)
from src.app.services import _FALLBACK_ALERTS


def build_application_sidebar(
    currently_active_route_key: str,
    on_nav_item_click_callback,
    on_logout_click_callback,
    authenticated_user_session_data: dict | None = None,
) -> ft.Container:
    nav_group_sections = _build_all_nav_group_sections(
        currently_active_route_key, on_nav_item_click_callback
    )
    logo_header = _build_sidebar_logo_header()
    profile_footer = _build_sidebar_profile_footer(
        authenticated_user_session_data,
        on_logout_click_callback,
    )

    return ft.Container(
        width=SIDEBAR_WIDTH_PX,
        bgcolor=ThemeColor.SURFACE_PRIMARY,
        border=ft.border.only(right=ft.BorderSide(1, ThemeColor.BORDER_DEFAULT)),
        content=ft.Column(
            [
                logo_header,
                build_horizontal_divider(),
                ft.Column(
                    nav_group_sections,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    spacing=2,
                ),
                build_horizontal_divider(),
                profile_footer,
            ],
            spacing=0,
            expand=True,
        ),
    )


def _build_sidebar_logo_header() -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.INVENTORY, color=ThemeColor.TEXT_PRIMARY, size=20
                    ),
                    width=44,
                    height=44,
                    border_radius=12,
                    alignment=ft.Alignment.CENTER,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_LEFT,
                        end=ft.Alignment.BOTTOM_RIGHT,
                        colors=[ThemeColor.ACCENT_VIOLET, ThemeColor.ACCENT_TEAL],
                    ),
                ),
                ft.Column(
                    [
                        ft.Text(
                            "Inventory Manager",
                            color=ThemeColor.TEXT_PRIMARY,
                            size=17,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text("Smart Platform", color=ThemeColor.TEXT_MUTED, size=11),
                    ],
                    spacing=1,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=18, vertical=20),
    )


def _build_all_nav_group_sections(
    active_route_key: str,
    on_click_callback,
) -> list[ft.Control]:
    nav_item_lookup: dict[str, tuple] = {
        route_key: (route_key, icon, label)
        for route_key, icon, label in NAVIGATION_ITEM_DEFINITIONS
    }
    all_sections: list[ft.Control] = []

    for group_label, route_keys_in_group in NAVIGATION_GROUP_STRUCTURE:
        all_sections.append(build_nav_section_label(group_label))
        for route_key in route_keys_in_group:
            if route_key in nav_item_lookup:
                nav_item_tuple = nav_item_lookup[route_key]
                all_sections.append(
                    _build_nav_item_button(
                        route_key=nav_item_tuple[0],
                        item_icon=nav_item_tuple[1],
                        item_label=nav_item_tuple[2],
                        is_currently_active=(route_key == active_route_key),
                        on_click_callback=on_click_callback,
                    )
                )
    return all_sections


def _build_nav_item_button(
    route_key: str,
    item_icon: str,
    item_label: str,
    is_currently_active: bool,
    on_click_callback,
) -> ft.Container:
    def _handle_click(_event):
        on_click_callback(route_key)

    active_indicator_stripe = ft.Container(
        width=4,
        border_radius=ft.border_radius.only(top_right=3, bottom_right=3),
        bgcolor=ThemeColor.ACCENT_VIOLET if is_currently_active else "transparent",
    )
    inner_row = ft.Row(
        [
            ft.Container(width=8),
            ft.Container(
                content=ft.Icon(
                    item_icon,
                    color=(
                        ThemeColor.ACCENT_VIOLET
                        if is_currently_active
                        else ThemeColor.TEXT_MUTED
                    ),
                    size=20,
                ),
                bgcolor=(
                    ft.Colors.with_opacity(0.14, ThemeColor.ACCENT_VIOLET)
                    if is_currently_active
                    else "transparent"
                ),
                border_radius=10,
                padding=10,
            ),
            ft.Text(
                item_label,
                size=14,
                color=(
                    ThemeColor.TEXT_PRIMARY
                    if is_currently_active
                    else ThemeColor.TEXT_SECONDARY
                ),
                weight=(
                    ft.FontWeight.W_600 if is_currently_active else ft.FontWeight.NORMAL
                ),
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    nav_item_container = ft.Container(
        content=ft.Row(
            [active_indicator_stripe, ft.Container(inner_row, expand=True)], spacing=0
        ),
        height=NAV_ITEM_HEIGHT_PX,
        border_radius=ft.border_radius.only(top_right=12, bottom_right=12),
        bgcolor=(
            ft.Colors.with_opacity(0.1, ThemeColor.ACCENT_VIOLET)
            if is_currently_active
            else "transparent"
        ),
        margin=ft.margin.only(right=12),
        on_click=_handle_click,
    )

    if not is_currently_active:

        def _handle_hover(hover_event: ft.HoverEvent):
            nav_item_container.bgcolor = (
                ft.Colors.with_opacity(0.05, ThemeColor.TEXT_PRIMARY)
                if hover_event.data == "true"
                else "transparent"
            )
            nav_item_container.update()

        nav_item_container.on_hover = _handle_hover

    return nav_item_container


def _build_sidebar_profile_footer(
    user_session_data: dict | None,
    on_logout_click_callback,
) -> ft.Container:
    user_display_name = "User"
    user_email_address = "user@email.com"

    if user_session_data:
        user_display_name = user_session_data.get("name", "User")
        user_email_address = user_session_data.get("email", "")

    avatar_letter = user_display_name[0].upper() if user_display_name else "U"

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        avatar_letter,
                        color=ThemeColor.TEXT_PRIMARY,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=40,
                    height=40,
                    border_radius=10,
                    alignment=ft.Alignment.CENTER,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_LEFT,
                        end=ft.Alignment.BOTTOM_RIGHT,
                        colors=[ThemeColor.ACCENT_VIOLET, "#5B4FCC"],
                    ),
                ),
                ft.Column(
                    [
                        ft.Text(
                            user_display_name,
                            color=ThemeColor.TEXT_PRIMARY,
                            size=13,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            user_email_address, color=ThemeColor.TEXT_MUTED, size=11
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.IconButton(
                    ft.Icons.LOGOUT,
                    icon_color=ThemeColor.TEXT_MUTED,
                    icon_size=18,
                    tooltip="Logout",
                    on_click=on_logout_click_callback,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.all(14),
    )


def build_application_topbar(currently_active_route_key: str) -> ft.Container:
    active_page_display_label = next(
        (
            label
            for key, _icon, label in NAVIGATION_ITEM_DEFINITIONS
            if key == currently_active_route_key
        ),
        "Dashboard",
    )
    urgent_alert_count = sum(
        1 for alert in _FALLBACK_ALERTS if alert["type"] in ("danger", "warning")
    )

    breadcrumb_row = ft.Row(
        [
            ft.Text("Inventory Manager", size=13, color=ThemeColor.TEXT_MUTED),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=15, color=ThemeColor.TEXT_MUTED),
            ft.Text(
                active_page_display_label,
                size=14,
                color=ThemeColor.TEXT_PRIMARY,
                weight=ft.FontWeight.W_600,
            ),
        ],
        spacing=5,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    global_search_field = ft.TextField(
        hint_text="Search…",
        prefix_icon=ft.Icons.SEARCH,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_color=ThemeColor.BORDER_SUBTLE,
        color=ThemeColor.TEXT_PRIMARY,
        hint_style=ft.TextStyle(color=ThemeColor.TEXT_MUTED),
        height=44,
        width=230,
        border_radius=12,
        focused_border_color=ThemeColor.ACCENT_VIOLET,
        text_size=14,
        content_padding=ft.padding.symmetric(horizontal=4, vertical=0),
    )

    notification_bell_with_badge = ft.Stack(
        [
            ft.Container(
                content=ft.Icon(
                    ft.Icons.NOTIFICATIONS, color=ThemeColor.TEXT_SECONDARY, size=22
                ),
                bgcolor=ThemeColor.CARD_BACKGROUND,
                border_radius=12,
                padding=10,
                border=ft.border.all(1, ThemeColor.BORDER_SUBTLE),
            ),
            ft.Container(
                content=ft.Text(
                    str(urgent_alert_count),
                    color=ThemeColor.TEXT_PRIMARY,
                    size=10,
                    weight=ft.FontWeight.BOLD,
                ),
                bgcolor=ThemeColor.ACCENT_ROSE,
                border_radius=8,
                width=18,
                height=18,
                alignment=ft.Alignment.CENTER,
                right=0,
                top=0,
            ),
        ]
    )

    date_display_container = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=13, color=ThemeColor.TEXT_MUTED),
                ft.Text(
                    datetime.now().strftime("%b %d, %Y"),
                    size=13,
                    color=ThemeColor.TEXT_SECONDARY,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.border.all(1, ThemeColor.BORDER_SUBTLE),
    )

    return ft.Container(
        content=ft.Row(
            [
                breadcrumb_row,
                ft.Container(expand=True),
                global_search_field,
                notification_bell_with_badge,
                date_display_container,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ThemeColor.SURFACE_PRIMARY,
        border=ft.border.only(bottom=ft.BorderSide(1, ThemeColor.BORDER_DEFAULT)),
        padding=ft.padding.symmetric(horizontal=28, vertical=12),
    )
