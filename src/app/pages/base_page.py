from __future__ import annotations

import flet as ft
from abc import ABC, abstractmethod

from src.app.components.primitive_components import (
    build_vertical_spacer,
    build_scrollable_page_column,
)


class BasePage(ABC):
    def __init__(self, flet_page: ft.Page) -> None:
        self.flet_page = flet_page

    @abstractmethod
    def build_page_content(self) -> list[ft.Control]: ...

    def build(self) -> ft.Control:

        page_body_controls = self.build_page_content()

        return build_scrollable_page_column(
            build_vertical_spacer(6),
            *page_body_controls,
            build_vertical_spacer(28),
        )
