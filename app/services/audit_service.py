
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongodb import database


ALLOWED_ENTITY_TYPES = {"lead", "customer", "deal"}


async def log_audit_event(
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
):
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise ValueError("Invalid audit entity type")

    if not ObjectId.is_valid(actor_id):
        raise ValueError("Invalid audit actor ID")

    if not ObjectId.is_valid(entity_id):
        raise ValueError("Invalid audit entity ID")

    event = {
        "actor_id": ObjectId(actor_id),
        "action": action,
        "entity_type": entity_type,
        "entity_id": ObjectId(entity_id),
        "details": details or {},
        "created_at": datetime.now(timezone.utc),
    }

    result = await database.audit_logs.insert_one(event)

    return {
        "id": str(result.inserted_id),
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": event["details"],
        "created_at": event["created_at"],
    }


async def get_entity_timeline(
    entity_type: str,
    entity_id: str,
    current_user: dict,
    page: int = 1,
    page_size: int = 20,
):
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise ValueError("Invalid entity type")

    if not ObjectId.is_valid(entity_id):
        raise ValueError("Invalid entity ID")

    if page < 1:
        raise ValueError("page must be at least 1")

    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")

    entity_object_id = ObjectId(entity_id)

    collection_name = {
        "lead": "leads",
        "customer": "customers",
        "deal": "deals",
    }[entity_type]

    entity = await database[collection_name].find_one(
        {"_id": entity_object_id}
    )

    if not entity:
        raise ValueError(f"{entity_type.capitalize()} not found")

    if current_user["role"] == "sales_executive":
        if entity.get("assigned_to") != ObjectId(current_user["id"]):
            raise PermissionError("You cannot access this timeline")

    filters = {
        "entity_type": entity_type,
        "entity_id": entity_object_id,
    }

    total = await database.audit_logs.count_documents(filters)

    cursor = (
        database.audit_logs.find(filters)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []

    async for event in cursor:
        items.append({
            "id": str(event["_id"]),
            "actor_id": str(event["actor_id"]),
            "action": event["action"],
            "entity_type": event["entity_type"],
            "entity_id": str(event["entity_id"]),
            "details": event.get("details", {}),
            "created_at": event["created_at"],
        })

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }
