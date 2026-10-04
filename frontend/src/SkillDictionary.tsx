import { useEffect, useRef, useState } from 'react';
import { requestMessage } from './api';
import { fetchSkillCatalog } from './skillCatalog';
import type { SkillCatalog } from './skillCatalog';

export function SkillDictionary() {
  const [catalog, setCatalog] = useState<SkillCatalog | null>(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function load() {
    if (controller.current || catalog) return;
    const request = new AbortController(); controller.current = request;
    setLoading(true); setError('');
    try {
      const result = await fetchSkillCatalog(request.signal);
      if (!request.signal.aborted) setCatalog(result);
    } catch (error) { if (!request.signal.aborted) setError(requestMessage(error)); }
    finally { controller.current = null; setLoading(false); }
  }
  const normalized = query.trim().toLowerCase();
  const skills = catalog?.skills.filter(skill => [skill.name, ...skill.aliases].some(name => name.toLowerCase().includes(normalized))) ?? [];
  return <details className="card skill-dictionary" onToggle={event => { if (event.currentTarget.open && !catalog && !error) void load(); }}>
    <summary>Explore supported skills and aliases</summary>
    <p>The dictionary recognizes explicit technology names. Related tools remain separate skills. A recognized name still needs positive resume evidence to earn credit.</p>
    {loading ? <p role="status">Loading supported skills…</p> : null}
    {error ? <div><p className="error" role="alert">{error}</p><button type="button" className="text-button" onClick={() => void load()}>Retry dictionary</button></div> : null}
    {catalog ? <><label htmlFor="skill-search">Search by technology or alias</label><input id="skill-search" type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Try sklearn, Svelte, or Kafka" /><p role="status">{skills.length} of {catalog.skills.length} skills · Dictionary v{catalog.version}</p><ul className="dictionary-results">{skills.map(skill => <li key={skill.name}><strong>{skill.name}</strong><span>Recognized wording: {skill.aliases.join(', ')}</span></li>)}</ul>{skills.length === 0 ? <p>No supported skill matches this search. You can review an unknown job requirement and map a genuine alias during comparison.</p> : null}</> : null}
  </details>;
}
