from __future__ import annotations

import flet as ft

from src.app.pages.dashboard_page import build_dashboard_page
from src.app.pages.products_page import build_products_page
from src.app.pages.products_return_page import build_products_return_page
from src.app.pages.categories_page import build_categories_page
from src.app.pages.suppliers_page import build_suppliers_page
from src.app.pages.employees_page import build_employees_page
from src.app.pages.sales_page import build_sales_page
from src.app.pages.forecast_page import build_forecast_page
from src.app.pages.risk_page import build_risk_page
from src.app.pages.purchase_orders_page import build_purchase_orders_page
from src.app.pages.admin_page import build_admin_page
from src.app.pages.data_cleaning_page import build_data_cleaning_visualization_page
from src.app.pages.reorder_page import build_reorder_page
from src.app.components.theme import ThemeColor
from src.utilities.perf import PerfTimer

PAGE_BUILDER_REGISTRY: dict = {
    "dashboard": build_dashboard_page,
    "products": build_products_page,
    "products_return": build_products_return_page,
    "categories": build_categories_page,
    "sales": build_sales_page,
    "suppliers": build_suppliers_page,
    "employees": build_employees_page,
    "forecast": build_forecast_page,
    "reorder": build_reorder_page,
    "risk": build_risk_page,
    "data_cleaning": build_data_cleaning_visualization_page,
    "purchase_orders": build_purchase_orders_page,
    "admin": build_admin_page,
}

ROLE_ALLOWED_ROUTES: dict[str, list[str]] = {
    "Admin": list(PAGE_BUILDER_REGISTRY.keys()),
    "Lead": list(PAGE_BUILDER_REGISTRY.keys()),
    "Manager": [
        "dashboard",
        "products",
        "categories",
        "suppliers",
        "forecast",
        "analytics",
        "purchase_orders",
    ],
    "Employee": ["dashboard", "products", "sales"],
}


def _build_loading_spinner() -> ft.Container:
    return ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            [
                ft.ProgressRing(
                    width=40,
                    height=40,
                    stroke_width=3,
                    color=ThemeColor.ACCENT_VIOLET,
                ),
                ft.Container(height=16),
                ft.Text(
                    "Loading…",
                    size=13,
                    color=ThemeColor.TEXT_MUTED,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0,
        ),
    )


class ApplicationRouter:
    def __init__(self, flet_page: ft.Page) -> None:
        self._flet_page = flet_page
        self._active_route_key: str = "dashboard"
        self._authenticated_user_session: dict | None = None
        self._in_memory_session_cache: dict = {}
        self._nav_generation: int = 0

    def initialize(self) -> None:
        self._flet_page.title = "Inventory Manager"
        self._flet_page.bgcolor = ThemeColor.BACKGROUND_DEEPEST
        self._flet_page.padding = 0
        self._flet_page.window.width = 1400
        self._flet_page.window.height = 920
        self._flet_page.window.min_width = 1000
        self._flet_page.window.min_height = 660
        self._flet_page.window.update()
        self._flet_page.fonts = {
            "Inter": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2"
        }
        self._flet_page.theme = ft.Theme(font_family="Inter")
        self._flet_page.theme_mode = ft.ThemeMode.DARK

        cached_user = self._retrieve_session_value("user")
        if cached_user:
            self._authenticated_user_session = cached_user
            self._rebuild_app_shell(self._active_route_key)
        else:
            self._show_auth_screen("login")

    def navigate_to_route(self, destination_route_key: str) -> None:
        if self._authenticated_user_session is None:
            self._show_auth_screen("login")
            return
        role = self._authenticated_user_session.get("role", "Employee")
        allowed = ROLE_ALLOWED_ROUTES.get(role, ["dashboard"])
        if destination_route_key not in allowed:
            destination_route_key = "dashboard"
        self._active_route_key = destination_route_key
        self._rebuild_app_shell(destination_route_key)

    def _handle_login_success(self, user_session_data: dict) -> None:
        self._authenticated_user_session = user_session_data
        self._store_session_value("user", user_session_data)
        self._rebuild_app_shell("dashboard")

    def _handle_logout(self) -> None:
        self._authenticated_user_session = None
        self._remove_session_value("user")
        self._show_auth_screen("login")

    def _rebuild_app_shell(self, active_route_key: str) -> None:
        from src.app.shell_layout import (
            build_application_sidebar,
            build_application_topbar,
        )

        self._nav_generation += 1
        my_generation = self._nav_generation

        _rt = PerfTimer(f"router:{active_route_key}")

        page_builder = PAGE_BUILDER_REGISTRY.get(active_route_key, build_dashboard_page)

        sidebar = build_application_sidebar(
            currently_active_route_key=active_route_key,
            on_nav_item_click_callback=self.navigate_to_route,
            on_logout_click_callback=lambda _e: self._handle_logout(),
            authenticated_user_session_data=self._authenticated_user_session,
        )
        topbar = build_application_topbar(currently_active_route_key=active_route_key)

        content_slot = ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=30, vertical=20),
            bgcolor=ThemeColor.BACKGROUND_DEEPEST,
            content=_build_loading_spinner(),
        )

        self._flet_page.controls.clear()
        self._flet_page.add(
            ft.Row(
                [
                    sidebar,
                    ft.Column(
                        [
                            topbar,
                            content_slot,
                        ],
                        spacing=0,
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            )
        )
        self._flet_page.update()
        _rt.checkpoint("shell + spinner visible to user")

        async def _load_in_background():
            if my_generation != self._nav_generation:
                return
            try:
                page_content = page_builder(self._flet_page)
                _rt.checkpoint("page_builder() returned")
            except Exception as _exc:
                import traceback as _tb

                _tb.print_exc()
                if my_generation != self._nav_generation:
                    return
                page_content = ft.Column(
                    [
                        ft.Text(
                            "Failed to load page.",
                            color=ThemeColor.ACCENT_ROSE,
                            size=14,
                        ),
                        ft.Text(
                            str(_exc),
                            color=ThemeColor.TEXT_MUTED,
                            size=12,
                            selectable=True,
                        ),
                    ]
                )
            if my_generation != self._nav_generation:
                return
            content_slot.content = page_content
            try:
                self._flet_page.update()
                _rt.checkpoint("page.update() — content swapped in")
                _rt.done()
            except Exception:
                pass

        self._flet_page.run_task(_load_in_background)

    def _show_auth_screen(self, auth_sub_page_key: str) -> None:
        from src.app.auth_screen import build_auth_screen

        build_auth_screen(
            flet_page=self._flet_page,
            auth_sub_page_key=auth_sub_page_key,
            on_login_success_callback=self._handle_login_success,
        )

    def _store_session_value(self, key: str, value) -> None:
        self._in_memory_session_cache[key] = value
        try:
            self._flet_page.session.set(key, value)
        except Exception:
            pass

    def _retrieve_session_value(self, key: str):
        try:
            v = self._flet_page.session.get(key)
            if v:
                return v
        except Exception:
            pass
        return self._in_memory_session_cache.get(key)

    def _remove_session_value(self, key: str) -> None:
        self._in_memory_session_cache.pop(key, None)
        try:
            self._flet_page.session.remove(key)
        except Exception:
            pass
