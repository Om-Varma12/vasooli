import asyncio
from pathlib import Path
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    # Order matters: base tables first, then additions
    migration_files = [
        "migrations/001_init_recovery_tracking.sql",
        "migrations/002_add_raw_payload.sql",
        "migrations/003_add_phone_number.sql",
        "migrations/004_add_sequencer_fields.sql",
    ]

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        for file_path in migration_files:
            print(f"Executing {file_path}...")
            sql = Path(file_path).read_text()
            await conn.execute(sql)
            print(f"Successfully applied {file_path}")
        print("\n✅ All migrations applied successfully.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        await conn.close()

asyncio.run(main())