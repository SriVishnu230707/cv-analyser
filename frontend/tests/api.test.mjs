import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

// Compile only this small module in memory; no extra test dependencies are needed.
const source = await readFile(new URL('../src/api.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { checkedFetch, requestMessage } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));

test('HTML, empty, and null server errors show an actionable message', async () => {
  const original = globalThis.fetch;
  try {
    for (const body of ['<html>Bad gateway</html>', '', 'null']) {
      globalThis.fetch = async () => new Response(body, { status: 502 });
      await assert.rejects(checkedFetch('/api/compare'), { message: 'The server could not complete this request. Please try again.' });
    }
  } finally { globalThis.fetch = original; }
});

test('structured API errors retain their useful validation message', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => Response.json({ message: 'Re-extract the document.' }, { status: 422 });
    await assert.rejects(checkedFetch('/api/report/export'), { message: 'Re-extract the document.' });
  } finally { globalThis.fetch = original; }
});

test('caller cancellation is passed through to fetch', async () => {
  const original = globalThis.fetch;
  try {
    const controller = new AbortController();
    let signal;
    globalThis.fetch = async (_url, options) => { signal = options.signal; return new Response('ok'); };
    await checkedFetch('/api/report/export', { signal: controller.signal });
    controller.abort();
    assert.equal(signal.aborted, true);
  } finally { globalThis.fetch = original; }
});

test('network, timeout, and malformed success responses have readable messages', () => {
  assert.match(requestMessage(new TypeError('Failed to fetch')), /Cannot reach the server/);
  assert.match(requestMessage(new DOMException('timed out', 'TimeoutError')), /timed out/);
  assert.match(requestMessage(new SyntaxError('Unexpected token <')), /unreadable response/);
});
