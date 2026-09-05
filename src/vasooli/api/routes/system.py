import logging
import asyncio
import os
import sys
import subprocess
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
