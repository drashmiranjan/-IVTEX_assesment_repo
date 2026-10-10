
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongodb import database
from app.schemas.deal import DealCreate, DealUpdate, DealStage


CLOSED_STAGES = {DealStage.WON.value, DealStage.LOST.value}


def serialize_deal(deal: dict) -> dict:
    return {
        "id": str(deal["_id"]),
        "title": deal["title"],
        "customer_id": str(deal["customer_id"]),
        "assigned_to": str(deal["assigned_to"]),
        "created_by": str(deal["created_by"]),
        "value": deal["value"],
        "probability": deal["probability"],
        "expected_revenue": deal["expected_revenue"],
        "stage": deal["stage"],
        "expected_close_date": deal.get("expected_close_date"),
        "actual_close_date": deal.get("actual_close_date"),
        "lost_reason": deal.get("lost_reason"),
        "notes": deal.get("notes"),
        "created_at": deal["created_at"],
        "updated_at": deal["updated_at"],
    }


async def create_deal(deal_data: DealCreate, current_user: dict):
    if not ObjectId.is_valid(deal_data.customer_id):
        raise ValueError("Invalid customer ID")

    customer_id = ObjectId(deal_data.customer_id)
    customer = await database.customers.find_one({"_id": customer_id})

    if not customer:
        raise ValueError("Customer not found")

    user_id = ObjectId(current_user["id"])

    if (
        current_user["role"] == "sales_executive"
        and customer.get("assigned_to") != user_id
    ):
        raise PermissionError("You cannot create a deal for this customer")

    stage = deal_data.stage.value

    if stage == DealStage.LOST.value and not deal_data.lost_reason:
        raise ValueError("A reason is required when a deal is lost")

    if stage in CLOSED_STAGES:
        raise ValueError("Create the deal as open, then close it through an update")

    now = datetime.now(timezone.utc)

    deal = {
        "title": deal_data.title,
        "customer_id": customer_id,
        "assigned_to": customer.get("assigned_to", user_id),
        "created_by": user_id,
        "value": deal_data.value,
        "probability": deal_data.probability,
        "expected_revenue": round(
            deal_data.value * deal_data.probability / 100, 2
        ),
        "stage": stage,
        "expected_close_date": deal_data.expected_close_date,
        "actual_close_date": None,
        "lost_reason": None,
        "notes": deal_data.notes,
        "created_at": now,
        "updated_at": now,
    }

    result = await database.deals.insert_one(deal)
    deal["_id"] = result.inserted_id

    return serialize_deal(deal)


async def get_deal_by_id(deal_id: str, current_user: dict):
    if not ObjectId.is_valid(deal_id):
        raise ValueError("Invalid deal ID")

    deal = await database.deals.find_one({"_id": ObjectId(deal_id)})

    if not deal:
        raise ValueError("Deal not found")

    if (
        current_user["role"] == "sales_executive"
        and deal.get("assigned_to") != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot access this deal")

    return serialize_deal(deal)


async def list_deals(
    current_user: dict,
    search: str | None = None,
    stage: str | None = None,
    assigned_to: str | None = None,
    customer_id: str | None = None,
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

        requested_user_id = ObjectId(assigned_to)

        if (
            current_user["role"] == "sales_executive"
            and requested_user_id != ObjectId(current_user["id"])
        ):
            raise PermissionError("You cannot view another user's deals")

        filters["assigned_to"] = requested_user_id

    if customer_id:
        if not ObjectId.is_valid(customer_id):
            raise ValueError("Invalid customer ID")
        filters["customer_id"] = ObjectId(customer_id)

    if stage:
        valid_stages = {item.value for item in DealStage}
        if stage not in valid_stages:
            raise ValueError("Invalid deal stage")
        filters["stage"] = stage

    if search:
        filters["title"] = {"$regex": search, "$options": "i"}

    total = await database.deals.count_documents(filters)

    cursor = (
        database.deals.find(filters)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []

    async for deal in cursor:
        items.append(serialize_deal(deal))

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def update_deal(
    deal_id: str,
    deal_data: DealUpdate,
    current_user: dict,
):
    if not ObjectId.is_valid(deal_id):
        raise ValueError("Invalid deal ID")

    deal_object_id = ObjectId(deal_id)
    deal = await database.deals.find_one({"_id": deal_object_id})

    if not deal:
        raise ValueError("Deal not found")

    if (
        current_user["role"] == "sales_executive"
        and deal.get("assigned_to") != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot update this deal")

    if deal["stage"] in CLOSED_STAGES:
        raise ValueError("Closed deals cannot be modified")

    updates = deal_data.model_dump(exclude_unset=True)

    if not updates:
        raise ValueError("No fields provided for update")

    new_stage = updates.get("stage", deal["stage"])
    if isinstance(new_stage, DealStage):
        new_stage = new_stage.value
    updates["stage"] = new_stage

    lost_reason = updates.get("lost_reason", deal.get("lost_reason"))

    if new_stage == DealStage.LOST.value and not lost_reason:
        raise ValueError("A reason is required when a deal is lost")

    value = updates.get("value", deal["value"])
    probability = updates.get("probability", deal["probability"])

    updates["expected_revenue"] = round(value * probability / 100, 2)

    now = datetime.now(timezone.utc)
    updates["updated_at"] = now

    if new_stage in CLOSED_STAGES:
        updates["actual_close_date"] = now

    if new_stage == DealStage.WON.value:
        updates["probability"] = 100
        updates["expected_revenue"] = round(value, 2)
        updates["lost_reason"] = None

    if new_stage == DealStage.LOST.value:
        updates["probability"] = 0
        updates["expected_revenue"] = 0

    if new_stage not in CLOSED_STAGES:
        updates.pop("actual_close_date", None)

    for key, value_to_store in list(updates.items()):
        if isinstance(value_to_store, DealStage):
            updates[key] = value_to_store.value

    await database.deals.update_one(
        {"_id": deal_object_id},
        {"$set": updates},
    )

    updated_deal = await database.deals.find_one({"_id": deal_object_id})
    return serialize_deal(updated_deal)


async def delete_deal(deal_id: str, current_user: dict):
    if current_user["role"] != "admin":
        raise PermissionError("Only admins can delete deals")

    if not ObjectId.is_valid(deal_id):
        raise ValueError("Invalid deal ID")

    result = await database.deals.delete_one({"_id": ObjectId(deal_id)})

    if result.deleted_count == 0:
        raise ValueError("Deal not found")

    return {"message": "Deal deleted successfully"}
