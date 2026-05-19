import asyncio
import csv
from typing import Callable

import flet as ft

from src.app.components.theme import ThemeColor
from src.app.components.primitive_components import show_toast


def open_form_dialog(
    flet_page: ft.Page,
    *,
    title: str,
    fields: list[ft.Control],
    submit_label: str = "Save",
    submit_color: str = ThemeColor.ACCENT_VIOLET,
    on_submit: Callable[[ft.ControlEvent], None],
    width: int = 580,
    height: int = 440,
    field_spacing: int = 12,
) -> ft.AlertDialog:
    dialog: ft.AlertDialog | None = None

    def _handle_submit(e):
        on_submit(e)

    dialog = ft.AlertDialog(
        modal=True,
        open=False,
        title=ft.Text(
            title,
            color=ThemeColor.TEXT_PRIMARY,
            weight=ft.FontWeight.W_600,
            size=18,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        content=ft.Container(
            width=width,
            content=ft.Column(
                fields,
                spacing=field_spacing,
                scroll=ft.ScrollMode.AUTO,
                height=height,
            ),
        ),
        actions=[
            ft.TextButton(
                "Cancel",
                on_click=lambda e: (
                    setattr(dialog, "open", False),
                    flet_page.update(),
                ),
                style=ft.ButtonStyle(color=ThemeColor.TEXT_MUTED),
            ),
            ft.FilledButton(
                submit_label,
                on_click=_handle_submit,
                style=ft.ButtonStyle(
                    bgcolor=submit_color,
                    color=ThemeColor.TEXT_PRIMARY,
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    if dialog not in flet_page.overlay:
        flet_page.overlay.append(dialog)
    dialog.open = True
    flet_page.update()
    return dialog


def close_dialog(flet_page: ft.Page, dialog: ft.AlertDialog) -> None:
    dialog.open = False
    flet_page.update()


def open_confirm_dialog(
    flet_page: ft.Page,
    *,
    title: str = "Confirm Delete",
    body_lines: list[str],
    confirm_label: str = "Delete",
    confirm_color: str = ThemeColor.ACCENT_ROSE,
    on_confirm: Callable[[ft.ControlEvent], None],
) -> ft.AlertDialog:
    dialog: ft.AlertDialog | None = None

    def _do_confirm(e):
        on_confirm(e)

    text_sizes = [14, 15, 12]
    text_colors = [
        ThemeColor.TEXT_SECONDARY,
        ThemeColor.TEXT_PRIMARY,
        ThemeColor.TEXT_MUTED,
    ]
    text_weights = [
        ft.FontWeight.NORMAL,
        ft.FontWeight.W_600,
        ft.FontWeight.NORMAL,
    ]

    body_controls = [
        ft.Text(
            line,
            color=text_colors[min(i, len(text_colors) - 1)],
            size=text_sizes[min(i, len(text_sizes) - 1)],
            weight=text_weights[min(i, len(text_weights) - 1)],
        )
        for i, line in enumerate(body_lines)
    ]

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        title=ft.Text(title, color=ThemeColor.TEXT_PRIMARY, weight=ft.FontWeight.W_600),
        content=ft.Column(body_controls, spacing=6, tight=True),
        actions=[
            ft.TextButton(
                "Cancel",
                on_click=lambda e: (
                    setattr(dialog, "open", False),
                    flet_page.update(),
                ),
                style=ft.ButtonStyle(color=ThemeColor.TEXT_MUTED),
            ),
            ft.FilledButton(
                confirm_label,
                on_click=_do_confirm,
                style=ft.ButtonStyle(
                    bgcolor=confirm_color,
                    color=ThemeColor.TEXT_PRIMARY,
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    flet_page.overlay.append(dialog)
    dialog.open = True
    flet_page.update()
    return dialog


def open_csv_import_dialog(
    flet_page: ft.Page,
    *,
    on_file_selected: Callable[[str], None] | None = None,
    hint_text: str = "Header row required. Existing IDs are skipped.",
    allowed_extensions: list[str] | None = None,
) -> ft.AlertDialog:
    allowed_extensions = allowed_extensions or ["csv"]

    progress_bar = ft.ProgressBar(
        value=0,
        bgcolor=ft.Colors.with_opacity(0.15, ThemeColor.ACCENT_VIOLET),
        color=ThemeColor.ACCENT_VIOLET,
        border_radius=8,
        height=10,
    )
    status_text = ft.Text("", size=12, color=ThemeColor.TEXT_MUTED)
    pct_text = ft.Text(
        "0%", size=12, color=ThemeColor.ACCENT_VIOLET, weight=ft.FontWeight.W_600
    )

    dialog: ft.AlertDialog | None = None

    dialog = ft.AlertDialog(
        modal=True,
        open=False,
        bgcolor=ThemeColor.CARD_BACKGROUND,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.UPLOAD_FILE, color=ThemeColor.ACCENT_VIOLET, size=20),
                ft.Text(
                    "Import from CSV",
                    color=ThemeColor.TEXT_PRIMARY,
                    weight=ft.FontWeight.W_700,
                    size=18,
                ),
            ],
            spacing=10,
        ),
        content=ft.Container(
            width=460,
            content=ft.Column(
                [
                    ft.Text(hint_text, size=13, color=ThemeColor.TEXT_SECONDARY),
                    ft.Container(height=8),
                    ft.Row([status_text, ft.Container(expand=True), pct_text]),
                    progress_bar,
                ],
                spacing=4,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton(
                "Close",
                on_click=lambda e: (
                    setattr(dialog, "open", False),
                    flet_page.update(),
                ),
                style=ft.ButtonStyle(color=ThemeColor.TEXT_MUTED),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    if dialog not in flet_page.overlay:
        flet_page.overlay.append(dialog)

    dialog._csv_progress_bar = progress_bar  # type: ignore[attr-defined]
    dialog._csv_status_text = status_text  # type: ignore[attr-defined]
    dialog._csv_pct_text = pct_text  # type: ignore[attr-defined]

    async def _pick_and_run():
        files = await ft.FilePicker().pick_files(
            dialog_title="Select a CSV file to import",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=allowed_extensions,
            allow_multiple=False,
        )
        if not files:
            return
        file_path = files[0].path
        if not file_path:
            show_toast(
                flet_page, "Cannot read file path on this platform.", is_error=True
            )
            return
        progress_bar.value = 0.0
        pct_text.value = "0%"
        status_text.value = "Starting import…"
        status_text.color = ThemeColor.TEXT_MUTED
        dialog.open = True
        flet_page.update()
        if on_file_selected:
            on_file_selected(file_path)

    flet_page.run_task(_pick_and_run)
    return dialog


class CsvImportController:
    def __init__(
        self,
        flet_page: ft.Page,
        *,
        collection,
        id_field: str = "_id",
        on_done: Callable | None = None,
        extra_transform: Callable[[dict], dict] | None = None,
    ):
        self._page = flet_page
        self._col = collection
        self._id_field = id_field
        self._on_done = on_done
        self._transform = extra_transform
        self._dialog: ft.AlertDialog | None = None

    def open(self, **dialog_kwargs) -> None:
        self._dialog = open_csv_import_dialog(
            self._page,
            on_file_selected=self._run_import,
            **dialog_kwargs,
        )

    def _update(
        self, status: str, pct: float, status_color: str = ThemeColor.TEXT_MUTED
    ):
        if not self._dialog:
            return
        self._dialog._csv_status_text.value = status  # type: ignore[attr-defined]
        self._dialog._csv_status_text.color = status_color  # type: ignore[attr-defined]
        self._dialog._csv_progress_bar.value = pct  # type: ignore[attr-defined]
        self._dialog._csv_pct_text.value = f"{int(pct * 100)}%"  # type: ignore[attr-defined]
        self._page.update()

    def _run_import(self, file_path: str) -> None:
        self._page.run_task(self._async_import, file_path)

    async def _async_import(self, file_path: str) -> None:
        try:
            with open(file_path, newline="", encoding="utf-8-sig") as f:
                raw_rows = list(csv.DictReader(f))
        except Exception as exc:
            self._update(f"Error reading file: {exc}", 1.0, ThemeColor.ACCENT_ROSE)
            return

        rows = [{k.strip().lower(): v for k, v in r.items()} for r in raw_rows]
        total = len(rows)
        if total == 0:
            self._update(
                "CSV is empty — nothing to import.", 1.0, ThemeColor.ACCENT_ROSE
            )
            return

        self._update(f"Checking {total} rows…", 0.0)
        await asyncio.sleep(0)

        existing_ids = {
            str(doc[self._id_field]) for doc in self._col.find({}, {self._id_field: 1})
        }
        skipped, to_insert = 0, []

        for row in rows:
            _id = str(row.get(self._id_field, "") or "").strip()
            if not _id or _id in existing_ids:
                skipped += 1
                continue
            doc = {k: v for k, v in row.items()}
            if self._transform:
                doc = self._transform(doc)
            to_insert.append(doc)
            existing_ids.add(_id)

        if not to_insert:
            self._update(
                f"Nothing to insert, {skipped} skipped.", 1.0, ThemeColor.ACCENT_AMBER
            )
            return

        inserted = 0
        batch_size = max(1, len(to_insert) // 20)
        for start in range(0, len(to_insert), batch_size):
            batch = to_insert[start : start + batch_size]
            self._col.insert_many(batch, ordered=False)
            inserted += len(batch)
            progress = min((inserted + skipped) / total, 1.0)
            self._update(f"Inserting… {inserted} / {len(to_insert)}", progress)
            await asyncio.sleep(0.03)

        color = ThemeColor.ACCENT_AMBER if skipped else ThemeColor.ACCENT_GREEN
        msg = (
            f"Done — {inserted} inserted, {skipped} skipped."
            if skipped
            else f"Done — {inserted} records imported successfully."
        )
        self._update(msg, 1.0, color)
        if self._on_done:
            self._on_done()
