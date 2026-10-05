import { useState } from 'react';
import { isAndroidApp, serverStorageKey } from './mobile';
import { checkedFetch, normalizeServerUrl, requestMessage } from './api';

export function AndroidConnection({ disabled }: { disabled: boolean }) {
  return isAndroidApp ? <Connection disabled={disabled} /> : null;
}

function storedServer() {
  try { return localStorage.getItem(serverStorageKey) ?? ''; } catch { return ''; }
}

function Connection({ disabled }: { disabled: boolean }) {
  const [server, setServer] = useState(storedServer);
  const [status, setStatus] = useState('');
  const [testing, setTesting] = useState(false);
  async function testConnection() {
    setTesting(true); setStatus('');
    try {
      const url = normalizeServerUrl(server);
      const response = await checkedFetch(url + '/health');
      const body = await response.json();
      if (body?.status !== 'ok') throw new Error('This address did not return a healthy CV Analyser API.');
      setStatus('Server is reachable. Save this address to use it.');
    } catch (error) { setStatus(requestMessage(error)); }
    finally { setTesting(false); }
  }
  function save() {
    try {
      const url = normalizeServerUrl(server);
      localStorage.setItem(serverStorageKey, url);
      window.location.reload();
    } catch (error) { setStatus(requestMessage(error)); }
  }
  return <details className="android-connection" open={!storedServer()}>
    <summary>Android server settings</summary>
    <p>The app needs an analysis server. On the same Wi-Fi, enter your computer’s address and API port. Use HTTPS for a hosted server. Saving restarts your current review.</p>
    <label htmlFor="analysis-server">Analysis server address</label>
    <input id="analysis-server" type="url" inputMode="url" autoCapitalize="none" autoCorrect="off" spellCheck={false} placeholder="http://192.168.0.105:8001" value={server} onChange={e => { setServer(e.target.value); setStatus(''); }} disabled={disabled || testing} />
    <div><button type="button" onClick={() => void testConnection()} disabled={disabled || testing}>{testing ? 'Testing…' : 'Test connection'}</button><button type="button" onClick={save} disabled={disabled || testing}>Save server</button></div>
    <p role="status" aria-live="polite">{status}</p>
  </details>;
}
