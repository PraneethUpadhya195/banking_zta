import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared')))
from database import AsyncSessionLocal
from models import User

async def seed_staff():
    async with AsyncSessionLocal() as db:
        # 1. Create the Admin
        admin_user = User(
            username="admin",
            hashed_password="keycloak_managed",
            role="admin",
            is_blocked=False
        )
        db.add(admin_user)

        # 2. Create the Manager
        manager_user = User(
            username="manager",
            hashed_password="keycloak_managed",
            role="manager",
            is_blocked=False
        )
        db.add(manager_user)

        await db.commit()
        print("Successfully created Admin and Manager in the database!")

if __name__ == "__main__":
    asyncio.run(seed_staff())