import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const fixture = JSON.parse(await readFile(new URL('./fixtures/workflow.json', import.meta.url), 'utf8'));
const extractionSchema = JSON.parse(await readFile(new URL('../../contracts/extraction-result.schema.json', import.meta.url), 'utf8'));
const profileSchema = JSON.parse(await readFile(new URL('../../contracts/structured-profile.schema.json', import.meta.url), 'utf8'));
const source = await readFile(new URL('../src/workflowValidation.ts', import.meta.url), 'utf8');
let compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
compiled = compiled.replace(/(['"])ajv\/dist\/2020\1/g, JSON.stringify(pathToFileURL(require.resolve('ajv/dist/2020.js')).href));
compiled = compiled.replace(/import extractionSchema from [^;]+;/, 'const extractionSchema = ' + JSON.stringify(extractionSchema) + ';');
compiled = compiled.replace(/import profileSchema from [^;]+;/, 'const profileSchema = ' + JSON.stringify(profileSchema) + ';');
const { parseExtraction, parseProfile, parseDemoJob } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));

test('real synthetic backend extraction and preparation pass validation', () => {
  assert.equal(parseExtraction(fixture.extraction).text, fixture.profile.resume_text);
  assert.equal(parseProfile(fixture.profile, fixture.extraction.text, fixture.profile.job_description).preparation_id, fixture.profile.preparation_id);
  assert.equal(parseDemoJob({ job_description: fixture.profile.job_description }), fixture.profile.job_description);
});

test('malformed extraction cannot enter the preview', () => {
  for (const value of [null, {}, { ...fixture.extraction, sections: [null] }, { ...fixture.extraction, readability: null }, { ...fixture.extraction, pages: [] }, { ...fixture.extraction, text: 42 }]) {
    assert.throws(() => parseExtraction(value), /invalid extracted resume/);
  }
});

test('malformed and stale profiles cannot replace preparation or review', () => {
  for (const value of [null, {}, { ...fixture.profile, resume_skills: [null] }, { ...fixture.profile, job_requirements: [null] }, { ...fixture.profile, warnings: null }, { ...fixture.profile, resume_text: 'Stale source' }, { ...fixture.profile, job_description: 'Stale job' }]) {
    assert.throws(() => parseProfile(value, fixture.extraction.text, fixture.profile.job_description), /invalid or mismatched/);
  }
});

test('legitimate server normalization is accepted', () => {
  const padded = '  ' + fixture.extraction.text.replaceAll('\n', '\r\n  ').replaceAll(' ', '\u00a0') + '\r\n';
  assert.equal(parseProfile(fixture.profile, padded, '  ' + fixture.profile.job_description + '  ').resume_text, fixture.profile.resume_text);
});

test('invalid demo responses fail before overwriting form state', () => {
  for (const value of [null, {}, { job_description: 42 }, { job_description: 'short' }, { job_description: 'x'.repeat(20001) }]) {
    assert.throws(() => parseDemoJob(value), /example job description is invalid/);
  }
});
