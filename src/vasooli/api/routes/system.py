import logging
import asyncio
import os
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from ..deps import AsyncSessionLocal

router = APIRouter(prefix="/system", tags=["System"])

# Security whitelist for test scripts
ALLOWED_SCRIPTS = {
    "gen_tests": "scripts/gen_tests.py",
    "generate_data": "scripts/generate_synthetic_data.py",
    "run_demo": "scripts/run_demo.py",
    "test_voice": "scripts/test_voice_send.py",
    "test_whatsapp": "scripts/test_whatsapp_send.py",
    "trigger_bouncer": "scripts/trigger_chronic_bouncer.py",
}

logger = logging.getLogger("vasooli.api.system")

@router.get("/health")
async def health_check():
    """Check if the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
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

    # Ensure script path is relative to project root (where the API is usually launched from)
    # If not launched from root, we might need absolute paths.
    # For now, assuming launched from the project root.

    try:
        logger.info(f"Executing test script: {script_path}")

        # Use python -u for unbuffered output so we can capture it better
        process = await asyncio.create_subprocess_exec(
            "python", "-u", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        return {
            "script": script_key,
            "exit_code": process.returncode,
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
            "status": "success" if process.returncode == 0 else "failed"
        }
    except Exception as e:
        logger.error(f"Failed to run script {script_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error executing script: {str(e)}")
