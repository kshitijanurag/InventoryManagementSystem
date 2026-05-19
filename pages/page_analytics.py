import random
import flet as ft
from ui.theme import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    SURFACE_DARK,
)
from ui.components import (
    build_card,
    build_page_header,
    build_stat_card,
    build_mini_bar_chart,
)
from data.constants import ALL_PRODUCTS

KPI_METRICS = [
    ("Inventory Accuracy", "97.3%", 97, COLOR_SUCCESS),
    ("Order Fulfillment", "94.2%", 94, ACCENT_PRIMARY),
    ("On-Time Delivery", "88.5%", 88, ACCENT_SECONDARY),
    ("Supplier Reliability", "91.8%", 92, COLOR_WARNING),
]

STOCK_MOVEMENT_MONTH_LABELS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
STOCK_MOVEMENT_VALUES = [320, 415, 390, 480, 360, 520]

STOCK_VALUE_CATEGORY_LABELS = ["Electronics", "Furniture", "Office", "Lighting"]
STOCK_VALUE_CATEGORY_AMOUNTS = [89430, 12399, 4120, 2399]

random.seed(42)
TOP_PRODUCT_VELOCITIES = [random.randint(50, 200) for _ in range(5)]
random.seed()


def build_analytics_page(flet_page: ft.Page):
    kpi_metric_rows = []
    for kpi_label, kpi_display_value, kpi_percent, kpi_bar_color in KPI_METRICS:
        kpi_row = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            kpi_label,
                            color=TEXT_SECONDARY,
                            size=13,
                            expand=True,
                        ),
                        ft.Text(
                            kpi_display_value,
                            color=TEXT_PRIMARY,
                            size=13,
                            weight=ft.FontWeight.W_600,
                        ),
                    ]
                ),
                ft.Container(
                    ft.Container(
                        bgcolor=kpi_bar_color,
                        border_radius=4,
                        width=kpi_percent * 3.0,
                    ),
                    bgcolor=SURFACE_DARK,
                    border_radius=4,
                    height=6,
                    width=300,
                ),
            ],
            spacing=6,
        )
        kpi_metric_rows.append(kpi_row)

    top_products_rows = [
        ft.Row(
            [
                ft.Text(
                    f"{product_rank + 1}.",
                    color=TEXT_SECONDARY,
                    size=13,
                    width=20,
                ),
                ft.Text(
                    ALL_PRODUCTS[product_rank]["name"],
                    color=TEXT_PRIMARY,
                    size=13,
                    expand=True,
                ),
                ft.Text(
                    f"{TOP_PRODUCT_VELOCITIES[product_rank]} units/month",
                    color=ACCENT_SECONDARY,
                    size=12,
                ),
            ]
        )
        for product_rank in range(5)
    ]

    stock_value_chart_card = build_card(
        ft.Column(
            [
                ft.Text(
                    "Stock Value by Category",
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_PRIMARY,
                ),
                ft.Container(height=12),
                build_mini_bar_chart(
                    bar_values=STOCK_VALUE_CATEGORY_AMOUNTS,
                    bar_labels=STOCK_VALUE_CATEGORY_LABELS,
                    bar_color=ACCENT_PRIMARY,
                    chart_height=140,
                ),
            ]
        )
    )

    stock_movement_chart_card = build_card(
        ft.Column(
            [
                ft.Text(
                    "Monthly Stock Movement",
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_PRIMARY,
                ),
                ft.Container(height=12),
                build_mini_bar_chart(
                    bar_values=STOCK_MOVEMENT_VALUES,
                    bar_labels=STOCK_MOVEMENT_MONTH_LABELS,
                    bar_color=ACCENT_SECONDARY,
                    chart_height=140,
                ),
            ]
        )
    )

    kpi_snapshot_card = build_card(
        ft.Column(
            [
                ft.Text(
                    "KPI Snapshot",
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_PRIMARY,
                ),
                ft.Container(height=12),
            ]
            + kpi_metric_rows,
            spacing=16,
        )
    )

    top_products_card = build_card(
        ft.Column(
            [
                ft.Text(
                    "Top Moving Products",
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_PRIMARY,
                ),
                ft.Container(height=12),
                *top_products_rows,
            ],
            spacing=10,
        )
    )

    return ft.Column(
        [
            build_page_header(
                header_title="Inventory Analytics",
                header_subtitle="Deep insights and performance metrics",
                header_icon=ft.Icons.BAR_CHART,
            ),
            ft.Container(height=20),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.ATTACH_MONEY,
                                "Total Inventory Value",
                                "₹100,000",
                                7,
                                COLOR_SUCCESS,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.LOOP,
                                "Turnover Rate",
                                "4.5x",
                                12,
                                ACCENT_PRIMARY,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.TIMER,
                                "Days Sales Inventory",
                                "77",
                                -5,
                                ACCENT_SECONDARY,
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                    ft.Column(
                        [
                            build_stat_card(
                                ft.Icons.CALCULATE, "Fill Rate", "95%", 2, COLOR_SUCCESS
                            )
                        ],
                        col={"xs": 6, "md": 3},
                    ),
                ],
                spacing=16,
            ),
            ft.Container(height=20),
            ft.ResponsiveRow(
                [
                    ft.Column([stock_value_chart_card], col={"xs": 12, "md": 6}),
                    ft.Column([stock_movement_chart_card], col={"xs": 12, "md": 6}),
                ],
                spacing=16,
            ),
            ft.Container(height=16),
            ft.ResponsiveRow(
                [
                    ft.Column([kpi_snapshot_card], col={"xs": 12, "md": 6}),
                    ft.Column([top_products_card], col={"xs": 12, "md": 6}),
                ],
                spacing=16,
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
