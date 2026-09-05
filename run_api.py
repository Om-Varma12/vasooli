import asyncio
import sys
import uvicorn
import multiprocessing

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    # Necessary for Windows multiprocessing/reload
    multiprocessing.freeze_support()
    uvicorn.run("vasooli.api.main:app", host="0.0.0.0", port=8001, reload=True)
