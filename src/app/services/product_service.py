from __future__ import annotations

from src.database.mongo_connection import get_inventory_database


def _get_products_collection():
    return get_inventory_database()["products"]


def _get_categories_collection():
    return get_inventory_database()["categories"]


def _get_suppliers_collection():
    return get_inventory_database()["suppliers"]


def fetch_all_products(result_limit: int | None = None) -> list[dict]:
    try:
        query_cursor = _get_products_collection().find({}, {"_id": 0})
        if result_limit:
            query_cursor = query_cursor.limit(result_limit)
        return list(query_cursor)
    except Exception as database_error:
        print(f"[ProductService] fetch_all_products error: {database_error}")
        return []


def fetch_products_matching_search_query(search_query_text: str) -> list[dict]:
    products_collection = _get_products_collection()
    stripped_query = search_query_text.strip()

    if not stripped_query:
        return list(products_collection.find({}, {"_id": 0}))

    regex_filter = {"$regex": stripped_query, "$options": "i"}
    return list(
        products_collection.find(
            {
                "$or": [
                    {"name": regex_filter},
                    {"category_id": regex_filter},
                    {"supplier_id": regex_filter},
                ]
            },
            {"_id": 0},
        )
    )


def fetch_products_below_reorder_threshold() -> list[dict]:
    try:
        all_products = fetch_all_products()
        return [
            product
            for product in all_products
            if int(product.get("current_stock", 0))
            < int(product.get("reorder_point", 0))
        ]
    except Exception as filter_error:
        print(
            f"[ProductService] fetch_products_below_reorder_threshold error: {filter_error}"
        )
        return []


def fetch_all_category_names() -> list[str]:
    try:
        categories = list(_get_categories_collection().find({}, {"name": 1, "_id": 0}))
        return [category["name"] for category in categories if "name" in category]
    except Exception as category_error:
        print(f"[ProductService] fetch_all_category_names error: {category_error}")
        return []


def fetch_all_supplier_names() -> list[str]:
    try:
        suppliers = list(_get_suppliers_collection().find({}, {"name": 1, "_id": 0}))
        return [supplier["name"] for supplier in suppliers if "name" in supplier]
    except Exception as supplier_error:
        print(f"[ProductService] fetch_all_supplier_names error: {supplier_error}")
        return []


def insert_new_product(product_data_dict: dict) -> bool:
    try:
        _get_products_collection().insert_one(product_data_dict)
        return True
    except Exception as insert_error:
        print(f"[ProductService] insert_new_product error: {insert_error}")
        return False


def update_existing_product_by_id(
    product_id: str,
    updated_fields_dict: dict,
) -> bool:
    try:
        _get_products_collection().update_one(
            {"product_id": product_id},
            {"$set": updated_fields_dict},
        )
        return True
    except Exception as update_error:
        print(f"[ProductService] update_existing_product_by_id error: {update_error}")
        return False


def delete_product_by_id(product_id: str) -> bool:
    try:
        _get_products_collection().delete_one({"product_id": product_id})
        return True
    except Exception as delete_error:
        print(f"[ProductService] delete_product_by_id error: {delete_error}")
        return False


def decrement_product_stock_after_sale(
    product_id: str,
    quantity_sold: int,
) -> bool:
    try:
        from datetime import datetime

        product = _get_products_collection().find_one({"product_id": product_id})
        if not product:
            return False

        current_stock = int(product.get("current_stock", 0))
        new_stock_level = max(0, current_stock - quantity_sold)
        _get_products_collection().update_one(
            {"product_id": product_id},
            {
                "$set": {
                    "current_stock": new_stock_level,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return True
    except Exception as stock_error:
        print(
            f"[ProductService] decrement_product_stock_after_sale error: {stock_error}"
        )
        return False
