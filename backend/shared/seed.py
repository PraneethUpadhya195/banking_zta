import asyncio
import sys
import os
import uuid

sys.path.append(os.path.dirname(__file__))

from database import AsyncSessionLocal, engine, Base
from models import User, Account
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    async with AsyncSessionLocal() as db:
        users = [
            {"username": "customer1", "password": "pass123", "role": "customer"},
            {"username": "teller1",   "password": "pass123", "role": "teller"},
            {"username": "manager1",  "password": "pass123", "role": "manager"},
            {"username": "admin1",    "password": "pass123", "role": "admin"},
        ]

        balances = {
            "customer1": 52000.0,
            "teller1":   0.0,
            "manager1":  0.0,
            "admin1":    0.0,
        }

        for u in users:
            user = User(
                username=u["username"],
                hashed_password=pwd_context.hash(u["password"]),
                role=u["role"]
            )
            db.add(user)
            await db.flush()

            account = Account(
                user_id=user.id,
                account_number=f"ACC{str(uuid.uuid4().int)[:10]}",
                balance=balances[u["username"]]
            )
            db.add(account)

        await db.commit()
        print("Seeded users and accounts successfully")

asyncio.run(seed())