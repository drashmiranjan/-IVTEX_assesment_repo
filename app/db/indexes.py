
from pymongo import ASCENDING, DESCENDING

from app.db.mongodb import database


async def create_indexes():
    # Users
    await database.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="users_email_unique",
    )
    await database.users.create_index(
        [("role", ASCENDING), ("is_active", ASCENDING)],
        name="users_role_active",
    )

    # Leads
    await database.leads.create_index(
        [("status", ASCENDING)],
        name="leads_status",
    )
    await database.leads.create_index(
        [("source", ASCENDING)],
        name="leads_source",
    )
    await database.leads.create_index(
        [("assigned_to", ASCENDING), ("created_at", DESCENDING)],
        name="leads_assignee_created",
    )

    # Customers
    await database.customers.create_index(
        [("email", ASCENDING)],
        name="customers_email",
    )
    await database.customers.create_index(
        [("assigned_to", ASCENDING), ("created_at", DESCENDING)],
        name="customers_assignee_created",
    )

    # Deals
    await database.deals.create_index(
        [("stage", ASCENDING)],
        name="deals_stage",
    )
    await database.deals.create_index(
        [("assigned_to", ASCENDING), ("created_at", DESCENDING)],
        name="deals_assignee_created",
    )
    await database.deals.create_index(
        [("customer_id", ASCENDING)],
        name="deals_customer",
    )

    # Activities
    await database.activities.create_index(
        [("assigned_to", ASCENDING), ("due_date", ASCENDING)],
        name="activities_assignee_due",
    )
    await database.activities.create_index(
        [("status", ASCENDING), ("due_date", ASCENDING)],
        name="activities_status_due",
    )

    # Audit timeline
    await database.audit_logs.create_index(
        [
            ("entity_type", ASCENDING),
            ("entity_id", ASCENDING),
            ("created_at", DESCENDING),
        ],
        name="audit_entity_timeline",
    )
