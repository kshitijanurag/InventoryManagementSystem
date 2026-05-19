import flet as ft
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
from io import BytesIO

from src.app.pages.base_page import BasePage
from src.app.components.primitive_components import (
    build_vertical_spacer,
    build_stat_card,
    build_card,
    build_mini_bar_chart,
    build_status_badge,
    build_avatar_circle,
    build_outlined_action_button,
)
from src.app.components.theme import ThemeColor
from src.app.services.analytics_service import (
    load_cleaned_inventory_dataframe,
    compute_monthly_revenue_series,
)
from src.app.services import _FALLBACK_PRODUCTS, _FALLBACK_ALERTS


def _hoverable(container: ft.Container) -> ft.Container:
    def _on_hover(e: ft.HoverEvent) -> None:
        e.control.bgcolor = (
            ft.Colors.with_opacity(0.04, ThemeColor.TEXT_PRIMARY)
            if e.data == "true"
            else "transparent"
        )
        e.control.update()

    container.on_hover = _on_hover
    return container


def _titled_card(
    title: str, body: ft.Control, action_label: str = "View All"
) -> ft.Control:
    return build_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            title,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                        ft.Container(expand=True),
                        build_outlined_action_button(action_label, is_small_size=True),
                    ]
                ),
                build_vertical_spacer(14),
                body,
            ],
            spacing=0,
        )
    )


class DashboardPage(BasePage):

    def build_page_content(self) -> list[ft.Control]:
        df = load_cleaned_inventory_dataframe()
        monthly_revenue = compute_monthly_revenue_series(df)

        products = _FALLBACK_PRODUCTS
        alerts = _FALLBACK_ALERTS

        low_stock = sum(1 for p in products if 0 < p["stock"] < p["reorder"])
        out_of_stock = sum(1 for p in products if p["stock"] == 0)

        return [
            self._greeting_row(),
            build_vertical_spacer(24),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.INVENTORY,
                                "Total Products",
                                len(products),
                                "8 categories",
                                ThemeColor.ACCENT_VIOLET,
                                5,
                            )
                        ],
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.WARNING,
                                "Low Stock",
                                low_stock,
                                "Need attention",
                                ThemeColor.ACCENT_AMBER,
                                -8,
                            )
                        ],
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.CANCEL,
                                "Out of Stock",
                                out_of_stock,
                                "Urgent reorder",
                                ThemeColor.ACCENT_ROSE,
                            )
                        ],
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.RECEIPT,
                                "Pending POs",
                                2,
                                "Worth $27,499",
                                ThemeColor.ACCENT_TEAL,
                                15,
                            )
                        ],
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                ],
                spacing=16,
            ),
            build_vertical_spacer(18),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [build_card(self._revenue_card(monthly_revenue))],
                        col={"xs": 12, "md": 8},
                    ),
                    ft.Column(
                        [build_card(self._stock_health_card(), should_expand=True)],
                        col={"xs": 12, "md": 4},
                    ),
                ],
                spacing=16,
            ),
            build_vertical_spacer(18),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [_titled_card("Live Alerts", self._alert_feed(alerts))],
                        col={"xs": 12, "md": 5},
                    ),
                    ft.Column(
                        [_titled_card("Top Products", self._top_products(products))],
                        col={"xs": 12, "md": 7},
                    ),
                ],
                spacing=16,
            ),
        ]

    def _greeting_row(self) -> ft.Row:
        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            "Good morning, Admin 👋",
                            size=14,
                            color=ThemeColor.TEXT_MUTED,
                        ),
                        ft.Text(
                            "AI Smart Dashboard",
                            size=30,
                            weight=ft.FontWeight.BOLD,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CIRCLE, size=9, color=ThemeColor.ACCENT_GREEN
                            ),
                            ft.Text(
                                "All systems operational",
                                size=13,
                                color=ThemeColor.ACCENT_GREEN,
                            ),
                        ],
                        spacing=6,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.07, ThemeColor.ACCENT_GREEN),
                    border_radius=22,
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    border=ft.border.all(
                        1, ft.Colors.with_opacity(0.2, ThemeColor.ACCENT_GREEN)
                    ),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _revenue_card(self, monthly_revenue: dict) -> ft.Column:
        labels = monthly_revenue.get(
            "labels", ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
        )
        values = monthly_revenue.get("values", [42, 55, 78, 61, 49, 68])
        display_labels = [str(l)[-7:] if len(str(l)) > 7 else str(l) for l in labels]
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Revenue Trend",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=ThemeColor.TEXT_PRIMARY,
                        ),
                        ft.Container(expand=True),
                        build_status_badge(
                            "6 months", ThemeColor.ACCENT_VIOLET, is_filled_style=False
                        ),
                    ]
                ),
                build_vertical_spacer(18),
                build_mini_bar_chart(
                    values, display_labels, ThemeColor.ACCENT_VIOLET, 170
                ),
            ],
            spacing=0,
        )

    def _stock_health_card(self) -> ft.Column:
        from pymongo import MongoClient

        products = list(
            MongoClient("mongodb://localhost:27017/")["inventory"]["products"].find()
        )
        total = len(products) or 1
        in_stock = sum(
            1
            for p in products
            if int(p.get("current_stock", 0)) >= int(p.get("reorder_point", 0))
            and int(p.get("current_stock", 0)) > 0
        )
        out = sum(1 for p in products if int(p.get("current_stock", 0)) == 0)
        low = total - in_stock - out

        in_pct, low_pct, out_pct = (
            round(in_stock / total * 100),
            round(low / total * 100),
            round(out / total * 100),
        )

        fig, ax = plt.subplots(figsize=(3.8, 2.8))
        fig.patch.set_facecolor("#0D1120")
        wedges, texts = ax.pie(
            [max(in_pct, 0.1), max(low_pct, 0.1), max(out_pct, 0.1)],
            colors=[
                ThemeColor.ACCENT_GREEN,
                ThemeColor.ACCENT_AMBER,
                ThemeColor.ACCENT_ROSE,
            ],
            startangle=90,
            wedgeprops=dict(width=0.55, edgecolor="#0D1120", linewidth=2),
        )
        for t, lbl, c in zip(
            texts,
            [f"In Stock\n{in_pct}%", f"Low\n{low_pct}%", f"Out\n{out_pct}%"],
            [ThemeColor.ACCENT_GREEN, ThemeColor.ACCENT_AMBER, ThemeColor.ACCENT_ROSE],
        ):
            t.set_text(lbl)
            t.set_color(c)
            t.set_fontsize(8)
        ax.set_facecolor("#0D1120")
        plt.tight_layout(pad=0.2)
        buf = BytesIO()
        fig.savefig(
            buf, format="png", bbox_inches="tight", dpi=110, facecolor="#0D1120"
        )
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode()
        buf.close()
        plt.close(fig)

        legend = [
            ft.Row(
                [
                    ft.Container(width=10, height=10, border_radius=5, bgcolor=c),
                    ft.Text(lbl, size=12, color=ThemeColor.TEXT_SECONDARY, expand=True),
                    ft.Text(f"{pct}%", size=13, color=c, weight=ft.FontWeight.W_700),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for lbl, pct, c in [
                ("In Stock", in_pct, ThemeColor.ACCENT_GREEN),
                ("Low Stock", low_pct, ThemeColor.ACCENT_AMBER),
                ("Out of Stock", out_pct, ThemeColor.ACCENT_ROSE),
            ]
        ]

        return ft.Column(
            [
                ft.Text(
                    "Stock Health",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ThemeColor.TEXT_PRIMARY,
                ),
                build_vertical_spacer(8),
                ft.Image(
                    src=f"data:image/png;base64,{img_b64}", fit="contain", height=200
                ),
                build_vertical_spacer(8),
                ft.Column(legend, spacing=8),
            ],
            spacing=0,
        )

    def _alert_feed(self, alerts: list[dict]) -> ft.Column:
        color_map = {
            "danger": ThemeColor.ACCENT_ROSE,
            "warning": ThemeColor.ACCENT_AMBER,
            "info": ThemeColor.ACCENT_VIOLET,
            "success": ThemeColor.ACCENT_TEAL,
        }
        rows = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=4,
                            height=44,
                            border_radius=3,
                            bgcolor=color_map.get(a["type"], ThemeColor.TEXT_MUTED),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    a["title"],
                                    size=13,
                                    color=ThemeColor.TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(
                                    a["msg"],
                                    size=12,
                                    color=ThemeColor.TEXT_MUTED,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Text(
                            a["time"],
                            size=11,
                            color=ThemeColor.TEXT_MUTED,
                            no_wrap=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=2, vertical=6),
            )
            for a in alerts[:5]
        ]
        return ft.Column(rows, spacing=8)

    def _top_products(self, products: list[dict]) -> ft.Column:
        rows = []
        for i, p in enumerate(products[:6]):
            stock_color = (
                ThemeColor.ACCENT_GREEN
                if p["stock"] > p["reorder"]
                else (
                    ThemeColor.ACCENT_ROSE
                    if p["stock"] == 0
                    else ThemeColor.ACCENT_AMBER
                )
            )
            rows.append(
                _hoverable(
                    ft.Container(
                        content=ft.Row(
                            [
                                build_avatar_circle(p["name"][0], i, 36),
                                ft.Column(
                                    [
                                        ft.Text(
                                            p["name"],
                                            size=14,
                                            color=ThemeColor.TEXT_PRIMARY,
                                            weight=ft.FontWeight.W_500,
                                            no_wrap=True,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            p["category"],
                                            size=11,
                                            color=ThemeColor.TEXT_MUTED,
                                        ),
                                    ],
                                    spacing=1,
                                    expand=True,
                                ),
                                ft.Text(
                                    f'${p["price"]:,.0f}',
                                    size=13,
                                    color=ThemeColor.TEXT_SECONDARY,
                                    no_wrap=True,
                                ),
                                build_status_badge(
                                    f'{p["stock"]} units',
                                    stock_color,
                                    is_filled_style=False,
                                ),
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(horizontal=6, vertical=8),
                        border_radius=10,
                    )
                )
            )
        return ft.Column(rows, spacing=2)


def build_dashboard_page(flet_page: ft.Page) -> ft.Control:
    return DashboardPage(flet_page).build()
