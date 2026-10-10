
from bson import ObjectId

from app.db.mongodb import database


CLOSED_STAGES = {"won", "lost"}


async def get_sales_analytics(current_user: dict):
    user_role = current_user["role"]
    user_id = ObjectId(current_user["id"])

    # Sales executives see only their own deals.
    deal_filter = {}
    if user_role == "sales_executive":
        deal_filter["assigned_to"] = user_id

    # Overall deal counts and pipeline value.
    total_deals = await database.deals.count_documents(deal_filter)

    pipeline_filter = {
        **deal_filter,
        "stage": {"$nin": list(CLOSED_STAGES)},
    }

    pipeline_result = await database.deals.aggregate([
        {"$match": pipeline_filter},
        {
            "$group": {
                "_id": None,
                "pipeline_value": {"$sum": "$value"},
                "expected_revenue": {"$sum": "$expected_revenue"},
            }
        },
    ]).to_list(length=1)

    pipeline = pipeline_result[0] if pipeline_result else {}

    # Deal counts and values by stage.
    stage_results = await database.deals.aggregate([
        {"$match": deal_filter},
        {
            "$group": {
                "_id": "$stage",
                "count": {"$sum": 1},
                "value": {"$sum": "$value"},
                "expected_revenue": {"$sum": "$expected_revenue"},
            }
        },
        {"$sort": {"_id": 1}},
    ]).to_list(length=None)

    stages = [
        {
            "stage": item["_id"],
            "count": item["count"],
            "value": item["value"],
            "expected_revenue": item["expected_revenue"],
        }
        for item in stage_results
    ]

    result = {
        "total_deals": total_deals,
        "open_pipeline_value": pipeline.get("pipeline_value", 0),
        "open_expected_revenue": pipeline.get("expected_revenue", 0),
        "deals_by_stage": stages,
    }

    # Admins and sales managers can see team performance.
    if user_role in {"admin", "sales_manager"}:
        team_results = await database.deals.aggregate([
            {
                "$group": {
                    "_id": "$assigned_to",
                    "total_deals": {"$sum": 1},
                    "total_value": {"$sum": "$value"},
                    "won_deals": {
                        "$sum": {
                            "$cond": [{"$eq": ["$stage", "won"]}, 1, 0]
                        }
                    },
                }
            },
            {"$sort": {"total_value": -1}},
        ]).to_list(length=None)

        team = []

        for item in team_results:
            user = await database.users.find_one(
                {"_id": item["_id"]},
                {"name": 1, "email": 1},
            )

            team.append({
                "user_id": str(item["_id"]),
                "name": user.get("name") if user else None,
                "email": user.get("email") if user else None,
                "total_deals": item["total_deals"],
                "total_value": item["total_value"],
                "won_deals": item["won_deals"],
            })

        result["team_performance"] = team

    return result
