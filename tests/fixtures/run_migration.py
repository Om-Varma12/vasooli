import asyncio
from pathlib import Path
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()  

DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    sql = Path("migrations/002_add_raw_payload.sql").read_text()

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        await conn.execute(sql)
        print("Migration executed successfully.")
    finally:
        await conn.close()

asyncio.run(main())