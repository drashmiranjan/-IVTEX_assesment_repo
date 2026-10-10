
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongodb import database
from app.schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityStatus,
    RelatedEntityType,
)


RELATED_COLLECTIONS = {
    RelatedEntityType.LEAD.value: "leads",
    RelatedEntityType.CUSTOMER.value: "customers",
    RelatedEntityType.DEAL.value: "deals",
}


def serialize_activity(activity: dict) -> dict:
    now = datetime.now(timezone.utc)
    due_date = activity["due_date"]

    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)

    is_overdue = (
        activity["status"] == ActivityStatus.PENDING.value
        and due_date < now
    )

    return {
        "id": str(activity["_id"]),
        "title": activity["title"],
        "description": activity.get("description"),
        "activity_type": activity["activity_type"],
        "status": activity["status"],
        "due_date": activity["due_date"],
        "related_type": activity["related_type"],
        "related_id": str(activity["related_id"]),
        "assigned_to": str(activity["assigned_to"]),
        "created_by": str(activity["created_by"]),
        "completed_at": activity.get("completed_at"),
        "is_overdue": is_overdue,
        "created_at": activity["created_at"],
        "updated_at": activity["updated_at"],
    }


async def create_activity(
    activity_data: ActivityCreate,
    current_user: dict,
):
    if not ObjectId.is_valid(activity_data.related_id):
        raise ValueError("Invalid related entity ID")

    related_type = activity_data.related_type.value
    collection_name = RELATED_COLLECTIONS[related_type]
    related_id = ObjectId(activity_data.related_id)

    related_entity = await database[collection_name].find_one(
        {"_id": related_id}
    )

    if not related_entity:
        raise ValueError(f"{related_type.capitalize()} not found")

    user_id = ObjectId(current_user["id"])
    assigned_to = user_id

    if activity_data.assigned_to:
        if not ObjectId.is_valid(activity_data.assigned_to):
            raise ValueError("Invalid assigned_to user ID")

        assigned_user_id = ObjectId(activity_data.assigned_to)
        assigned_user = await database.users.find_one(
            {"_id": assigned_user_id, "is_active": True}
        )

        if not assigned_user:
            raise ValueError("Assigned user not found or inactive")

        if current_user["role"] == "sales_executive":
            if assigned_user_id != user_id:
                raise PermissionError(
                    "Sales executives cannot assign activities to other users"
                )

        assigned_to = assigned_user_id

    if current_user["role"] == "sales_executive":
        owner = related_entity.get("assigned_to")

        if owner != user_id:
            raise PermissionError(
                "You cannot create an activity for this record"
            )

    now = datetime.now(timezone.utc)

    activity = {
        "title": activity_data.title,
        "description": activity_data.description,
        "activity_type": activity_data.activity_type.value,
        "status": ActivityStatus.PENDING.value,
        "due_date": activity_data.due_date,
        "related_type": related_type,
        "related_id": related_id,
        "assigned_to": assigned_to,
        "created_by": user_id,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await database.activities.insert_one(activity)
    activity["_id"] = result.inserted_id

    return serialize_activity(activity)


async def list_activities(
    current_user: dict,
    status: str | None = None,
    activity_type: str | None = None,
    related_type: str | None = None,
    related_id: str | None = None,
    assigned_to: str | None = None,
    overdue_only: bool = False,
    page: int = 1,
    page_size: int = 10,
):
    if page < 1:
        raise ValueError("page must be at least 1")

    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")

    filters = {}

    if current_user["role"] == "sales_executive":
        filters["assigned_to"] = ObjectId(current_user["id"])
    elif assigned_to:
        if not ObjectId.is_valid(assigned_to):
            raise ValueError("Invalid assigned_to user ID")
        filters["assigned_to"] = ObjectId(assigned_to)

    if status:
        valid_statuses = {item.value for item in ActivityStatus}
        if status not in valid_statuses:
            raise ValueError("Invalid activity status")
        filters["status"] = status

    if activity_type:
        valid_types = {"call", "email", "meeting", "task", "follow_up"}
        if activity_type not in valid_types:
            raise ValueError("Invalid activity type")
        filters["activity_type"] = activity_type

    if related_type:
        if related_type not in RELATED_COLLECTIONS:
            raise ValueError("Invalid related entity type")
        filters["related_type"] = related_type

    if related_id:
        if not ObjectId.is_valid(related_id):
            raise ValueError("Invalid related entity ID")
        filters["related_id"] = ObjectId(related_id)

    if overdue_only:
        filters["status"] = ActivityStatus.PENDING.value
        filters["due_date"] = {"$lt": datetime.now(timezone.utc)}

    total = await database.activities.count_documents(filters)

    cursor = (
        database.activities.find(filters)
        .sort("due_date", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []

    async for activity in cursor:
        items.append(serialize_activity(activity))

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def get_activity_by_id(activity_id: str, current_user: dict):
    if not ObjectId.is_valid(activity_id):
        raise ValueError("Invalid activity ID")

    activity = await database.activities.find_one(
        {"_id": ObjectId(activity_id)}
    )

    if not activity:
        raise ValueError("Activity not found")

    if (
        current_user["role"] == "sales_executive"
        and activity["assigned_to"] != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot access this activity")

    return serialize_activity(activity)


async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    current_user: dict,
):
    if not ObjectId.is_valid(activity_id):
        raise ValueError("Invalid activity ID")

    activity_object_id = ObjectId(activity_id)
    activity = await database.activities.find_one(
        {"_id": activity_object_id}
    )

    if not activity:
        raise ValueError("Activity not found")

    if (
        current_user["role"] == "sales_executive"
        and activity["assigned_to"] != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot update this activity")

    updates = activity_data.model_dump(exclude_unset=True)

    if not updates:
        raise ValueError("No fields provided for update")

    new_status = updates.get("status", activity["status"])

    if isinstance(new_status, ActivityStatus):
        new_status = new_status.value

    if (
        activity["status"] == ActivityStatus.COMPLETED.value
        and new_status != ActivityStatus.COMPLETED.value
    ):
        raise ValueError("Completed activities cannot be reopened")

    if new_status == ActivityStatus.COMPLETED.value:
        updates["completed_at"] = datetime.now(timezone.utc)
    elif "status" in updates:
        updates["completed_at"] = None

    if "assigned_to" in updates:
        assigned_to = updates["assigned_to"]

        if not ObjectId.is_valid(assigned_to):
            raise ValueError("Invalid assigned_to user ID")

        assigned_user_id = ObjectId(assigned_to)
        assigned_user = await database.users.find_one(
            {"_id": assigned_user_id, "is_active": True}
        )

        if not assigned_user:
            raise ValueError("Assigned user not found or inactive")

        if current_user["role"] == "sales_executive":
            if assigned_user_id != ObjectId(current_user["id"]):
                raise PermissionError(
                    "Sales executives cannot assign activities to other users"
                )

        updates["assigned_to"] = assigned_user_id

    updates["updated_at"] = datetime.now(timezone.utc)

    for key, value in list(updates.items()):
        if hasattr(value, "value"):
            updates[key] = value.value

    await database.activities.update_one(
        {"_id": activity_object_id},
        {"$set": updates},
    )

    updated_activity = await database.activities.find_one(
        {"_id": activity_object_id}
    )

    return serialize_activity(updated_activity)


async def delete_activity(activity_id: str, current_user: dict):
    if current_user["role"] != "admin":
        raise PermissionError("Only admins can delete activities")

    if not ObjectId.is_valid(activity_id):
        raise ValueError("Invalid activity ID")

    result = await database.activities.delete_one(
        {"_id": ObjectId(activity_id)}
    )

    if result.deleted_count == 0:
        raise ValueError("Activity not found")

    return {"message": "Activity deleted successfully"}
