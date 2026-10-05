import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

globalThis.__nativeApiHttp = { request: async () => { throw Error('Unexpected native request'); } };
const source = (await readFile(new URL('../src/api.ts', import.meta.url), 'utf8')).replace("import { Capacitor, CapacitorHttp } from '@capacitor/core';", 'const Capacitor={isNativePlatform:()=>true}; const CapacitorHttp=globalThis.__nativeApiHttp;');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { checkedFetch, configureApiServer } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));
configureApiServer('https://analysis.example', true);

test('native requests forward auth, disable redirects and enforce network timeouts', async () => {
  globalThis.sessionStorage = { getItem: () => 'token' };
  globalThis.__nativeApiHttp.request = async options => {
    assert.equal(options.headers.Authorization ?? options.headers.authorization, 'Bearer token');
    assert.equal(options.disableRedirects, true);
    assert.equal(options.connectTimeout, 10000);
    assert.equal(options.readTimeout, 55000);
    assert.deepEqual(options.data, { resume_text: 'synthetic' });
    return { status: 200, headers: { 'content-type': 'application/json' }, data: { ok: true } };
  };
  try { assert.deepEqual(await (await checkedFetch('/api/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ resume_text: 'synthetic' }) })).json(), { ok: true }); }
  finally { delete globalThis.sessionStorage; }
});

test('cancelled native requests return promptly and discard late responses', async () => {
  let complete;
  globalThis.__nativeApiHttp.request = () => new Promise(resolve => { complete = resolve; });
  const controller = new AbortController();
  const response = checkedFetch('/api/compare', { signal: controller.signal });
  controller.abort();
  await assert.rejects(response, { name: 'AbortError' });
  complete({ status: 200, headers: {}, data: { ok: true } });
});

test('native uploads preserve binary bytes and sanitize multipart filenames', async () => {
  globalThis.FileReader = class {
    readAsDataURL(blob) { blob.arrayBuffer().then(data => { this.result = 'data:application/pdf;base64,' + Buffer.from(data).toString('base64'); this.onload(); }); }
  };
  const bytes = Buffer.from([37, 80, 68, 70, 45, 255, 0]);
  const form = new FormData(); form.append('resume', new Blob([bytes]), 'test"\r\n.pdf');
  globalThis.__nativeApiHttp.request = async options => {
    assert.equal(options.dataType, 'formData');
    assert.equal(options.data[0].fileName, 'test___.pdf');
    assert.deepEqual(Buffer.from(options.data[0].value, 'base64'), bytes);
    return { status: 200, headers: {}, data: { ok: true } };
  };
  try { await checkedFetch('/api/extract', { method: 'POST', body: form }); }
  finally { delete globalThis.FileReader; }
});
