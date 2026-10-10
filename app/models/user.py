from datetime import datetime, timezone

from app.schemas.user import UserRole


def build_user_document(
    name: str,
    email: str,
    password_hash: str,
    role: UserRole,
) -> dict:
    now = datetime.now(timezone.utc)

    return {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "role": role.value,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }