import bcrypt


def hash_plaintext_password(plaintext_password: str) -> str:
    password_bytes = plaintext_password.encode("utf-8")
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")


def verify_plaintext_password_against_hash(
    plaintext_password: str,
    stored_password_hash: str,
) -> bool:
    password_bytes = plaintext_password.encode("utf-8")
    stored_hash_bytes = stored_password_hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, stored_hash_bytes)


def is_password_hash_legacy_sha256(stored_password_hash: str) -> bool:
    return len(stored_password_hash) == 64 and not stored_password_hash.startswith(
        "$2b$"
    )


def migrate_sha256_hash_to_bcrypt(
    plaintext_password: str,
    legacy_sha256_hash: str,
) -> str | None:
    import hashlib

    computed_legacy_hash = hashlib.sha256(plaintext_password.encode()).hexdigest()
    if computed_legacy_hash == legacy_sha256_hash:
        return hash_plaintext_password(plaintext_password)
    return None
