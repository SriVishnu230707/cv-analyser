import { checkedFetch } from './api';

export interface SkillCatalog { version: string; skills: { name: string; aliases: string[] }[] }

export function parseSkillCatalog(value: unknown): SkillCatalog {
  if (!value || typeof value !== 'object' || !('version' in value) || typeof value.version !== 'string' || !value.version.trim() || !('skills' in value) || !Array.isArray(value.skills) || value.skills.length === 0) {
    throw new Error('The server returned an invalid skill dictionary. Please retry.');
  }
  for (const skill of value.skills) {
    if (!skill || typeof skill !== 'object' || typeof skill.name !== 'string' || !skill.name.trim() || !Array.isArray(skill.aliases) || skill.aliases.length === 0 || !skill.aliases.every((alias: unknown) => typeof alias === 'string' && alias.trim())) {
      throw new Error('The server returned an invalid skill dictionary. Please retry.');
    }
  }
  return value as SkillCatalog;
}

export async function fetchSkillCatalog(signal?: AbortSignal) {
  const response = await checkedFetch('/api/skills', { signal });
  return parseSkillCatalog(await response.json());
}
