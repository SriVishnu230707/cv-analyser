"""Short-lived signed findings, no stored resumes or browser-trusted scores."""
import base64
import hashlib
import hmac
import json
import secrets
import time

KEY = secrets.token_bytes(32)


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def sign_context(result):
    payload = {'text_hash': text_hash(result['text']), 'readability': result['readability'], 'warnings': result['warnings'], 'expires': int(time.time()) + 3600}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode()
    return encoded + '.' + hmac.new(KEY, encoded.encode(), hashlib.sha256).hexdigest()


def read_context(token, text):
    if not token:
        return {'status': 'not_assessed', 'issues': ['Extraction context was not provided.']}
    try:
        encoded, signature = token.rsplit('.', 1)
        if not hmac.compare_digest(signature, hmac.new(KEY, encoded.encode(), hashlib.sha256).hexdigest()):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(encoded))
        if payload['expires'] < time.time():
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise ValueError('Extraction context is invalid or expired. Re-extract the document.') from None
    findings = {**payload['readability'], 'issues': [*payload['readability']['issues'], *payload['warnings']]}
    if payload['text_hash'] != text_hash(text):
        findings['status'] = 'needs_review'
        findings['issues'].append('The extracted text was edited. Check completeness and reading order again.')
    return findings
