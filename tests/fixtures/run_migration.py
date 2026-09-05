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
            try:
                print(f"Executing {file_path}...")
                sql = Path(file_path).read_text()
                # Use a separate transaction for each file
                async with conn.transaction():
                    await conn.execute(sql)
                print(f"Successfully applied {file_path}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"Notice: Column already exists in {file_path}, skipping.")
                else:
                    print(f"Error applying {file_path}: {e}")
        print("\nAll migrations processed.")
    except Exception as e:
        print(f"Global migration failure: {e}")
    finally:
        await conn.close()

asyncio.run(main())