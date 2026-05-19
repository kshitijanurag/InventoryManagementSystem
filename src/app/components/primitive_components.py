import flet as ft
from src.app.components.theme import (
    AVATAR_COLOR_CYCLE,
    ThemeColor,
    FONT_SIZE_BODY,
    FONT_SIZE_BODY_LARGE,
    FONT_SIZE_STAT_VALUE,
    FONT_SIZE_TITLE,
    CARD_DEFAULT_PADDING,
    CARD_DEFAULT_BORDER_RADIUS,
)


def build_vertical_spacer(height_px: int = 16) -> ft.Container:
    return ft.Container(height=height_px)


def build_horizontal_divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=ThemeColor.BORDER_DEFAULT)


def build_glow_status_dot(indicator_color: str, dot_size_px: int = 10) -> ft.Container:
    return ft.Container(
        width=dot_size_px,
        height=dot_size_px,
        border_radius=dot_size_px // 2,
        bgcolor=indicator_color,
    )


def build_avatar_circle(
    display_letter: str,
    color_cycle_index: int = 0,
    avatar_size_px: int = 40,
) -> ft.Container:
    resolved_background_color = AVATAR_COLOR_CYCLE[
        color_cycle_index % len(AVATAR_COLOR_CYCLE)
    ]
    font_size = max(10, int(avatar_size_px / 2.8))
    return ft.Container(
        content=ft.Text(
            display_letter.upper(),
            color=ThemeColor.TEXT_PRIMARY,
            size=font_size,
            weight=ft.FontWeight.BOLD,
        ),
        width=avatar_size_px,
        height=avatar_size_px,
        border_radius=avatar_size_px // 2,
        bgcolor=resolved_background_color,
        alignment=ft.Alignment.CENTER,
    )


def build_status_badge(
    badge_label: str,
    badge_color: str,
    is_filled_style: bool = True,
) -> ft.Container:
    text_color = ThemeColor.TEXT_PRIMARY if is_filled_style else badge_color
    background_color = (
        badge_color if is_filled_style else ft.Colors.with_opacity(0.14, badge_color)
    )
    border = (
        ft.border.all(1, ft.Colors.with_opacity(0.4, badge_color))
        if not is_filled_style
        else None
    )
    return ft.Container(
        content=ft.Text(
            badge_label,
            size=12,
            color=text_color,
            weight=ft.FontWeight.W_700,
            no_wrap=True,
        ),
        bgcolor=background_color,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        border=border,
    )


def build_icon_box(
    icon_name: str,
    icon_color: str,
    icon_size_px: int = 22,
    box_padding: int = 12,
    box_border_radius: int = 14,
) -> ft.Container:
    return ft.Container(
        content=ft.Icon(icon_name, color=icon_color, size=icon_size_px),
        bgcolor=ft.Colors.with_opacity(0.14, icon_color),
        border_radius=box_border_radius,
        padding=box_padding,
    )


def build_progress_bar(
    fill_percentage: float,
    bar_color: str = ThemeColor.ACCENT_VIOLET,
    bar_height_px: int = 8,
    fixed_width_px: int | None = None,
) -> ft.Container:
    clipped = max(0.0, min(fill_percentage / 100, 1.0))
    kwargs: dict = {
        "value": clipped,
        "color": bar_color,
        "bgcolor": ft.Colors.with_opacity(0.15, bar_color),
        "bar_height": bar_height_px,
        "border_radius": ft.border_radius.all(bar_height_px),
    }
    if fixed_width_px:
        kwargs["width"] = fixed_width_px
    else:
        kwargs["expand"] = True
    return ft.ProgressBar(**kwargs)


def build_card(
    card_content: ft.Control,
    card_padding: int = CARD_DEFAULT_PADDING,
    card_border_radius: int = CARD_DEFAULT_BORDER_RADIUS,
    card_background_color: str = ThemeColor.CARD_BACKGROUND,
    should_expand: bool = False,
    has_border: bool = True,
    **extra_kwargs,
) -> ft.Container:
    return ft.Container(
        content=card_content,
        bgcolor=card_background_color,
        border_radius=card_border_radius,
        padding=card_padding,
        expand=should_expand,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT) if has_border else None,
        **extra_kwargs,
    )


def build_section_header(
    title_text: str,
    subtitle_text: str = "",
    action_button_controls: list | None = None,
) -> ft.Row:
    left_column = ft.Column(
        [
            ft.Text(
                title_text,
                size=FONT_SIZE_TITLE,
                weight=ft.FontWeight.BOLD,
                color=ThemeColor.TEXT_PRIMARY,
            ),
            (
                ft.Text(subtitle_text, size=FONT_SIZE_BODY, color=ThemeColor.TEXT_MUTED)
                if subtitle_text
                else ft.Container(height=0)
            ),
        ],
        spacing=3,
    )
    row_children: list[ft.Control] = [left_column, ft.Container(expand=True)]
    if action_button_controls:
        row_children.extend(action_button_controls)
    return ft.Row(
        row_children,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=14,
    )


def build_filled_action_button(
    button_label: str,
    button_icon: str | None = None,
    on_click_handler=None,
    button_color: str = ThemeColor.ACCENT_VIOLET,
    is_small_size: bool = False,
) -> ft.FilledButton:
    return ft.FilledButton(
        button_label,
        icon=button_icon,
        on_click=on_click_handler,
        height=40 if is_small_size else 48,
        style=ft.ButtonStyle(
            bgcolor=button_color,
            color=ThemeColor.TEXT_PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.padding.symmetric(
                horizontal=18 if is_small_size else 24, vertical=0
            ),
        ),
    )


def build_outlined_action_button(
    button_label: str,
    button_icon: str | None = None,
    on_click_handler=None,
    button_color: str = ThemeColor.ACCENT_VIOLET,
    is_small_size: bool = False,
) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        button_label,
        icon=button_icon,
        on_click=on_click_handler,
        height=40 if is_small_size else 48,
        style=ft.ButtonStyle(
            color=button_color,
            side=ft.BorderSide(1, ft.Colors.with_opacity(0.4, button_color)),
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.padding.symmetric(
                horizontal=18 if is_small_size else 24, vertical=0
            ),
        ),
    )


def build_icon_action_button(
    icon_name: str,
    icon_color: str,
    on_click_handler=None,
) -> ft.IconButton:
    return ft.IconButton(
        icon_name,
        icon_color=icon_color,
        icon_size=18,
        on_click=on_click_handler,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.09, icon_color),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )


def build_body_text(
    text_content: str,
    text_color: str = ThemeColor.TEXT_SECONDARY,
    is_bold: bool = False,
    font_size: int = FONT_SIZE_BODY,
    should_wrap: bool = True,
) -> ft.Text:
    return ft.Text(
        text_content,
        size=font_size,
        color=text_color,
        weight=ft.FontWeight.W_600 if is_bold else ft.FontWeight.NORMAL,
        no_wrap=not should_wrap,
        overflow=ft.TextOverflow.ELLIPSIS,
    )


def build_stat_card(
    stat_icon: str,
    stat_label: str,
    stat_display_value: str | int | float,
    stat_subtitle_text: str | None = None,
    icon_and_trend_color: str = ThemeColor.ACCENT_VIOLET,
    trend_percentage: float | None = None,
) -> ft.Container:
    trend_row: ft.Control = ft.Container()
    if trend_percentage is not None:
        is_upward_trend = trend_percentage > 0
        trend_color = (
            ThemeColor.ACCENT_GREEN if is_upward_trend else ThemeColor.ACCENT_ROSE
        )
        trend_row = ft.Row(
            [
                ft.Icon(
                    (
                        ft.Icons.ARROW_UPWARD
                        if is_upward_trend
                        else ft.Icons.ARROW_DOWNWARD
                    ),
                    size=13,
                    color=trend_color,
                ),
                ft.Text(
                    f"{abs(trend_percentage)}%",
                    size=13,
                    color=trend_color,
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=3,
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        build_icon_box(stat_icon, icon_and_trend_color, 22, 12, 12),
                        ft.Container(expand=True),
                        trend_row,
                    ]
                ),
                build_vertical_spacer(14),
                ft.Text(
                    str(stat_display_value),
                    size=FONT_SIZE_STAT_VALUE,
                    weight=ft.FontWeight.BOLD,
                    color=ThemeColor.TEXT_PRIMARY,
                ),
                build_vertical_spacer(2),
                ft.Text(
                    stat_label, size=FONT_SIZE_BODY, color=ThemeColor.TEXT_SECONDARY
                ),
                (
                    ft.Text(stat_subtitle_text, size=12, color=ThemeColor.TEXT_MUTED)
                    if stat_subtitle_text
                    else ft.Container(height=0)
                ),
            ],
            spacing=3,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        border_radius=CARD_DEFAULT_BORDER_RADIUS,
        padding=CARD_DEFAULT_PADDING,
        border=ft.border.all(1, ThemeColor.BORDER_DEFAULT),
    )


def build_info_banner(
    banner_icon: str,
    banner_title: str,
    banner_subtitle: str,
    banner_color: str = ThemeColor.ACCENT_VIOLET,
    trailing_widget: ft.Control | None = None,
) -> ft.Container:
    row_children: list[ft.Control] = [
        ft.Container(
            content=ft.Icon(
                banner_icon,
                color=ft.Colors.with_opacity(0.9, banner_color),
                size=26,
            ),
            bgcolor=ft.Colors.with_opacity(0.1, banner_color),
            border_radius=14,
            padding=14,
            border=ft.border.all(1, ft.Colors.with_opacity(0.22, banner_color)),
        ),
        ft.Column(
            [
                ft.Text(
                    banner_title,
                    size=FONT_SIZE_BODY_LARGE,
                    color=ThemeColor.TEXT_PRIMARY,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(banner_subtitle, size=12, color=ThemeColor.TEXT_MUTED),
            ],
            spacing=3,
            expand=True,
        ),
    ]
    if trailing_widget:
        row_children.append(trailing_widget)

    return ft.Container(
        content=ft.Row(
            row_children,
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.05, banner_color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.18, banner_color)),
        border_radius=14,
        padding=18,
    )


def build_mini_bar_chart(
    bar_values: list[int | float],
    bar_labels: list[str],
    bar_color: str = ThemeColor.ACCENT_VIOLET,
    chart_height_px: int = 170,
) -> ft.Row:
    maximum_value = max(bar_values) if bar_values else 1
    bar_column_controls: list[ft.Control] = []

    for individual_value, individual_label in zip(bar_values, bar_labels):
        bar_fill_height = max(
            6, int((individual_value / maximum_value) * (chart_height_px - 52))
        )
        value_display = (
            str(individual_value)
            if individual_value < 1000
            else f"{individual_value // 1000}K"
        )
        bar_column_controls.append(
            ft.Column(
                [
                    ft.Text(
                        value_display,
                        size=11,
                        color=ThemeColor.TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        border_radius=ft.border_radius.only(top_left=6, top_right=6),
                        height=bar_fill_height,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_CENTER,
                            end=ft.Alignment.BOTTOM_CENTER,
                            colors=[
                                ft.Colors.with_opacity(1.0, bar_color),
                                ft.Colors.with_opacity(0.35, bar_color),
                            ],
                        ),
                    ),
                    build_vertical_spacer(6),
                    ft.Text(
                        individual_label,
                        size=11,
                        color=ThemeColor.TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                expand=True,
                height=chart_height_px,
            )
        )

    return ft.Row(
        bar_column_controls,
        spacing=10,
        expand=True,
        height=chart_height_px,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def build_auth_text_field(
    field_label: str,
    field_hint: str,
    field_prefix_icon: str,
    is_password_field: bool = False,
) -> ft.TextField:
    return ft.TextField(
        label=field_label,
        hint_text=field_hint,
        prefix_icon=field_prefix_icon,
        password=is_password_field,
        can_reveal_password=is_password_field,
        bgcolor=ThemeColor.SURFACE_PRIMARY,
        border_color=ThemeColor.BORDER_SUBTLE,
        focused_border_color=ThemeColor.ACCENT_VIOLET,
        color=ThemeColor.TEXT_PRIMARY,
        label_style=ft.TextStyle(color=ThemeColor.TEXT_MUTED),
        hint_style=ft.TextStyle(color=ThemeColor.TEXT_MUTED),
        border_radius=14,
        text_size=15,
    )


def build_nav_section_label(section_label_text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            section_label_text,
            size=10,
            color=ThemeColor.TEXT_MUTED,
            weight=ft.FontWeight.W_700,
        ),
        padding=ft.padding.only(left=18, top=16, bottom=5),
    )


def build_scrollable_page_column(*child_controls: ft.Control) -> ft.Column:
    return ft.Column(
        list(child_controls),
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def show_toast(
    flet_page: ft.Page,
    message: str,
    is_error: bool = False,
    duration_ms: int = 3000,
) -> None:
    color = ThemeColor.ACCENT_ROSE if is_error else ThemeColor.ACCENT_GREEN
    snack = ft.SnackBar(
        content=ft.Row(
            [
                ft.Icon(
                    (
                        ft.Icons.ERROR_OUTLINE
                        if is_error
                        else ft.Icons.CHECK_CIRCLE_OUTLINE
                    ),
                    color=color,
                    size=20,
                ),
                ft.Text(message, color=ThemeColor.TEXT_PRIMARY, size=14, expand=True),
            ],
            spacing=10,
        ),
        bgcolor=ThemeColor.CARD_BACKGROUND,
        duration=duration_ms,
        show_close_icon=True,
        close_icon_color=ThemeColor.TEXT_MUTED,
        behavior=ft.SnackBarBehavior.FLOATING,
        shape=ft.RoundedRectangleBorder(radius=12),
        margin=ft.margin.only(bottom=20, left=20, right=20),
    )
    flet_page.overlay.append(snack)
    snack.open = True
    flet_page.update()


def build_csv_import_button(on_click_handler) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        "Import CSV",
        icon=ft.Icons.UPLOAD_FILE,
        on_click=on_click_handler,
        height=46,
        style=ft.ButtonStyle(
            color=ThemeColor.ACCENT_VIOLET,
            side=ft.BorderSide(1.5, ThemeColor.ACCENT_VIOLET),
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )


def build_loading_container(step_text: str = "Loading…") -> ft.Container:
    bar = ft.ProgressBar(
        expand=True,
        value=None,
        color=ThemeColor.ACCENT_VIOLET,
        bgcolor=ft.Colors.with_opacity(0.15, ThemeColor.ACCENT_VIOLET),
        bar_height=5,
        border_radius=ft.border_radius.all(4),
    )
    ring = ft.ProgressRing(
        width=22,
        height=22,
        stroke_width=3,
        color=ThemeColor.ACCENT_VIOLET,
    )
    label = ft.Text(step_text, size=13, color=ThemeColor.ACCENT_VIOLET)
    container = ft.Container(
        visible=False,
        content=ft.Column(
            [
                bar,
                build_vertical_spacer(8),
                ft.Row(
                    [ring, label],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=0,
        ),
        bgcolor=ft.Colors.with_opacity(0.06, ThemeColor.ACCENT_VIOLET),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ThemeColor.ACCENT_VIOLET)),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=18, vertical=12),
    )
    # Attach refs so callers can reach them without separate variables
    container._loading_bar = bar  # type: ignore[attr-defined]
    container._loading_ring = ring  # type: ignore[attr-defined]
    container._loading_label = label  # type: ignore[attr-defined]
    return container
