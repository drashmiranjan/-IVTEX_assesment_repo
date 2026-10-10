from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.mongodb import client
from app.db.indexes import create_indexes
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.leads import router as leads_router
from app.api.routes.customers import router as customers_router
from app.api.routes.deals import router as deals_router
from app.api.routes.activities import router as activities_router
from app.api.routes.timeline import router as timeline_router
from app.api.routes.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await client.admin.command("ping")
    print("MongoDB connection successful")

    await create_indexes()
    print("MongoDB indexes created")

    yield

    await client.close()
    print("MongoDB connection closed")


app = FastAPI(
    title="CRM Sales Management API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(leads_router)
app.include_router(customers_router)
app.include_router(deals_router)
app.include_router(activities_router)
app.include_router(timeline_router)
app.include_router(analytics_router)


@app.get("/health")
async def health_check():
    return {
        "success": True,
        "message": "CRM Sales Management API is running",
    }