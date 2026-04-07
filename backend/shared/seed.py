import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared')))
from database import AsyncSessionLocal
from models import User, Account

async def seed_customer2():
    async with AsyncSessionLocal() as db:
        # 1. Create the User
        new_user = User(
            username="customer2",
            hashed_password="keycloak_managed",
            role="customer",
            is_blocked=False
        )
        db.add(new_user)
        await db.flush() # Flushes to DB to get the new_user.id generated

        # 2. Create the Account
        new_account = Account(
            user_id=new_user.id,
            account_number="ACC9876543210",
            balance=5000.00
        )
        db.add(new_account)
        await db.commit()
        print("Successfully created customer2 and added ₹5,000 to their account!")

if __name__ == "__main__":
    asyncio.run(seed_customer2())