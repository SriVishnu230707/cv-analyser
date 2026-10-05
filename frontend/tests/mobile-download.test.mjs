import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const nativeHttp={ request: async () => { throw Error('Unexpected request'); } };
globalThis.__androidTestHttp=nativeHttp;
let source=await readFile(new URL('../src/mobile.ts',import.meta.url),'utf8');
source=source.replace("import { Capacitor, CapacitorHttp } from '@capacitor/core';",'const Capacitor={isNativePlatform:()=>true}; const CapacitorHttp=globalThis.__androidTestHttp;')
  .replace("import { Filesystem, Directory } from '@capacitor/filesystem';",'const Filesystem={}; const Directory={};')
  .replace("import { Share } from '@capacitor/share';",'const Share={};')
  .replace("import { apiUrl, checkedFetch, configureApiServer } from './api';",'const apiUrl=url=>"https://analysis.example"+url; const checkedFetch=()=>{throw Error("Unexpected browser request")}; const configureApiServer=()=>{};');
const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const {downloadResponse}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));

test('native PDF downloads preserve non-UTF8 bytes exactly',async()=>{
  const bytes=Uint8Array.from([37,80,68,70,45,0,255,128,254,13,10]);
  nativeHttp.request=async options=>{
    assert.equal(options.url,'https://analysis.example/api/report/export');
    assert.equal(options.responseType,'arraybuffer');
    assert.deepEqual(options.data,{format:'pdf'});
    return {status:200,headers:{'content-type':'application/pdf'},data:Buffer.from(bytes).toString('base64')};
  };
  const response=await downloadResponse('/api/report/export',{method:'POST',body:JSON.stringify({format:'pdf'})});
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()),bytes);
});

test('native JSON exports preserve parsed fields',async()=>{
  nativeHttp.request=async()=>({status:200,headers:{'Content-Type':'application/json'},data:{scores:{overall:57.5},resume_sections:[]}});
  const response=await downloadResponse('/api/report/export');
  assert.deepEqual(await response.json(),{scores:{overall:57.5},resume_sections:[]});
});

test('native export errors and pre-cancelled requests cannot become report files',async()=>{
  nativeHttp.request=async()=>({status:422,headers:{},data:{message:'Confirm the categories first.'}});
  await assert.rejects(downloadResponse('/api/report/export'),/Confirm the categories first/);
  const controller=new AbortController();controller.abort();
  nativeHttp.request=async()=>{assert.fail('Cancelled request must not reach Android');};
  await assert.rejects(downloadResponse('/api/report/export',{signal:controller.signal}),{name:'AbortError'});
});
