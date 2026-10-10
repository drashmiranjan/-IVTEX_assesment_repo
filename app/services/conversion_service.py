from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.mongodb import database
from app.schemas.deal import DealStage


async def convert_lead(
    lead_id: str,
    deal_title: str,
    deal_value: float,
    deal_probability: int,
    current_user: dict,
):
    # 1. Validate input
    if not ObjectId.is_valid(lead_id):
        raise ValueError("Invalid lead ID")

    if not deal_title or len(deal_title.strip()) < 2:
        raise ValueError("Deal title must contain at least 2 characters")

    if deal_value <= 0:
        raise ValueError("Deal value must be greater than zero")

    if not 0 <= deal_probability <= 100:
        raise ValueError("Deal probability must be between 0 and 100")

    if not ObjectId.is_valid(current_user.get("id", "")):
        raise ValueError("Invalid current user ID")

    lead_object_id = ObjectId(lead_id)
    user_object_id = ObjectId(current_user["id"])

    # 2. Atomically claim the lead to prevent duplicate conversions
    lead = await database.leads.find_one_and_update(
        {
            "_id": lead_object_id,
            "converted": {"$ne": True},
            "conversion_in_progress": {"$ne": True},
            "status": {"$ne": "converted"},
        },
        {
            "$set": {
                "conversion_in_progress": True,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.BEFORE,
    )

    if not lead:
        existing = await database.leads.find_one(
            {"_id": lead_object_id}
        )

        if not existing:
            raise ValueError("Lead not found")

        raise ValueError(
            "Lead has already been converted or is being converted"
        )

    customer_id = None
    deal_id = None

    try:
        # 3. Verify record ownership before creating related records
        if (
            current_user["role"] == "sales_executive"
            and lead.get("assigned_to") != user_object_id
        ):
            raise PermissionError("You cannot convert this lead")

        now = datetime.now(timezone.utc)
        owner_id = lead.get("assigned_to") or user_object_id

        # 4. Create customer linked to the original lead
        customer = {
            "name": lead["name"],
            "email": lead.get("email"),
            "phone": lead.get("phone"),
            "company": lead.get("company"),
            "address": None,
            "original_lead_id": lead_object_id,
            "assigned_to": owner_id,
            "created_by": user_object_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

        customer_result = await database.customers.insert_one(
            customer
        )
        customer_id = customer_result.inserted_id

        # 5. Create deal linked to the new customer
        deal = {
            "title": deal_title.strip(),
            "customer_id": customer_id,
            "assigned_to": owner_id,
            "created_by": user_object_id,
            "value": deal_value,
            "probability": deal_probability,
            "expected_revenue": round(
                deal_value * deal_probability / 100, 2
            ),
            "stage": DealStage.QUALIFICATION.value,
            "expected_close_date": None,
            "actual_close_date": None,
            "lost_reason": None,
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        deal_result = await database.deals.insert_one(deal)
        deal_id = deal_result.inserted_id

        # 6. Finalize conversion only if this operation still owns the claim
        update_result = await database.leads.update_one(
            {
                "_id": lead_object_id,
                "conversion_in_progress": True,
                "converted": {"$ne": True},
            },
            {
                "$set": {
                    "converted": True,
                    "status": "converted",
                    "converted_customer_id": customer_id,
                    "converted_deal_id": deal_id,
                    "updated_at": now,
                },
                "$unset": {
                    "conversion_in_progress": "",
                },
            },
        )

        if update_result.modified_count != 1:
            raise RuntimeError("Could not finalize lead conversion")

        return {
            "message": "Lead converted successfully",
            "lead_id": str(lead_object_id),
            "customer_id": str(customer_id),
            "deal_id": str(deal_id),
        }

    except Exception:
        # 7. Best-effort cleanup if conversion fails
        if deal_id is not None:
            await database.deals.delete_one(
                {"_id": deal_id}
            )

        if customer_id is not None:
            await database.customers.delete_one(
                {"_id": customer_id}
            )

        await database.leads.update_one(
            {
                "_id": lead_object_id,
                "conversion_in_progress": True,
                "converted": {"$ne": True},
            },
            {
                "$set": {
                    "converted": False,
                },
                "$unset": {
                    "conversion_in_progress": "",
                },
            },
        )

        raise