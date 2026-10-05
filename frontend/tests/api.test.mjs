import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

// Compile only this small module in memory; no extra test dependencies are needed.
const source = (await readFile(new URL('../src/api.ts', import.meta.url), 'utf8')).replace("import { Capacitor, CapacitorHttp } from '@capacitor/core';", 'const Capacitor={isNativePlatform:()=>false}; const CapacitorHttp={};');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { checkedFetch, requestMessage, normalizeServerUrl, configureApiServer, apiHeaders, apiUrl } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));

test('session access token is attached only to application API paths',()=>{
  globalThis.sessionStorage={getItem:()=> 'test-token'};
  try {
    assert.equal(apiHeaders('/api/compare').get('authorization'),'Bearer test-token');
    assert.equal(apiHeaders('/api/demo/job', {Authorization:'Bearer new-token'}).get('authorization'),'Bearer new-token');
    assert.equal(apiHeaders('https://other.example').get('authorization'),null);
    assert.equal(apiHeaders('//other.example').get('authorization'),null);
    assert.throws(()=>apiUrl('//other.example'),/relative API path/);
  } finally { delete globalThis.sessionStorage; }
});

test('Android rejects invalid server origins before any resume is sent', () => {
  for (const value of ['file:///tmp', 'javascript:alert(1)', 'https://user:secret@example.com', 'https://example.com/api', 'https://example.com?token=x', 'https://example.com#secret']) assert.throws(() => normalizeServerUrl(value));
  assert.equal(normalizeServerUrl(' http://192.168.0.105:8001/ '), 'http://192.168.0.105:8001');
});

test('Android requires a server and routes upload requests to the saved origin', async () => {
  const original = globalThis.fetch;
  try {
    configureApiServer('', true);
    await assert.rejects(checkedFetch('/api/extract'), /server settings first/);
    configureApiServer('http://10.0.2.2:8001', true);
    let target, body;
    globalThis.fetch = async (url, options) => { target=url;body=options.body;return new Response('ok'); };
    const form=new FormData();form.append('resume',new Blob(['%PDF-synthetic']), 'resume.pdf');
    await checkedFetch('/api/extract', { method:'POST', body:form });
    assert.equal(target,'http://10.0.2.2:8001/api/extract');assert.equal(body,form);
  } finally { globalThis.fetch=original; configureApiServer(''); }
});

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
