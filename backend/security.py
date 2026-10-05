"""Bound uploads before parsing and protect shared servers before reading bodies."""
import hmac
import ipaddress
import os

from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 6 * 1024 * 1024  # 5 MiB file plus multipart overhead


class SecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))

        async def reject(status, code, message):
            await JSONResponse({'code': code, 'message': message, 'field': 'request'}, status_code=status,
                               headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})(scope, receive, send)

        if scope['path'] != '/health':
            token = os.environ.get('CV_API_TOKEN', '').strip()
            peer = (scope.get('client') or ('', 0))[0]
            try:
                loopback = ipaddress.ip_address(peer).is_loopback
            except ValueError:
                loopback = peer == 'testclient'
            if not token and not loopback:
                return await reject(503, 'access_not_configured', 'Shared server access requires CV_API_TOKEN on the backend.')
            if token and not hmac.compare_digest(headers.get(b'authorization', b''), ('Bearer ' + token).encode()):
                return await reject(401, 'unauthorized', 'Enter the server access token in connection settings.')
            # With no token, a browser on another site must not invoke local analysis.
            origin = headers.get(b'origin', b'').decode('latin-1')
            allowed = {'http://localhost:5173', 'http://127.0.0.1:5173', 'https://localhost', 'http://localhost'}
            allowed.update(filter(None, os.environ.get('CV_ALLOWED_ORIGINS', '').split(',')))
            if origin and origin not in allowed and not token:
                return await reject(403, 'untrusted_origin', 'This browser origin is not allowed to access the analysis server.')

        length = headers.get(b'content-length')
        if length is not None:
            try:
                size = int(length)
                if size < 0:
                    raise ValueError()
            except ValueError:
                return await reject(400, 'invalid_length', 'Invalid request length.')
            if size > MAX_REQUEST_BYTES:
                return await reject(413, 'request_too_large', 'The complete request must be 6 MiB or smaller.')

        # Bounded buffering also handles chunked uploads and dishonest Content-Length.
        # No multipart parser or temporary file runs until the size is verified.
        chunks, total = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            total += len(chunk)
            if total > MAX_REQUEST_BYTES:
                return await reject(413, 'request_too_large', 'The complete request must be 6 MiB or smaller.')
            if chunk:
                chunks.append(chunk)
            if not message.get('more_body', False):
                break
        body = b''.join(chunks)
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()

        async def secure_send(message):
            if message['type'] == 'http.response.start':
                response_headers = list(message.get('headers', []))
                response_headers = [(k, v) for k, v in response_headers if k.lower() not in {b'cache-control', b'x-content-type-options'}]
                message = {**message, 'headers': response_headers + [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]}
            await send(message)

        await self.app(scope, bounded_receive, secure_send)
