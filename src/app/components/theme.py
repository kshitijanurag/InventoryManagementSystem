from enum import Enum


class ThemeColor(str, Enum):
    BACKGROUND_DEEPEST = "#080B14"  # Page background
    SURFACE_PRIMARY = "#0D1120"  # Sidebar, topbar, table bg
    CARD_BACKGROUND = "#111827"  # Card fill

    ACCENT_VIOLET = "#7C6FFF"  # Primary interactive accent
    ACCENT_VIOLET_LIGHT = "#A89BFF"  # Hover / lighter variant
    ACCENT_TEAL = "#00C9A7"  # Secondary accent
    ACCENT_ROSE = "#FF4D6D"  # Danger / destructive
    ACCENT_AMBER = "#FFB347"  # Warning
    ACCENT_GREEN = "#22D3A5"  # Success / positive trend

    TEXT_PRIMARY = "#F0F2FF"  # Body / headings
    TEXT_SECONDARY = "#A0AACB"  # Captions, sub-labels
    TEXT_MUTED = "#5A6480"  # Placeholder, disabled

    BORDER_DEFAULT = "#1E2640"
    BORDER_SUBTLE = "#252D45"

    AVATAR_PURPLE = "#9B59B6"
    AVATAR_ORANGE = "#E67E22"
    AVATAR_CYAN = "#1ABC9C"


AVATAR_COLOR_CYCLE = [
    ThemeColor.ACCENT_VIOLET,
    ThemeColor.ACCENT_TEAL,
    ThemeColor.ACCENT_ROSE,
    ThemeColor.ACCENT_AMBER,
    ThemeColor.AVATAR_PURPLE,
    ThemeColor.AVATAR_ORANGE,
    ThemeColor.AVATAR_CYAN,
]

FONT_SIZE_LABEL = 10  # Section group labels
FONT_SIZE_CAPTION = 11  # Timestamps, muted info
FONT_SIZE_BODY_SMALL = 12  # Table secondary cells
FONT_SIZE_BODY = 14  # Standard body text
FONT_SIZE_BODY_LARGE = 15  # Dialog / banner titles
FONT_SIZE_SUBTITLE = 16  # Card headings
FONT_SIZE_TITLE = 24  # Page section titles
FONT_SIZE_HEADLINE = 30  # Dashboard greeting, auth headings
FONT_SIZE_STAT_VALUE = 32  # Stat card numbers

SIDEBAR_WIDTH_PX = 264
TOPBAR_HORIZONTAL_PADDING = 28
PAGE_HORIZONTAL_PADDING = 30
PAGE_VERTICAL_PADDING = 20
CARD_DEFAULT_PADDING = 22
CARD_DEFAULT_BORDER_RADIUS = 16
NAV_ITEM_HEIGHT_PX = 48

import flet as ft

NAVIGATION_ITEM_DEFINITIONS = [
    ("dashboard", ft.Icons.DASHBOARD, "Dashboard"),
    ("products", ft.Icons.INVENTORY, "Products"),
    ("products_return", ft.Icons.ASSIGNMENT_RETURNED, "Products Return"),
    ("categories", ft.Icons.CATEGORY, "Categories"),
    ("sales", ft.Icons.SHOPPING_CART, "Sales"),
    ("suppliers", ft.Icons.LOCAL_SHIPPING, "Suppliers"),
    ("employees", ft.Icons.PEOPLE, "Employees"),
    ("forecast", ft.Icons.TRENDING_UP, "Demand Forecast"),
    ("reorder", ft.Icons.AUTORENEW, "Smart Reorder"),
    ("risk", ft.Icons.WARNING, "Risk & Alerts"),
    ("data_cleaning", ft.Icons.CLEANING_SERVICES, "Data Cleaning"),
    ("purchase_orders", ft.Icons.RECEIPT, "Purchase Orders"),
    ("admin", ft.Icons.ADMIN_PANEL_SETTINGS, "Admin Panel"),
]

NAVIGATION_GROUP_STRUCTURE = [
    ("OVERVIEW", ["dashboard"]),
    ("INVENTORY", ["products", "products_return", "categories", "suppliers"]),
    ("OPERATIONS", ["sales", "purchase_orders", "employees"]),
    ("AI & INTEL", ["forecast", "reorder", "data_cleaning"]),
    ("SYSTEM", ["risk", "admin"]),
]
