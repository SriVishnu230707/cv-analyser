import { Capacitor, CapacitorHttp } from '@capacitor/core';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import { apiHeaders, apiUrl, checkedFetch, configureApiServer } from './api';

export const isAndroidApp = Capacitor.isNativePlatform();
export const serverStorageKey = 'cv-analyser-server';

export function initializeMobile() {
  if (!isAndroidApp) return;
  document.documentElement.classList.add('native-app');
  let server = '';
  try { server = localStorage.getItem(serverStorageKey) ?? ''; configureApiServer(server, true); }
  catch { configureApiServer('', true); }
}

export async function clearCachedReports() {
  try { await Filesystem.rmdir({ path: 'reports', directory: Directory.Cache, recursive: true }); }
  catch (error) {
    if (!(error && typeof error === 'object' && 'code' in error && error.code === 'OS-PLUG-FILE-0008')) throw new Error('Could not clear cached reports. Try again.');
  }
}

export async function downloadResponse(url: string, options?: RequestInit): Promise<Response> {
  if (!isAndroidApp) return checkedFetch(url, options);
  options?.signal?.throwIfAborted();
  // Explicit binary response avoids UTF-8 conversion in the patched WebView fetch.
  const result = await CapacitorHttp.request({
    url: apiUrl(url), method: options?.method ?? 'GET',
    headers: Object.fromEntries(apiHeaders(url, options?.headers).entries()),
    data: typeof options?.body === 'string' ? JSON.parse(options.body) : undefined,
    responseType: 'arraybuffer', connectTimeout: 10000, readTimeout: 60000, disableRedirects: true,
  });
  options?.signal?.throwIfAborted();
  if (result.status < 200 || result.status >= 300) throw new Error(typeof result.data?.message === 'string' ? result.data.message : 'The server could not prepare this download. Please try again.');
  const headers = new Headers(result.headers);
  const isJson = (headers.get('Content-Type') ?? '').includes('application/json');
  const data = isJson ? JSON.stringify(result.data) : Uint8Array.from(atob(result.data), character => character.charCodeAt(0));
  return new Response(data, { status: result.status, headers });
}

export async function saveReport(blob: Blob, filename: string) {
  if (!/^cv-analysis-[a-f0-9]{8}\.(pdf|json)$/.test(filename)) throw new Error('Invalid report filename.');
  if (blob.size > 10 * 1024 * 1024) throw new Error('The report is too large to save.');
  if (filename.endsWith('.pdf')) {
    if (!blob.type.toLowerCase().includes('application/pdf') || await blob.slice(0, 5).text() !== '%PDF-') throw new Error('The server did not return a valid PDF report.');
  } else {
    if (!blob.type.toLowerCase().includes('application/json')) throw new Error('The server did not return a JSON report.');
    try { JSON.parse(await blob.text()); } catch { throw new Error('The server returned an unreadable JSON report.'); }
  }
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
  try { await Share.share({ title: 'CV Analyser report', url: file.uri, dialogTitle: 'Save or share your report' }); }
  catch (error) {
    if (error instanceof Error && error.message === 'Share canceled') return 'Sharing cancelled. The report remains in private app cache.';
    throw error;
  }
  // Keep the cache file available while the selected Android app reads its URI.
  // Android may reclaim cache files; these are user-requested exports, not resume history.
  return 'Report ready. Use Android sharing to save it to your chosen app or folder.';
}
