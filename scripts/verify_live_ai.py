"""Opt-in, synthetic end-to-end AI check against a running local backend."""
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

RESUME = 'Projects\nTracked application events using Python.\nEducation\nCompleted an introductory programming course.'
JOB = 'Monitor logs. ' + 'This fictional team creates reliable tools for internal customers. ' * 2


def api_request(base_url, path, payload=None):
    encoded = json.dumps(payload).encode() if payload is not None else None
    request = Request(base_url.rstrip('/') + path, data=encoded, headers={'Content-Type': 'application/json'}, method='POST' if encoded is not None else 'GET')
    try:
        with urlopen(request, timeout=65) as response:
            data = response.read(5_000_001)
            if len(data) > 5_000_000:
                raise ValueError('Verification response exceeded the size limit.')
            return data if path == '/api/report/export' and payload['format'] == 'pdf' else json.loads(data)
    except HTTPError as exc:
        raise ValueError(f'Backend rejected {path} with HTTP {exc.code}. Check the API configuration and local server logs.') from None
    except (URLError, TimeoutError, OSError):
        raise ValueError('Cannot reach the local backend. Start it on the configured port and retry.') from None


def verify(base_url, allow_live=False, request=api_request):
    parsed = urlparse(base_url)
    if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'} or parsed.username or parsed.password or parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
        raise ValueError('Use the HTTP URL of a local backend, without credentials or a path.')
    status = request(base_url, '/api/ai/status')
    if not isinstance(status, dict) or status.get('configured') is not True:
        raise ValueError('OpenAI is not configured. Set OPENAI_API_KEY privately in the backend .env and restart the API. Live AI is still unverified.')
    if not allow_live:
        return {'status': 'not_run', 'reason': 'Configuration is present but model access is unverified. Use --run-live to authorize synthetic input and API charges.'}

    inputs = {'resume_text': RESUME, 'job_description': JOB}
    profile = request(base_url, '/api/preview', inputs)
    categories = [{'requirement_id': r['id'], 'category': 'excluded' if r['category'] == 'unclassified_skill' else r['category']} for r in profile['job_requirements']]
    reviewed = request(base_url, '/api/requirements/review', {**inputs, 'corrections': categories})
    if reviewed['review_status'] != 'confirmed':
        raise ValueError('Synthetic requirement review did not complete.')
    comparison = {**inputs, 'requirements_confirmed': True, 'category_corrections': categories}
    local = request(base_url, '/api/compare', comparison)
    enhanced = request(base_url, '/api/ai/analyze', {**comparison, 'cloud_consent': True})
    report = enhanced['report']
    if not enhanced['ai_context'] or not report.get('ai_analysis') or report['input_hash'] != local['input_hash'] or report['scores'] != local['scores']:
        raise ValueError('AI analysis failed provenance, input binding, or score preservation checks.')
    export_input = {**comparison, 'ai_context': enhanced['ai_context']}
    exported = request(base_url, '/api/report/export', {**export_input, 'format': 'json'})
    if exported['ai_analysis']['generation_id'] != report['ai_analysis']['generation_id']:
        raise ValueError('JSON export did not retain the AI generation.')
    pdf = request(base_url, '/api/report/export', {**export_input, 'format': 'pdf'})
    if not isinstance(pdf, bytes) or not pdf.startswith(b'%PDF-'):
        raise ValueError('PDF export did not produce a PDF.')
    return {'status': 'passed', 'model': report['ai_analysis']['model'], 'embedding_model': report['ai_analysis']['embedding_model'], 'score_preserved': True, 'json_export': True, 'pdf_export': True, 'limits': 'One synthetic live workflow verifies connectivity and contracts, not semantic accuracy on real resumes.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8001')
    parser.add_argument('--run-live', action='store_true', help='Authorize sending synthetic data to OpenAI; API charges may apply.')
    args = parser.parse_args()
    try:
        outcome = verify(args.base_url, args.run_live)
    except (ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'not_verified', 'reason': str(exc)}))
        return 2
    print(json.dumps(outcome, indent=2))
    return 0 if outcome['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
