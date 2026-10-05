# Security and bug review

Shared-server analysis and paid OpenAI requests now require a bearer access token. Local loopback development remains available without a token. The launcher refuses external binding without a token of at least 32 characters, ignores forwarded client headers, and bounds concurrency. Direct ASGI hosting also fails closed for remote clients when no token is configured. Use HTTPS for hosted servers: a token does not encrypt debug LAN HTTP.

Cross-site browser requests cannot invoke an unprotected local API. Set `CV_ALLOWED_ORIGINS` for a custom local browser origin. API responses have no-store and nosniff headers. The 6 MiB total request limit checks declared size and actual streamed bytes before JSON or multipart parsing; individual resume files still have a 5 MiB limit.

The web and Android interfaces accept a server access token kept in session storage. It is attached only to application API paths. Native requests explicitly disable redirects and set connection/read timeouts. Cancellation discards late native responses; Capacitor does not expose a transport cancellation method. Multipart filenames are sanitized before native serialization. Downloads check filenames, media types, PDF signatures, JSON parsing and a 10 MiB save limit. Android settings can clear private report cache after sharing finishes.

Regression checks cover unauthorized AI access, valid/invalid tokens, spoofed forwarded headers, hostile browser origins, declared and chunked oversized bodies, native binary/multipart preservation, cancellation, redirected request options and malformed downloads. Dependency audits cover npm and the installed backend/NLP Python dependency directories. This review does not establish absence of all vulnerabilities; hosted deployment and physical-device testing require their own verification.

Implementation references: [Starlette ASGI middleware](https://www.starlette.io/middleware/) and [Capacitor native HTTP controls](https://capacitorjs.com/docs/apis/http).

## Verification

Version 0.11.1: 192 backend tests and 27 frontend tests passed. npm audit and pip-audit of the installed backend/NLP dependency directories reported no known vulnerabilities. Android build, APK signature verification and lint passed (0 errors, 18 template/dependency warnings). Emulator checks exercised authenticated connection, native multipart extraction, 57.5% synthetic scoring, valid PDF/JSON exports, clearing report cache and rejection of unauthenticated native requests. Native bridge logging is disabled to keep request tokens and candidate content out of bridge logs. Physical phones and live OpenAI billing were not tested in this review.
