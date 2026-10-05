import { Capacitor, CapacitorHttp } from '@capacitor/core';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import { apiUrl, checkedFetch, configureApiServer } from './api';

export const isAndroidApp = Capacitor.isNativePlatform();
export const serverStorageKey = 'cv-analyser-server';

export function initializeMobile() {
  if (!isAndroidApp) return;
  document.documentElement.classList.add('native-app');
  let server = '';
  try { server = localStorage.getItem(serverStorageKey) ?? ''; configureApiServer(server, true); }
  catch { configureApiServer('', true); }
}

export async function downloadResponse(url: string, options?: RequestInit): Promise<Response> {
  if (!isAndroidApp) return checkedFetch(url, options);
  options?.signal?.throwIfAborted();
  // Explicit binary response avoids UTF-8 conversion in the patched WebView fetch.
  const result = await CapacitorHttp.request({
    url: apiUrl(url), method: options?.method ?? 'GET',
    headers: Object.fromEntries(new Headers(options?.headers).entries()),
    data: typeof options?.body === 'string' ? JSON.parse(options.body) : undefined,
    responseType: 'arraybuffer', connectTimeout: 10000, readTimeout: 60000,
  });
  options?.signal?.throwIfAborted();
  if (result.status < 200 || result.status >= 300) throw new Error(typeof result.data?.message === 'string' ? result.data.message : 'The server could not prepare this download. Please try again.');
  const headers = new Headers(result.headers);
  const isJson = (headers.get('Content-Type') ?? '').includes('application/json');
  const data = isJson ? JSON.stringify(result.data) : Uint8Array.from(atob(result.data), character => character.charCodeAt(0));
  return new Response(data, { status: result.status, headers });
}

export async function saveReport(blob: Blob, filename: string) {
  if (!isAndroidApp) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    return 'Report prepared for download.';
  }
  const data = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = () => reject(new Error('Could not prepare the report file.'));
    reader.readAsDataURL(blob);
  });
  const file = await Filesystem.writeFile({ path: `reports/${filename}`, data, directory: Directory.Cache, recursive: true });
  await Share.share({ title: 'CV Analyser report', url: file.uri, dialogTitle: 'Save or share your report' });
  // Keep the cache file available while the selected Android app reads its URI.
  // Android may reclaim cache files; these are user-requested exports, not resume history.
  return 'Report ready. Use Android sharing to save it to your chosen app or folder.';
}
