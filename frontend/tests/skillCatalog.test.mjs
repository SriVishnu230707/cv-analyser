import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

async function moduleUrl(filename) {
  const source = await readFile(new URL(filename, import.meta.url), 'utf8');
  return 'data:text/javascript;base64,' + Buffer.from(ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText).toString('base64');
}
const apiUrl = await moduleUrl('../src/api.ts');
const catalogUrl = await moduleUrl('../src/skillCatalog.ts');
const code = Buffer.from(catalogUrl.split(',')[1], 'base64').toString().replace(/(['"])\.\/api\1/g, JSON.stringify(apiUrl));
const { parseSkillCatalog, fetchSkillCatalog } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));

test('malformed catalog responses are rejected before rendering', () => {
  for (const value of [null, {}, { version: '1', skills: null }, { version: '1', skills: [] }, { version: '1', skills: [null] }, { version: '1', skills: [{ name: 'Python', aliases: null }] }, { version: '1', skills: [{ name: 'Python', aliases: [42] }] }, { version: '1', skills: [{ name: '', aliases: ['python'] }] }]) {
    assert.throws(() => parseSkillCatalog(value), /invalid skill dictionary/);
  }
});

test('the actual server catalog passes validation', async () => {
  const catalog = JSON.parse(await readFile(new URL('../../backend/data/skills.json', import.meta.url), 'utf8'));
  assert.equal(parseSkillCatalog(catalog).skills.length, 71);
});

test('dictionary fetch recovers after a malformed success response', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => Response.json({ version: 'bad', skills: null });
    await assert.rejects(fetchSkillCatalog(), /invalid skill dictionary/);
    globalThis.fetch = async () => Response.json({ version: '1', skills: [{ name: 'Python', aliases: ['python'] }] });
    assert.equal((await fetchSkillCatalog()).skills[0].name, 'Python');
  } finally { globalThis.fetch = original; }
});
