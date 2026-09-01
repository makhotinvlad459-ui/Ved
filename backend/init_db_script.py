# backend/init_db_script.py
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.init_db import init_db


async def main():
    await init_db()


if __name__ == "__main__":
    asyncio.run(main())