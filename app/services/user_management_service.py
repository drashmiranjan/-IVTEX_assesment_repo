
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from app.db.mongodb import database


SORT_FIELDS = {
    "name": "name",
    "email": "email",
    "role": "role",
    "created_at": "created_at",
    "updated_at": "updated_at",
}


def serialize_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


async def list_users(
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    if page < 1:
        raise ValueError("page must be at least 1")

    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")

    if sort_by not in SORT_FIELDS:
        raise ValueError("Invalid sort_by field")

    if sort_order not in {"asc", "desc"}:
        raise ValueError("sort_order must be 'asc' or 'desc'")

    filters = {}

    if search:
        filters["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    if role:
        filters["role"] = role

    if is_active is not None:
        filters["is_active"] = is_active

    direction = ASCENDING if sort_order == "asc" else DESCENDING
    skip = (page - 1) * page_size

    total = await database.users.count_documents(filters)

    cursor = (
        database.users.find(filters)
        .sort(SORT_FIELDS[sort_by], direction)
        .skip(skip)
        .limit(page_size)
    )

    items = []

    async for user in cursor:
        items.append(serialize_user(user))

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def get_user_by_id(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    user = await database.users.find_one(
        {"_id": ObjectId(user_id)}
    )

    if not user:
        raise ValueError("User not found")

    return serialize_user(user)


async def update_user(user_id: str, updates: dict):
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    allowed_fields = {"name", "email", "role", "is_active"}
    clean_updates = {
        key: value
        for key, value in updates.items()
        if key in allowed_fields
    }

    if not clean_updates:
        raise ValueError("No valid fields provided for update")

    if "name" in clean_updates:
        name = clean_updates["name"]
        if not isinstance(name, str) or not 2 <= len(name.strip()) <= 100:
            raise ValueError("Name must contain 2 to 100 characters")
        clean_updates["name"] = name.strip()

    if "email" in clean_updates:
        email = clean_updates["email"]
        if not isinstance(email, str) or "@" not in email:
            raise ValueError("Invalid email address")

        clean_updates["email"] = email.strip().lower()

        existing = await database.users.find_one({
            "email": clean_updates["email"],
            "_id": {"$ne": ObjectId(user_id)},
        })

        if existing:
            raise ValueError("Email already registered")

    if "role" in clean_updates:
        allowed_roles = {"admin", "sales_manager", "sales_executive"}
        if clean_updates["role"] not in allowed_roles:
            raise ValueError("Invalid user role")

    if "is_active" in clean_updates:
        if not isinstance(clean_updates["is_active"], bool):
            raise ValueError("is_active must be a boolean")

    clean_updates["updated_at"] = datetime.now(timezone.utc)

    result = await database.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": clean_updates},
    )

    if result.matched_count == 0:
        raise ValueError("User not found")

    return await get_user_by_id(user_id)


async def set_user_active_status(user_id: str, is_active: bool):
    if not isinstance(is_active, bool):
        raise ValueError("is_active must be a boolean")

    return await update_user(
        user_id,
        {"is_active": is_active},
    )


async def delete_user(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    result = await database.users.delete_one(
        {"_id": ObjectId(user_id)}
    )

    if result.deleted_count == 0:
        raise ValueError("User not found")

    return {"message": "User deleted successfully"}
