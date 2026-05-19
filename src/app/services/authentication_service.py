from __future__ import annotations

from src.database.mongo_connection import get_inventory_database
from src.utilities.security import (
    hash_plaintext_password,
    verify_plaintext_password_against_hash,
    is_password_hash_legacy_sha256,
    migrate_sha256_hash_to_bcrypt,
)


def _get_users_collection():
    return get_inventory_database()["users"]


def authenticate_user_with_credentials(
    email_address: str,
    plaintext_password: str,
) -> tuple[dict | None, str | None]:
    users_collection = _get_users_collection()
    normalised_email = email_address.strip().lower()
    user_document = users_collection.find_one({"email": normalised_email})

    if user_document is None:
        return None, "No account found with that email address."

    stored_password_hash: str = user_document.get("password", "")

    if is_password_hash_legacy_sha256(stored_password_hash):
        upgraded_bcrypt_hash = migrate_sha256_hash_to_bcrypt(
            plaintext_password, stored_password_hash
        )
        if upgraded_bcrypt_hash is None:
            return None, "Incorrect password."
        users_collection.update_one(
            {"_id": user_document["_id"]},
            {"$set": {"password": upgraded_bcrypt_hash}},
        )
        user_document["password"] = upgraded_bcrypt_hash
    else:
        password_is_correct = verify_plaintext_password_against_hash(
            plaintext_password, stored_password_hash
        )
        if not password_is_correct:
            return None, "Incorrect password."

    sanitised_user = {
        "name": user_document.get("full_name", "User"),
        "email": user_document.get("email", ""),
        "role": user_document.get("role", "Employee"),
        "contact": user_document.get("contact", ""),
        "address": user_document.get("address", ""),
    }
    return sanitised_user, None


def register_new_user_account(
    full_name: str,
    email_address: str,
    plaintext_password: str,
    role: str = "Employee",
) -> tuple[bool, str | None]:
    users_collection = _get_users_collection()
    normalised_email = email_address.strip().lower()

    existing_user = users_collection.find_one({"email": normalised_email})
    if existing_user is not None:
        return False, "An account with this email already exists."

    if len(plaintext_password) < 8:
        return False, "Password must be at least 8 characters long."

    hashed_password = hash_plaintext_password(plaintext_password)
    users_collection.insert_one(
        {
            "full_name": full_name.strip(),
            "email": normalised_email,
            "password": hashed_password,
            "role": role,
        }
    )
    return True, None


def seed_default_admin_user_if_absent() -> None:
    users_collection = _get_users_collection()
    if users_collection.count_documents({}) == 0:
        hashed_password = hash_plaintext_password("admin123")
        users_collection.insert_one(
            {
                "full_name": "Admin User",
                "email": "admin@company.com",
                "password": hashed_password,
                "role": "Admin",
            }
        )
        print("✅ Default admin account seeded: admin@company.com / admin123")
