import flet as ft
from ui.theme import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ui.components import (
    build_card,
    build_status_badge,
    build_page_header,
    build_stat_card,
    build_data_table,
    build_action_button,
)
from data.constants import ALL_PRODUCTS


def build_reorder_page(flet_page: ft.Page):
    products_below_reorder_threshold = [
        product for product in ALL_PRODUCTS if product["stock"] < product["reorder"]
    ]

    reorder_suggestion_rows = [
        ft.DataRow(
            cells=[
                ft.DataCell(
                    ft.Text(product_entry["name"], color=TEXT_PRIMARY, size=13)
                ),
                ft.DataCell(
                    ft.Text(
                        str(product_entry["stock"]),
                        color=(
                            COLOR_DANGER
                            if product_entry["stock"] == 0
                            else COLOR_WARNING
                        ),
                        size=13,
                        weight=ft.FontWeight.W_600,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(product_entry["reorder"]),
                        color=TEXT_SECONDARY,
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(product_entry["reorder"] * 3),
                        color=ACCENT_SECONDARY,
                        size=13,
                    )
                ),
                ft.DataCell(
                    ft.Text(product_entry["supplier"], color=TEXT_SECONDARY, size=12)
                ),
                ft.DataCell(
                    ft.Text(
                        f'₹{product_entry["reorder"] * 3 * product_entry["price"]:,.0f}',
                        color=TEXT_PRIMARY,
                        size=13,
                    )
                ),
                ft.DataCell(
                    ft.ElevatedButton(
                        "Create Product Order",
                        bgcolor=ACCENT_PRIMARY,
                        color=TEXT_PRIMARY,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        height=32,
                    )
                ),
            ]
        )
        for product_entry in products_below_reorder_threshold
    ]

    ai_intelligence_banner = build_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LIGHTBULB, color=ACCENT_PRIMARY, size=20),
                        ft.Text(
                            "AI Reorder Intelligence Active",
                            color=TEXT_PRIMARY,
                            size=14,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Container(expand=True),
                        build_status_badge("AUTO-MODE ON", COLOR_SUCCESS),
                    ],
                    spacing=10,
                ),
                ft.Container(height=8),
                ft.Text(
                    "The AI engine monitors stock levels 24/7 and auto-suggests reorder quantities based on lead times, demand forecasts, and cost optimization.",
                    color=TEXT_SECONDARY,
                    size=13,
                ),
            ],
            spacing=0,
        ),
        card_background_color=ft.Colors.with_opacity(0.1, ACCENT_PRIMARY),
    )

    reorder_table_card = build_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Reorder Recommendations",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=TEXT_PRIMARY,
                        ),
                        ft.Container(expand=True),
                        build_action_button(
                            "Approve All", ft.Icons.DONE_ALL, button_color=COLOR_SUCCESS
                        ),
                    ]
                ),
                ft.Container(height=12),
                build_data_table(
                    column_labels=[
                        "Product",
                        "Current Stock",
                        "Min Threshold",
                        "Suggested Qty",
                        "Supplier",
                        "Est. Cost",
                        "Action",
                    ],
                    table_rows=reorder_suggestion_rows,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        )
    )

    return ft.Column(
        [
            build_page_header(
                header_title="Smart Reorder",
                header_subtitle="AI recommended reorder suggestions",
                header_icon=ft.Icons.AUTORENEW,
            ),
            ft.Container(height=20),
            ai_intelligence_banner,
            ft.Container(height=20),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.WARNING,
                                "Items to Reorder",
                                len(products_below_reorder_threshold),
                                None,
                                COLOR_DANGER,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.ATTACH_MONEY,
                                "Est. PO Value",
                                "₹12,450",
                                None,
                                ACCENT_PRIMARY,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.LOCAL_SHIPPING,
                                "Preferred Suppliers",
                                "3",
                                None,
                                ACCENT_SECONDARY,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.SCHEDULE,
                                "Avg Lead Time",
                                "5 days",
                                None,
                                COLOR_WARNING,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                ],
                spacing=16,
            ),
            ft.Container(height=20),
            reorder_table_card,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
