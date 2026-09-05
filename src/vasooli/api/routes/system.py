import logging
import asyncio
import os
import sys
import subprocess
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from ..deps import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from .database import settings, get_conn

async def get_health():
    """Check if the database is reachable."""
    try:
        # Using the session dependency would be better, but for health check
        # we want to verify the raw connection pool is working.
        # We use a simple SELECT 1 query.
        from .deps import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@router.post("/run-test/{script_key}")
async def run_test_script(script_key: str):
    """
    Executes a predefined test script from the scripts/ directory.
    Only scripts in the ALLOWED_SCRIPTS whitelist can be executed.
    """
    if script_key not in ALLOWED_SCRIPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid script key. Allowed keys: {', '.join(ALLOWED_SCRIPTS.keys())}"
        )

    script_path = ALLOWED_SCRIPTS[script_key]

    try:
        logger.info(f"Executing test script: {script_path}")

        # Use asyncio.to_thread with subprocess.run to avoid Windows NotImplementedError
        # with asyncio.create_subprocess_exec. This is the most robust way on Windows.
        def execute_script():
            return subprocess.run(
                [sys.executable, "-u", script_path],
                capture_output=True,
                text=False,  # Capture raw bytes to avoid encoding issues during read
                check=False,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )

        result = await asyncio.to_thread(execute_script)

        # Decode bytes manually using utf-8 to prevent Windows charmap errors
        stdout = result.stdout.decode("utf-8", errors="replace").strip() if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="replace").strip() if result.stderr else ""

        return {
            "script": script_key,
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "status": "success" if result.returncode == 0 else "failed"
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Failed to run script {script_path}:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Internal server error executing script: {str(e)}")
