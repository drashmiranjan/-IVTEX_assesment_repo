import certifi
from pymongo import AsyncMongoClient

from app.core.config import settings


client = AsyncMongoClient(
    settings.mongodb_url,
    tlsCAFile=certifi.where(),
)

database = client[settings.mongodb_database]