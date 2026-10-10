
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongodb import database
from app.schemas.customer import CustomerCreate, CustomerUpdate


def serialize_customer(customer: dict) -> dict:
    return {
        "id": str(customer["_id"]),
        "name": customer["name"],
        "email": customer.get("email"),
        "phone": customer.get("phone"),
        "company": customer.get("company"),
        "address": customer.get("address"),
        "original_lead_id": (
            str(customer["original_lead_id"])
            if customer.get("original_lead_id")
            else None
        ),
        "assigned_to": (
            str(customer["assigned_to"])
            if customer.get("assigned_to")
            else None
        ),
        "status": customer["status"],
        "created_at": customer["created_at"],
        "updated_at": customer["updated_at"],
    }


async def create_customer(
    customer_data: CustomerCreate,
    current_user: dict,
):
    now = datetime.now(timezone.utc)

    customer = {
        "name": customer_data.name,
        "email": str(customer_data.email) if customer_data.email else None,
        "phone": customer_data.phone,
        "company": customer_data.company,
        "address": customer_data.address,
        "original_lead_id": None,
        "assigned_to": ObjectId(current_user["id"]),
        "status": "active",
        "created_by": ObjectId(current_user["id"]),
        "created_at": now,
        "updated_at": now,
    }

    result = await database.customers.insert_one(customer)
    customer["_id"] = result.inserted_id

    return serialize_customer(customer)


async def list_customers(
    current_user: dict,
    search: str | None = None,
    status: str | None = None,
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
        filters["assigned_to"] = ObjectId(assigned_to)

    if search:
        filters["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
        ]

    if status:
        filters["status"] = status

    total = await database.customers.count_documents(filters)

    cursor = (
        database.customers.find(filters)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []
    async for customer in cursor:
        items.append(serialize_customer(customer))

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def get_customer_by_id(customer_id: str, current_user: dict):
    if not ObjectId.is_valid(customer_id):
        raise ValueError("Invalid customer ID")

    customer = await database.customers.find_one(
        {"_id": ObjectId(customer_id)}
    )

    if not customer:
        raise ValueError("Customer not found")

    if (
        current_user["role"] == "sales_executive"
        and customer.get("assigned_to") != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot access this customer")

    return serialize_customer(customer)


async def update_customer(
    customer_id: str,
    customer_data: CustomerUpdate,
    current_user: dict,
):
    if not ObjectId.is_valid(customer_id):
        raise ValueError("Invalid customer ID")

    customer_object_id = ObjectId(customer_id)
    customer = await database.customers.find_one(
        {"_id": customer_object_id}
    )

    if not customer:
        raise ValueError("Customer not found")

    if (
        current_user["role"] == "sales_executive"
        and customer.get("assigned_to") != ObjectId(current_user["id"])
    ):
        raise PermissionError("You cannot update this customer")

    updates = customer_data.model_dump(exclude_unset=True)

    if not updates:
        raise ValueError("No fields provided for update")

    for key, value in updates.items():
        if value is not None and key == "email":
            updates[key] = str(value).lower()

    updates["updated_at"] = datetime.now(timezone.utc)

    await database.customers.update_one(
        {"_id": customer_object_id},
        {"$set": updates},
    )

    updated = await database.customers.find_one(
        {"_id": customer_object_id}
    )

    return serialize_customer(updated)


async def delete_customer(customer_id: str, current_user: dict):
    if not ObjectId.is_valid(customer_id):
        raise ValueError("Invalid customer ID")

    customer_object_id = ObjectId(customer_id)
    customer = await database.customers.find_one(
        {"_id": customer_object_id}
    )

    if not customer:
        raise ValueError("Customer not found")

    if current_user["role"] == "sales_executive":
        if customer.get("assigned_to") != ObjectId(current_user["id"]):
            raise PermissionError("You cannot delete this customer")

    # Preserve customer/deal relationships: don't delete a customer
    # that is already referenced by a deal.
    related_deal = await database.deals.find_one(
        {"customer_id": customer_object_id}
    )

    if related_deal:
        raise ValueError("Cannot delete a customer with associated deals")

    await database.customers.delete_one({"_id": customer_object_id})

    return {"message": "Customer deleted successfully"}
