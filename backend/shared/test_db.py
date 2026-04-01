import asyncio
from database import engine

async def test():
    async with engine.connect() as conn:
        print("Connected to PostgreSQL successfully")

asyncio.run(test())