from __future__ import annotations

import flet as ft

from src.app.components.primitive_components import (
    build_auth_text_field,
    build_vertical_spacer,
)
from src.app.components.theme import ThemeColor
from src.app.services.authentication_service import (
    authenticate_user_with_credentials,
    register_new_user_account,
)


def build_auth_screen(
    flet_page: ft.Page,
    auth_sub_page_key: str,
    on_login_success_callback,
) -> None:
    flet_page.controls.clear()
    flet_page.bgcolor = ThemeColor.BACKGROUND_DEEPEST

    if auth_sub_page_key == "register":
        auth_card_widget = _build_registration_card(
            flet_page, on_login_success_callback
        )
    else:
        auth_card_widget = _build_login_card(flet_page, on_login_success_callback)

    flet_page.add(
        ft.Container(
            content=ft.Row(
                [
                    _build_auth_left_panel(),
                    ft.Container(
                        content=ft.Column(
                            [auth_card_widget],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            expand=True,
                        ),
                        expand=True,
                        bgcolor=ThemeColor.BACKGROUND_DEEPEST,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
        )
    )
    flet_page.update()


def _build_auth_left_panel() -> ft.Container:
    feature_bullet_items = [
        (ft.Icons.AUTO_AWESOME, "ML Demand Forecasting", "LSTM · XGBoost · Prophet"),
        (ft.Icons.RECEIPT_LONG, "Smart Billing", "One click invoice generation"),
        (
            ft.Icons.BAR_CHART,
            "Real-time Analytics",
            "Live dashboard, analytics and trend charts",
        ),
        (ft.Icons.SHIELD, "Role based Access", "Admin · Manager · Employee"),
    ]
    feature_rows = [
        ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(
                            feature_icon, color=ThemeColor.TEXT_PRIMARY, size=18
                        ),
                        bgcolor=ft.Colors.with_opacity(0.18, ThemeColor.TEXT_PRIMARY),
                        border_radius=10,
                        padding=10,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                feature_title,
                                size=14,
                                color=ThemeColor.TEXT_PRIMARY,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                feature_subtitle,
                                size=12,
                                color=ft.Colors.with_opacity(
                                    0.65, ThemeColor.TEXT_PRIMARY
                                ),
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.with_opacity(0.06, ThemeColor.TEXT_PRIMARY),
            border=ft.border.all(
                1, ft.Colors.with_opacity(0.12, ThemeColor.TEXT_PRIMARY)
            ),
            border_radius=14,
            padding=ft.padding.all(14),
        )
        for feature_icon, feature_title, feature_subtitle in feature_bullet_items
    ]

    return ft.Container(
        width=480,
        expand=False,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#1A0E3F", "#0D1A3A"],
        ),
        border=ft.border.only(right=ft.BorderSide(1, ThemeColor.BORDER_DEFAULT)),
        content=ft.Column(
            [
                build_vertical_spacer(60),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.INVENTORY,
                                    color=ThemeColor.TEXT_PRIMARY,
                                    size=26,
                                ),
                                width=52,
                                height=52,
                                border_radius=14,
                                alignment=ft.Alignment.CENTER,
                                gradient=ft.LinearGradient(
                                    begin=ft.Alignment.TOP_LEFT,
                                    end=ft.Alignment.BOTTOM_RIGHT,
                                    colors=[
                                        ThemeColor.ACCENT_VIOLET,
                                        ThemeColor.ACCENT_TEAL,
                                    ],
                                ),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Inventory Manager",
                                        color=ThemeColor.TEXT_PRIMARY,
                                        size=22,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "Smart Inventory Platform",
                                        color=ft.Colors.with_opacity(
                                            0.65, ThemeColor.TEXT_PRIMARY
                                        ),
                                        size=13,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=40),
                ),
                build_vertical_spacer(40),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "ML Powered Inventory\nManagement",
                                size=30,
                                weight=ft.FontWeight.BOLD,
                                color=ThemeColor.TEXT_PRIMARY,
                                text_align=ft.TextAlign.LEFT,
                            ),
                            build_vertical_spacer(8),
                            ft.Text(
                                "Experience real-time analytics, demand forecasting, and \nautonomous reordering all in one platform.",
                                size=14,
                                color=ft.Colors.with_opacity(
                                    0.65, ThemeColor.TEXT_PRIMARY
                                ),
                            ),
                        ],
                        spacing=0,
                    ),
                    padding=ft.padding.symmetric(horizontal=40),
                ),
                build_vertical_spacer(40),
                ft.Container(
                    content=ft.Column(feature_rows, spacing=10),
                    padding=ft.padding.symmetric(horizontal=40),
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text(
                        "",
                        size=11,
                        color=ft.Colors.with_opacity(0.35, ThemeColor.TEXT_PRIMARY),
                    ),
                    padding=ft.padding.all(40),
                ),
            ],
            spacing=0,
            expand=True,
        ),
    )


def _build_auth_card_shell(form_column: ft.Column) -> ft.Container:
    return ft.Container(
        width=430,
        content=form_column,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=24,
        padding=40,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=40,
            color=ft.Colors.with_opacity(0.3, "#000000"),
            offset=ft.Offset(0, 16),
        ),
    )


def _build_login_card(flet_page: ft.Page, on_login_success_callback) -> ft.Container:
    email_text_field = build_auth_text_field(
        "Email address", "you@company.com", ft.Icons.EMAIL
    )
    password_text_field = build_auth_text_field(
        "Password", "Enter your password", ft.Icons.LOCK, is_password_field=True
    )
    error_banner_text = ft.Text("", size=13, color=ThemeColor.ACCENT_ROSE)

    loading_progress_ring = ft.ProgressRing(
        width=20,
        height=20,
        stroke_width=2,
        color=ThemeColor.TEXT_PRIMARY,
        visible=False,
    )
    submit_button_ref = ft.Ref[ft.FilledButton]()

    def _handle_login_button_click(_event) -> None:
        error_banner_text.value = ""
        loading_progress_ring.visible = True
        if submit_button_ref.current:
            submit_button_ref.current.disabled = True
        flet_page.update()

        entered_email = email_text_field.value or ""
        entered_password = password_text_field.value or ""

        if not entered_email.strip() or not entered_password.strip():
            error_banner_text.value = "Please enter both email and password."
            loading_progress_ring.visible = False
            if submit_button_ref.current:
                submit_button_ref.current.disabled = False
            flet_page.update()
            return

        authenticated_user, error_message = authenticate_user_with_credentials(
            entered_email, entered_password
        )

        loading_progress_ring.visible = False
        if submit_button_ref.current:
            submit_button_ref.current.disabled = False

        if error_message:
            error_banner_text.value = error_message
            flet_page.update()
        else:
            on_login_success_callback(authenticated_user)

    def _handle_switch_to_register(_event) -> None:
        build_auth_screen(flet_page, "register", on_login_success_callback)

    login_submit_button = ft.FilledButton(
        ref=submit_button_ref,
        content=ft.Row(
            [
                loading_progress_ring,
                ft.Text("Sign In", size=15, weight=ft.FontWeight.W_600),
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=_handle_login_button_click,
        expand=True,
        height=52,
        style=ft.ButtonStyle(
            bgcolor=ThemeColor.ACCENT_VIOLET,
            color=ThemeColor.TEXT_PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )

    return _build_auth_card_shell(
        ft.Column(
            [
                ft.Text(
                    "Welcome back",
                    size=30,
                    weight=ft.FontWeight.BOLD,
                    color=ThemeColor.TEXT_PRIMARY,
                ),
                ft.Text(
                    "Sign in to your Inventory Manager account",
                    size=14,
                    color=ThemeColor.TEXT_MUTED,
                ),
                build_vertical_spacer(32),
                email_text_field,
                build_vertical_spacer(14),
                password_text_field,
                build_vertical_spacer(8),
                ft.Row(
                    [
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Forgot password?",
                            style=ft.ButtonStyle(color=ThemeColor.ACCENT_VIOLET),
                        ),
                    ]
                ),
                build_vertical_spacer(6),
                error_banner_text,
                build_vertical_spacer(4),
                login_submit_button,
                build_vertical_spacer(20),
                ft.Row(
                    [
                        ft.Text(
                            "Don't have an account?",
                            size=13,
                            color=ThemeColor.TEXT_MUTED,
                        ),
                        ft.TextButton(
                            "Create one",
                            on_click=_handle_switch_to_register,
                            style=ft.ButtonStyle(color=ThemeColor.ACCENT_VIOLET),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
                build_vertical_spacer(24),
                _build_demo_credentials_hint(),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )


def _build_registration_card(
    flet_page: ft.Page, on_login_success_callback
) -> ft.Container:
    full_name_text_field = build_auth_text_field(
        "Full name", "Jane Smith", ft.Icons.PERSON
    )
    email_text_field = build_auth_text_field(
        "Work email", "jane@company.com", ft.Icons.EMAIL
    )
    password_text_field = build_auth_text_field(
        "Password", "Min. 8 characters", ft.Icons.LOCK, is_password_field=True
    )
    confirm_password_field = build_auth_text_field(
        "Confirm password",
        "Re-enter password",
        ft.Icons.LOCK_OUTLINE,
        is_password_field=True,
    )
    error_banner_text = ft.Text("", size=13, color=ThemeColor.ACCENT_ROSE)
    success_banner_text = ft.Text("", size=13, color=ThemeColor.ACCENT_TEAL)

    def _handle_register_button_click(_event) -> None:
        error_banner_text.value = ""
        success_banner_text.value = ""

        entered_name = full_name_text_field.value or ""
        entered_email = email_text_field.value or ""
        entered_password = password_text_field.value or ""
        confirm_password = confirm_password_field.value or ""

        if not all(
            [entered_name.strip(), entered_email.strip(), entered_password.strip()]
        ):
            error_banner_text.value = "Please fill in all required fields."
            flet_page.update()
            return

        if entered_password != confirm_password:
            error_banner_text.value = "Passwords do not match."
            flet_page.update()
            return

        registration_succeeded, error_message = register_new_user_account(
            entered_name, entered_email, entered_password
        )

        if not registration_succeeded:
            error_banner_text.value = error_message or "Registration failed."
        else:
            success_banner_text.value = "Account created! Signing you in…"
            flet_page.update()
            authenticated_user, login_error = authenticate_user_with_credentials(
                entered_email, entered_password
            )
            if authenticated_user:
                on_login_success_callback(authenticated_user)
                return

        flet_page.update()

    def _handle_switch_to_login(_event) -> None:
        build_auth_screen(flet_page, "login", on_login_success_callback)

    return _build_auth_card_shell(
        ft.Column(
            [
                ft.Text(
                    "Create account",
                    size=30,
                    weight=ft.FontWeight.BOLD,
                    color=ThemeColor.TEXT_PRIMARY,
                ),
                ft.Text(
                    "Join Inventory Manager, it's free to start",
                    size=14,
                    color=ThemeColor.TEXT_MUTED,
                ),
                build_vertical_spacer(32),
                full_name_text_field,
                build_vertical_spacer(14),
                email_text_field,
                build_vertical_spacer(14),
                password_text_field,
                build_vertical_spacer(14),
                confirm_password_field,
                build_vertical_spacer(8),
                error_banner_text,
                success_banner_text,
                build_vertical_spacer(8),
                ft.FilledButton(
                    "Create Account",
                    on_click=_handle_register_button_click,
                    expand=True,
                    height=52,
                    icon=ft.Icons.PERSON_ADD,
                    style=ft.ButtonStyle(
                        bgcolor=ThemeColor.ACCENT_VIOLET,
                        color=ThemeColor.TEXT_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=14),
                    ),
                ),
                build_vertical_spacer(20),
                ft.Row(
                    [
                        ft.Text(
                            "Already have an account?",
                            size=13,
                            color=ThemeColor.TEXT_MUTED,
                        ),
                        ft.TextButton(
                            "Sign in",
                            on_click=_handle_switch_to_login,
                            style=ft.ButtonStyle(color=ThemeColor.ACCENT_VIOLET),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )


def _build_demo_credentials_hint() -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.INFO_OUTLINE,
                            size=14,
                            color=ft.Colors.with_opacity(0.7, ThemeColor.ACCENT_VIOLET),
                        ),
                        ft.Text(
                            "Demo credentials",
                            size=12,
                            color=ft.Colors.with_opacity(0.8, ThemeColor.ACCENT_VIOLET),
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=6,
                ),
                build_vertical_spacer(6),
                ft.Text(
                    "Email: admin@company.com", size=12, color=ThemeColor.TEXT_MUTED
                ),
                ft.Text("Password: admin123", size=12, color=ThemeColor.TEXT_MUTED),
            ],
            spacing=3,
        ),
        bgcolor=ft.Colors.with_opacity(0.07, ThemeColor.ACCENT_VIOLET),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ThemeColor.ACCENT_VIOLET)),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )
