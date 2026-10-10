
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongodb import database
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadStatus,
)


def serialize_lead(lead: dict) -> dict:
    return {
        "id": str(lead["_id"]),
        "name": lead["name"],
        "email": lead.get("email"),
        "phone": lead.get("phone"),
        "company": lead.get("company"),
        "source": lead["source"],
        "priority": lead["priority"],
        "status": lead["status"],
        "assigned_to": (
            str(lead["assigned_to"])
            if lead.get("assigned_to")
            else None
        ),
        "created_by": str(lead["created_by"]),
        "notes": lead.get("notes"),
        "created_at": lead["created_at"],
        "updated_at": lead["updated_at"],
    }


async def create_lead(lead_data: LeadCreate, current_user: dict):
    now = datetime.now(timezone.utc)

    lead_document = {
        "name": lead_data.name,
        "email": str(lead_data.email) if lead_data.email else None,
        "phone": lead_data.phone,
        "company": lead_data.company,
        "source": lead_data.source.value,
        "priority": lead_data.priority.value,
        "status": LeadStatus.NEW.value,
        "assigned_to": None,
        "created_by": ObjectId(current_user["id"]),
        "notes": lead_data.notes,
        "converted": False,
        "created_at": now,
        "updated_at": now,
    }

    result = await database.leads.insert_one(lead_document)
    lead_document["_id"] = result.inserted_id

    return serialize_lead(lead_document)


async def get_lead_by_id(lead_id: str, current_user: dict):
    if not ObjectId.is_valid(lead_id):
        raise ValueError("Invalid lead ID")

    lead = await database.leads.find_one(
        {"_id": ObjectId(lead_id)}
    )

    if not lead:
        raise ValueError("Lead not found")

    if (
        current_user["role"] == "sales_executive"
        and lead.get("assigned_to") != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot access this lead")

    return serialize_lead(lead)


async def list_leads(
    current_user: dict,
    search: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    source: str | None = None,
    assigned_to: str | None = None,
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

    if assigned_to:
        if not ObjectId.is_valid(assigned_to):
            raise ValueError("Invalid assigned_to user ID")

        if current_user["role"] == "sales_executive":
            if assigned_to != current_user["id"]:
                raise PermissionError(
                    "You cannot view leads assigned to another user"
                )
        else:
            filters["assigned_to"] = ObjectId(assigned_to)

    if search:
        filters["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
        ]

    if status:
        filters["status"] = status

    if priority:
        filters["priority"] = priority

    if source:
        filters["source"] = source

    total = await database.leads.count_documents(filters)

    cursor = (
        database.leads.find(filters)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []
    async for lead in cursor:
        items.append(serialize_lead(lead))

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def update_lead(
    lead_id: str,
    lead_data: LeadUpdate,
    current_user: dict,
):
    if not ObjectId.is_valid(lead_id):
        raise ValueError("Invalid lead ID")

    lead_object_id = ObjectId(lead_id)
    lead = await database.leads.find_one({"_id": lead_object_id})

    if not lead:
        raise ValueError("Lead not found")

    if (
        current_user["role"] == "sales_executive"
        and lead.get("assigned_to") != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot update this lead")

    updates = lead_data.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] is not None:
        new_status = updates["status"].value

        if lead.get("converted", False):
            raise ValueError("A converted lead cannot be updated")

        updates["status"] = new_status

    for field in ("source", "priority"):
        if field in updates and updates[field] is not None:
            updates[field] = updates[field].value

    if not updates:
        raise ValueError("No fields provided for update")

    updates["updated_at"] = datetime.now(timezone.utc)

    await database.leads.update_one(
        {"_id": lead_object_id},
        {"$set": updates},
    )

    updated_lead = await database.leads.find_one(
        {"_id": lead_object_id}
    )

    return serialize_lead(updated_lead)
