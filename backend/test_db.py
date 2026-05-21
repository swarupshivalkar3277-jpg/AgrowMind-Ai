import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo.errors import PyMongoError

from database.mongodb import check_database, db

load_dotenv(Path(__file__).resolve().parent / ".env")


async def test_connection():
    try:
        await check_database()
        collections = await db.list_collection_names()
        print("MongoDB connected successfully.")
        print("Database:", os.getenv("MONGO_DB_NAME", "agromind_ai"))
        print("Collections:", collections)
    except PyMongoError as exc:
        print("MongoDB connection failed.")
        print("Error:", str(exc))


if __name__ == "__main__":
    asyncio.run(test_connection())
