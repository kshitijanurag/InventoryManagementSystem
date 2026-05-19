import flet as ft

_FALLBACK_PRODUCTS = [
    {
        "id": "P001",
        "name": "Laptop Pro 15",
        "category": "Electronics",
        "stock": 45,
        "price": 1299.99,
        "reorder": 10,
        "supplier": "TechCorp",
    },
    {
        "id": "P002",
        "name": "Wireless Mouse",
        "category": "Electronics",
        "stock": 8,
        "price": 29.99,
        "reorder": 20,
        "supplier": "GadgetHub",
    },
    {
        "id": "P003",
        "name": "Office Chair",
        "category": "Furniture",
        "stock": 0,
        "price": 349.99,
        "reorder": 5,
        "supplier": "FurniturePlus",
    },
    {
        "id": "P004",
        "name": "Standing Desk",
        "category": "Furniture",
        "stock": 12,
        "price": 599.99,
        "reorder": 8,
        "supplier": "FurniturePlus",
    },
    {
        "id": "P005",
        "name": "USB-C Hub",
        "category": "Electronics",
        "stock": 3,
        "price": 49.99,
        "reorder": 15,
        "supplier": "TechCorp",
    },
    {
        "id": "P006",
        "name": 'Monitor 27"',
        "category": "Electronics",
        "stock": 22,
        "price": 449.99,
        "reorder": 10,
        "supplier": "DisplayMasters",
    },
    {
        "id": "P007",
        "name": "Keyboard Mech",
        "category": "Electronics",
        "stock": 31,
        "price": 129.99,
        "reorder": 12,
        "supplier": "GadgetHub",
    },
    {
        "id": "P008",
        "name": "Desk Lamp LED",
        "category": "Lighting",
        "stock": 6,
        "price": 39.99,
        "reorder": 10,
        "supplier": "LightCo",
    },
]

_FALLBACK_CATEGORIES = [
    {"id": "C001", "name": "Electronics", "products": 5, "value": 89430},
    {"id": "C002", "name": "Furniture", "products": 2, "value": 12399},
    {"id": "C003", "name": "Lighting", "products": 1, "value": 2399},
    {"id": "C004", "name": "Office Supplies", "products": 8, "value": 4120},
]

_FALLBACK_SUPPLIERS = [
    {
        "id": "S001",
        "name": "TechCorp",
        "contact": "tech@techcorp.com",
        "products": 2,
        "rating": 4.8,
        "status": "Active",
    },
    {
        "id": "S002",
        "name": "GadgetHub",
        "contact": "info@gadgethub.com",
        "products": 2,
        "rating": 4.5,
        "status": "Active",
    },
    {
        "id": "S003",
        "name": "FurniturePlus",
        "contact": "order@furnplus.com",
        "products": 2,
        "rating": 4.2,
        "status": "Active",
    },
    {
        "id": "S004",
        "name": "DisplayMasters",
        "contact": "sales@dispmas.com",
        "products": 1,
        "rating": 4.7,
        "status": "Active",
    },
    {
        "id": "S005",
        "name": "LightCo",
        "contact": "hi@lightco.com",
        "products": 1,
        "rating": 3.9,
        "status": "Inactive",
    },
]

_FALLBACK_EMPLOYEES = [
    {
        "id": "E001",
        "name": "Alice Johnson",
        "role": "Inventory Manager",
        "dept": "Operations",
        "status": "Active",
        "email": "alice@company.com",
    },
    {
        "id": "E002",
        "name": "Bob Smith",
        "role": "Warehouse Lead",
        "dept": "Logistics",
        "status": "Active",
        "email": "bob@company.com",
    },
    {
        "id": "E003",
        "name": "Carol Davis",
        "role": "Purchasing Agent",
        "dept": "Procurement",
        "status": "Active",
        "email": "carol@company.com",
    },
    {
        "id": "E004",
        "name": "David Lee",
        "role": "Data Analyst",
        "dept": "Analytics",
        "status": "On Leave",
        "email": "david@company.com",
    },
    {
        "id": "E005",
        "name": "Eva Martinez",
        "role": "Admin",
        "dept": "HR",
        "status": "Active",
        "email": "eva@company.com",
    },
]

_FALLBACK_PURCHASE_ORDERS = [
    {
        "id": "PO001",
        "supplier": "TechCorp",
        "product": "Laptop Pro 15",
        "qty": 20,
        "total": 25999.80,
        "status": "Pending",
        "date": "2026-03-01",
    },
    {
        "id": "PO002",
        "supplier": "GadgetHub",
        "product": "Wireless Mouse",
        "qty": 50,
        "total": 1499.50,
        "status": "Approved",
        "date": "2026-02-28",
    },
    {
        "id": "PO003",
        "supplier": "FurniturePlus",
        "product": "Office Chair",
        "qty": 10,
        "total": 3499.90,
        "status": "Delivered",
        "date": "2026-02-25",
    },
    {
        "id": "PO004",
        "supplier": "TechCorp",
        "product": "USB-C Hub",
        "qty": 30,
        "total": 1499.70,
        "status": "Pending",
        "date": "2026-03-02",
    },
    {
        "id": "PO005",
        "supplier": "LightCo",
        "product": "Desk Lamp LED",
        "qty": 15,
        "total": 599.85,
        "status": "Cancelled",
        "date": "2026-02-20",
    },
]

_FALLBACK_ALERTS = [
    {
        "type": "danger",
        "title": "Out of Stock",
        "msg": "Office Chair (P003) is completely out of stock.",
        "time": "2 min ago",
    },
    {
        "type": "warning",
        "title": "Low Stock Warning",
        "msg": "USB-C Hub has only 3 units left (threshold: 15).",
        "time": "15 min ago",
    },
    {
        "type": "warning",
        "title": "Low Stock Warning",
        "msg": "Wireless Mouse has only 8 units left (threshold: 20).",
        "time": "1 hr ago",
    },
    {
        "type": "warning",
        "title": "Low Stock Warning",
        "msg": "Desk Lamp LED has only 6 units left.",
        "time": "3 hr ago",
    },
    {
        "type": "info",
        "title": "AI Forecast Update",
        "msg": "Demand forecast recalculated for Q2 2026.",
        "time": "5 hr ago",
    },
    {
        "type": "success",
        "title": "PO Delivered",
        "msg": "Purchase Order PO003 from FurniturePlus delivered.",
        "time": "1 day ago",
    },
]

_FALLBACK_AI_MODELS = [
    {
        "name": "Demand Forecasting LSTM",
        "type": "Time Series",
        "accuracy": 91.4,
        "status": "Active",
        "last_train": "2026-03-01",
    },
    {
        "name": "Reorder Point Optimizer",
        "type": "Regression",
        "accuracy": 88.7,
        "status": "Active",
        "last_train": "2026-02-28",
    },
    {
        "name": "Anomaly Detector",
        "type": "Unsupervised",
        "accuracy": 94.2,
        "status": "Active",
        "last_train": "2026-02-25",
    },
    {
        "name": "Price Sensitivity Model",
        "type": "Classification",
        "accuracy": 83.1,
        "status": "Training",
        "last_train": "2026-03-03",
    },
    {
        "name": "Supplier Risk Scorer",
        "type": "Ensemble",
        "accuracy": 79.5,
        "status": "Inactive",
        "last_train": "2026-02-10",
    },
]

_FALLBACK_ADMIN_SYSTEM_SETTINGS = [
    ("Company Name", "InventoryAI Corp", ft.Icons.BUSINESS),
    ("Currency", "USD ($)", ft.Icons.ATTACH_MONEY),
    ("Timezone", "UTC-5 (EST)", ft.Icons.ACCESS_TIME),
    ("Fiscal Year", "January", ft.Icons.CALENDAR_TODAY),
    ("Low Stock Threshold", "10 units", ft.Icons.WARNING),
    ("AI Reorder Mode", "Automatic", ft.Icons.AUTORENEW),
]

_FALLBACK_NOTIFICATION_SETTINGS = [
    ("Low stock email alerts", True),
    ("Daily inventory digest", True),
    ("AI reorder notifications", True),
    ("Supplier delay alerts", False),
    ("Weekly analytics report", True),
]

_FALLBACK_SECURITY_SETTINGS = [
    ("Two-factor authentication", True),
    ("Session timeout (30 min)", True),
    ("Audit logging", True),
    ("IP whitelist", False),
]
