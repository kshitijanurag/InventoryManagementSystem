from __future__ import annotations

import random
from datetime import datetime, timedelta

from src.database.mongo_connection import get_inventory_database
from src.app.services.authentication_service import seed_default_admin_user_if_absent


def _seed_categories(inventory_db) -> None:
    if inventory_db["categories"].count_documents({}) > 0:
        print("  ⏭  categories: already seeded, skipping.")
        return
    inventory_db["categories"].insert_many(
        [
            {"category_id": "C001", "name": "Electronics"},
            {"category_id": "C002", "name": "Furniture"},
            {"category_id": "C003", "name": "Lighting"},
            {"category_id": "C004", "name": "Office Supplies"},
        ]
    )
    print("  ✅ categories seeded.")


def _seed_suppliers(inventory_db) -> None:
    if inventory_db["suppliers"].count_documents({}) > 0:
        print("  ⏭  suppliers: already seeded, skipping.")
        return
    inventory_db["suppliers"].insert_many(
        [
            {
                "supplier_id": "S001",
                "name": "TechCorp",
                "contact": "tech@techcorp.com",
                "products": 2,
                "rating": 4.8,
                "status": "Active",
            },
            {
                "supplier_id": "S002",
                "name": "GadgetHub",
                "contact": "info@gadgethub.com",
                "products": 2,
                "rating": 4.5,
                "status": "Active",
            },
            {
                "supplier_id": "S003",
                "name": "FurniturePlus",
                "contact": "order@furnplus.com",
                "products": 2,
                "rating": 4.2,
                "status": "Active",
            },
            {
                "supplier_id": "S004",
                "name": "DisplayMasters",
                "contact": "sales@dispmas.com",
                "products": 1,
                "rating": 4.7,
                "status": "Active",
            },
            {
                "supplier_id": "S005",
                "name": "LightCo",
                "contact": "hi@lightco.com",
                "products": 1,
                "rating": 3.9,
                "status": "Inactive",
            },
        ]
    )
    print("  ✅ suppliers seeded.")


def _seed_products(inventory_db) -> None:
    if inventory_db["products"].count_documents({}) > 0:
        print("  ⏭  products: already seeded, skipping.")
        return
    inventory_db["products"].insert_many(
        [
            {
                "product_id": "P001",
                "name": "Laptop Pro 15",
                "category_id": "Electronics",
                "supplier_id": "TechCorp",
                "current_stock": 45,
                "reorder_point": 10,
                "selling_price": 1299.99,
                "cost_price": 950.00,
            },
            {
                "product_id": "P002",
                "name": "Wireless Mouse",
                "category_id": "Electronics",
                "supplier_id": "GadgetHub",
                "current_stock": 8,
                "reorder_point": 20,
                "selling_price": 29.99,
                "cost_price": 12.00,
            },
            {
                "product_id": "P003",
                "name": "Office Chair",
                "category_id": "Furniture",
                "supplier_id": "FurniturePlus",
                "current_stock": 0,
                "reorder_point": 5,
                "selling_price": 349.99,
                "cost_price": 200.00,
            },
            {
                "product_id": "P004",
                "name": "Standing Desk",
                "category_id": "Furniture",
                "supplier_id": "FurniturePlus",
                "current_stock": 12,
                "reorder_point": 8,
                "selling_price": 599.99,
                "cost_price": 380.00,
            },
            {
                "product_id": "P005",
                "name": "USB-C Hub",
                "category_id": "Electronics",
                "supplier_id": "TechCorp",
                "current_stock": 3,
                "reorder_point": 15,
                "selling_price": 49.99,
                "cost_price": 18.00,
            },
            {
                "product_id": "P006",
                "name": 'Monitor 27"',
                "category_id": "Electronics",
                "supplier_id": "DisplayMasters",
                "current_stock": 22,
                "reorder_point": 10,
                "selling_price": 449.99,
                "cost_price": 280.00,
            },
            {
                "product_id": "P007",
                "name": "Keyboard Mech",
                "category_id": "Electronics",
                "supplier_id": "GadgetHub",
                "current_stock": 31,
                "reorder_point": 12,
                "selling_price": 129.99,
                "cost_price": 60.00,
            },
            {
                "product_id": "P008",
                "name": "Desk Lamp LED",
                "category_id": "Lighting",
                "supplier_id": "LightCo",
                "current_stock": 6,
                "reorder_point": 10,
                "selling_price": 39.99,
                "cost_price": 14.00,
            },
        ]
    )
    print("  ✅ products seeded.")


def _seed_employees(inventory_db) -> None:
    if inventory_db["employees"].count_documents({}) > 0:
        print("  ⏭  employees: already seeded, skipping.")
        return
    inventory_db["employees"].insert_many(
        [
            {
                "employee_id": "E001",
                "name": "Alice Johnson",
                "role": "Inventory Manager",
                "dept": "Operations",
                "status": "Active",
                "email": "alice@company.com",
            },
            {
                "employee_id": "E002",
                "name": "Bob Smith",
                "role": "Warehouse Lead",
                "dept": "Logistics",
                "status": "Active",
                "email": "bob@company.com",
            },
            {
                "employee_id": "E003",
                "name": "Carol Davis",
                "role": "Purchasing Agent",
                "dept": "Procurement",
                "status": "Active",
                "email": "carol@company.com",
            },
            {
                "employee_id": "E004",
                "name": "David Lee",
                "role": "Data Analyst",
                "dept": "Analytics",
                "status": "On Leave",
                "email": "david@company.com",
            },
            {
                "employee_id": "E005",
                "name": "Eva Martinez",
                "role": "Admin",
                "dept": "HR",
                "status": "Active",
                "email": "eva@company.com",
            },
        ]
    )
    print("  ✅ employees seeded.")


def _seed_purchase_orders(inventory_db) -> None:
    if inventory_db["purchase_orders"].count_documents({}) > 0:
        print("  ⏭  purchase_orders: already seeded, skipping.")
        return
    inventory_db["purchase_orders"].insert_many(
        [
            {
                "po_id": "PO001",
                "supplier_id": "TechCorp",
                "product_id": "Laptop Pro 15",
                "quantity": 20,
                "total": 25999.80,
                "status": "Pending",
                "order_date": "2026-03-01",
            },
            {
                "po_id": "PO002",
                "supplier_id": "GadgetHub",
                "product_id": "Wireless Mouse",
                "quantity": 50,
                "total": 1499.50,
                "status": "Approved",
                "order_date": "2026-02-28",
            },
            {
                "po_id": "PO003",
                "supplier_id": "FurniturePlus",
                "product_id": "Office Chair",
                "quantity": 10,
                "total": 3499.90,
                "status": "Delivered",
                "order_date": "2026-02-25",
            },
            {
                "po_id": "PO004",
                "supplier_id": "TechCorp",
                "product_id": "USB-C Hub",
                "quantity": 30,
                "total": 1499.70,
                "status": "Pending",
                "order_date": "2026-03-02",
            },
            {
                "po_id": "PO005",
                "supplier_id": "LightCo",
                "product_id": "Desk Lamp LED",
                "quantity": 15,
                "total": 599.85,
                "status": "Cancelled",
                "order_date": "2026-02-20",
            },
        ]
    )
    print("  ✅ purchase_orders seeded.")


def _seed_sales_history(inventory_db) -> None:
    if inventory_db["sales"].count_documents({}) > 0:
        print("  ⏭  sales: already seeded, skipping.")
        return
    random.seed(12345)
    product_price_map = [
        ("P001", "Laptop Pro 15", 1299.99),
        ("P002", "Wireless Mouse", 29.99),
        ("P004", "Standing Desk", 599.99),
        ("P006", 'Monitor 27"', 449.99),
        ("P007", "Keyboard Mech", 129.99),
    ]
    base_date = datetime(2025, 10, 1)
    sales_records = []
    for day_offset in range(180):
        transaction_date = base_date + timedelta(days=day_offset)
        for _ in range(random.randint(1, 8)):
            product_id, product_name, selling_price = random.choice(product_price_map)
            qty = random.randint(1, 5)
            sales_records.append(
                {
                    "invoice_id": f"INV-{len(sales_records) + 1000}",
                    "product_id": product_id,
                    "product_name": product_name,
                    "quantity": qty,
                    "selling_price": selling_price,
                    "cost_price": selling_price * 0.65,
                    "total": round(selling_price * qty, 2),
                    "profit": round((selling_price * 0.35) * qty, 2),
                    "date": transaction_date.strftime("%Y-%m-%d"),
                    "created_at": transaction_date,
                    "category_id": "Electronics",
                }
            )
    inventory_db["sales"].insert_many(sales_records)
    print(f"  ✅ sales seeded: {len(sales_records)} records.")
    random.seed()


def run_full_database_seed() -> None:
    print("\n🌱 Seeding MongoDB database…\n")
    inventory_db = get_inventory_database()
    _seed_categories(inventory_db)
    _seed_suppliers(inventory_db)
    _seed_products(inventory_db)
    _seed_employees(inventory_db)
    _seed_purchase_orders(inventory_db)
    _seed_sales_history(inventory_db)
    seed_default_admin_user_if_absent()
    print("\n✅ Database seed complete.\n")


if __name__ == "__main__":
    run_full_database_seed()
