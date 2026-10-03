"""One-shot worker: raw bytes on stdin, structured JSON on stdout, no file writes."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
if (root / ".tools/backend").is_dir():
    sys.path.insert(0, str(root / ".tools/backend"))

from backend.services.document_parser import ExtractionError, extract_document

if __name__ == "__main__":
    try:
        result = {"ok": True, "result": extract_document(sys.stdin.buffer.read(5 * 1024 * 1024 + 1), sys.argv[1])}
    except ExtractionError as exc:
        result = {"ok": False, "error": {"code": exc.code, "message": exc.message, "field": "resume"}, "status": exc.status}
    except Exception:
        result = {"ok": False, "error": {"code": "extraction_failed", "message": "The document could not be processed. Re-export it and try again.", "field": "resume"}, "status": 422}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
