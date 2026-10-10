from app.db.mongodb import database
from app.models.user import build_user_document
from app.schemas.user import UserCreate, UserRole
from app.core.security import hash_password, create_access_token, verify_password


async def get_user_by_email(email: str):
    return await database.users.find_one(
        {"email": email}
    )


async def create_user(user_data: UserCreate):
    existing_user = await get_user_by_email(user_data.email)

    if existing_user:
        raise ValueError("Email already registered")

    password_hash = hash_password(user_data.password)

    user_document = build_user_document(
        name=user_data.name,
        email=user_data.email,
        password_hash=password_hash,
        role=UserRole.SALES_EXECUTIVE,
    )

    result = await database.users.insert_one(user_document)

    user_document["id"] = str(result.inserted_id)
    user_document.pop("_id", None)
    user_document.pop("password_hash", None)

    return user_document

async def login_user(email: str, password: str):
    user = await get_user_by_email(email)

    if not user:
        raise ValueError("Invalid email or password")

    if not user["is_active"]:
        raise ValueError("User account is inactive")

    if not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password")

    access_token = create_access_token(str(user["_id"]))

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }