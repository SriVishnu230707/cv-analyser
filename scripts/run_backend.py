"""Run the API with normal Python or workspace-local Codex dependencies."""
import sys
import argparse
import ipaddress
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
for folder in ("nlp", "backend"):
    local_dependencies = root / ".tools" / folder
    if local_dependencies.is_dir():
        sys.path.insert(0, str(local_dependencies))

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(root / ".env")
    import uvicorn
    parser = argparse.ArgumentParser(description="Run the local CV Analyser API")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1", help="Use 0.0.0.0 for same-Wi-Fi Android access")
    args = parser.parse_args()
    try:
        local = ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        local = args.host == 'localhost'
    if not local and len(os.environ.get('CV_API_TOKEN', '').strip()) < 32:
        parser.error('Set CV_API_TOKEN to a random token of at least 32 characters before sharing the server.')
    uvicorn.run("backend.main:app", host=args.host, port=args.port, proxy_headers=False, limit_concurrency=16)
