import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const schema = JSON.parse(await readFile(new URL('../../contracts/analysis-result-v1.1.schema.json', import.meta.url), 'utf8'));
const fixture = JSON.parse(await readFile(new URL('./fixtures/report.json', import.meta.url), 'utf8'));
const source = await readFile(new URL('../src/reportValidation.ts', import.meta.url), 'utf8');
let compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
compiled = compiled.replace(/(['"])ajv\/dist\/2020\1/g, JSON.stringify(pathToFileURL(require.resolve('ajv/dist/2020.js')).href));
compiled = compiled.replace(/import schema from [^;]+;/, 'const schema = ' + JSON.stringify(schema) + ';');
const { parseReport, parseAIResponse } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));
const aiReport = { ...fixture, ai_analysis: { generation_id: 'synthetic-generation', provider: 'OpenAI', model: 'gpt-4.1-mini', embedding_model: 'text-embedding-3-small', discarded_rewrites: 0 } };

test('actual synthetic backend report and AI envelope are accepted', () => {
  assert.equal(parseReport(fixture).input_hash, fixture.input_hash);
  assert.equal(parseAIResponse({ report: aiReport, ai_context: 'signed-context' }, fixture.input_hash).report.ai_analysis.model, 'gpt-4.1-mini');
});

test('malformed reports are rejected before replacing visible state', () => {
  for (const value of [null, {}, { ...fixture, scores: null }, { ...fixture, suggestions: [null] }, { ...fixture, possible_evidence: null }, { ...fixture, ai_analysis: {} }, { ...fixture, resume_quality: { checks: [null] } }]) {
    assert.throws(() => parseReport(value), /invalid analysis report/);
  }
});

test('missing context, missing report, and stale AI reports are rejected', () => {
  for (const value of [null, { report: aiReport }, { report: null, ai_context: 'token' }, { report: fixture, ai_context: 'token' }, { report: { ...aiReport, input_hash: 'stale-input' }, ai_context: 'token' }]) {
    assert.throws(() => parseAIResponse(value, fixture.input_hash));
  }
});
