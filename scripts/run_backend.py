"""Run the API with normal Python or workspace-local Codex dependencies."""
import sys
import argparse
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
for folder in ("nlp", "backend"):
    local_dependencies = root / ".tools" / folder
    if local_dependencies.is_dir():
        sys.path.insert(0, str(local_dependencies))

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Run the local CV Analyser API")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=args.port)
