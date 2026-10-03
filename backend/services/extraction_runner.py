"""Hard timeout via a killable subprocess; native parsers never block the API loop."""
import asyncio
import json
import sys
from pathlib import Path

WORKER = Path(__file__).resolve().parents[1] / "extraction_worker.py"
EXTRACTION_TIMEOUT = 45
# Bound concurrent parsing/OCR work per API process.
slots = asyncio.Semaphore(2)


async def run_extraction(content: bytes, extension: str):
    process = None
    try:
        async with asyncio.timeout(EXTRACTION_TIMEOUT):
            async with slots:
                process = await asyncio.create_subprocess_exec(sys.executable, str(WORKER), extension, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                output, _ = await process.communicate(content)
                if process.returncode != 0:
                    raise ValueError("Worker failed")
                return json.loads(output)
    except TimeoutError:
        return {"ok": False, "status": 408, "error": {"code": "extraction_timeout", "message": "Extraction took too long. Try a simpler PDF or a smaller scan.", "field": "resume"}}
    finally:
        if process is not None and process.returncode is None:
            process.kill()
            await process.wait()
