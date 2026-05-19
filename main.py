import flet as ft
from src.app.routes import ApplicationRouter


def main(flet_page: ft.Page) -> None:
    router = ApplicationRouter(flet_page)
    router.initialize()