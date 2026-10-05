import { useState } from 'react';
import { clearCachedReports, isAndroidApp, serverStorageKey } from './mobile';
import { checkedFetch, normalizeServerUrl, requestMessage, tokenStorageKey } from './api';

export function AndroidConnection({ disabled }: { disabled: boolean }) {
  return <Connection disabled={disabled} />;
}

function storedServer() {
  try { return localStorage.getItem(serverStorageKey) ?? ''; } catch { return ''; }
}

function Connection({ disabled }: { disabled: boolean }) {
  const [server, setServer] = useState(storedServer);
  const [token, setToken] = useState(() => { try { return sessionStorage.getItem(tokenStorageKey) ?? ''; } catch { return ''; } });
  const [status, setStatus] = useState('');
  const [testing, setTesting] = useState(false);
  async function testConnection() {
    setTesting(true); setStatus('');
    try {
      const url = isAndroidApp ? normalizeServerUrl(server) : '';
      const response = await checkedFetch(url + '/api/demo/job', { headers: { Authorization: 'Bearer ' + token.trim() } });
      const body = await response.json();
      if (typeof body?.job_description !== 'string') throw new Error('This address did not return a CV Analyser API.');
      setStatus('Server is reachable. Save this address to use it.');
    } catch (error) { setStatus(requestMessage(error)); }
    finally { setTesting(false); }
  }
  function save() {
    try {
      if (isAndroidApp) localStorage.setItem(serverStorageKey, normalizeServerUrl(server));
      if (token.trim()) sessionStorage.setItem(tokenStorageKey, token.trim());
      else sessionStorage.removeItem(tokenStorageKey);
      window.location.reload();
    } catch (error) { setStatus(requestMessage(error)); }
  }
  return <details className="android-connection" open={isAndroidApp && !storedServer()}>
    <summary>{isAndroidApp ? 'Android server settings' : 'Server access settings'}</summary>
    <p>{isAndroidApp ? 'Enter your analysis server address. Use HTTPS for a hosted server. ' : ''}Shared servers require the access token set by the server owner. The token lasts for this app session. Saving restarts your current review.</p>
    {isAndroidApp ? <><label htmlFor="analysis-server">Analysis server address</label>
    <input id="analysis-server" type="url" inputMode="url" autoCapitalize="none" autoCorrect="off" spellCheck={false} placeholder="http://192.168.0.105:8001" value={server} onChange={e => { setServer(e.target.value); setStatus(''); }} disabled={disabled || testing} />
    </> : null}
    <label htmlFor="server-token">Server access token</label>
    <input id="server-token" type="password" autoComplete="off" autoCapitalize="none" spellCheck={false} value={token} onChange={e => { setToken(e.target.value); setStatus(''); }} disabled={disabled || testing} />
    <div><button type="button" onClick={() => void testConnection()} disabled={disabled || testing}>{testing ? 'Testing…' : 'Test connection'}</button><button type="button" onClick={save} disabled={disabled || testing}>Save server</button></div>
    {isAndroidApp ? <><p>Exports stay in private app cache until Android removes them or you clear them here. Clear after your chosen app finishes saving the report.</p><button type="button" disabled={disabled || testing} onClick={async () => {
      setTesting(true);
      try { await clearCachedReports(); setStatus('Cached reports cleared. Copies saved in other apps remain there.'); }
      catch (error) { setStatus(requestMessage(error)); }
      finally { setTesting(false); }
    }}>Clear cached reports</button></> : null}
    <p role="status" aria-live="polite">{status}</p>
  </details>;
}
