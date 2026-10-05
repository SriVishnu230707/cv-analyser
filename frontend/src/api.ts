import { Capacitor, CapacitorHttp } from '@capacitor/core';

let apiBaseUrl = '';
let requiresServer = false;
export const tokenStorageKey = 'cv-analyser-access-token';

export function apiHeaders(url: string, original?: HeadersInit) {
  const headers = new Headers(original);
  if (url.startsWith('/') && !url.startsWith('//')) {
    try {
      const token = sessionStorage.getItem(tokenStorageKey);
      if (token && !headers.has('Authorization')) headers.set('Authorization', 'Bearer ' + token);
    } catch { /* The connection UI reports unavailable session storage. */ }
  }
  return headers;
}

export function normalizeServerUrl(value: string) {
  let url: URL;
  try { url = new URL(value.trim()); } catch { throw new Error('Enter a full server address, for example https://api.example.com or http://192.168.0.105:8001.'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new Error('Use only the server origin, without credentials, paths, query parameters or fragments.');
  return url.origin;
}

export function configureApiServer(value: string, required = false) {
  apiBaseUrl = value ? normalizeServerUrl(value) : '';
  requiresServer = required;
}

export function apiUrl(url: string) {
  if (url.startsWith('//')) throw new Error('Use a relative API path or a full server address.');
  if (requiresServer && !apiBaseUrl && url.startsWith('/')) throw new Error('Connect to your analysis server using Android server settings first.');
  return url.startsWith('/') ? apiBaseUrl + url : url;
}

export async function checkedFetch(url: string, options?: RequestInit) {
  const target = apiUrl(url);
  const timeout = AbortSignal.timeout(60000);
  const signal = options?.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
  signal.throwIfAborted();
  const headers = apiHeaders(url, options?.headers);
  const response = Capacitor.isNativePlatform() ? await nativeFetch(target, headers, signal, options) :
    await fetch(target, { ...options, headers, redirect: 'error', signal });
  if (!response.ok) {
    let message = 'The server could not complete this request. Please try again.';
    try {
      const body: unknown = await response.json();
      if (body && typeof body === 'object' && 'message' in body && typeof body.message === 'string') message = body.message;
    } catch { /* Proxy errors may contain HTML or an empty body. */ }
    throw new Error(message);
  }
  return response;
}

async function nativeFetch(url: string, headers: Headers, signal: AbortSignal, options?: RequestInit) {
  let data: unknown = options?.body;
  let dataType: 'formData' | undefined;
  if (data instanceof FormData) {
    const entries = [];
    for (const [key, value] of data.entries()) {
      if (!/^[a-zA-Z0-9_-]+$/.test(key)) throw new Error('Invalid upload field.');
      if (typeof value === 'string') entries.push({ key, value, type: 'string' });
      else {
        if (value.size > 5 * 1024 * 1024) throw new Error('Your resume must be 5 MiB or smaller.');
        const encoded = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result).split(',')[1]);
          reader.onerror = () => reject(new Error('Could not read the selected resume.'));
          reader.readAsDataURL(value);
        });
        entries.push({ key, value: encoded, type: 'base64File', contentType: 'application/octet-stream', fileName: value.name.replace(/["\r\n\\]/g, '_') });
      }
    }
    data = entries; dataType = 'formData';
    headers.set('Content-Type', 'multipart/form-data');
  } else if (typeof data === 'string' && headers.get('Content-Type')?.includes('application/json')) data = JSON.parse(data);
  signal.throwIfAborted();
  // The patched Capacitor fetch does not forward redirect/timeout/abort options.
  // Use the native API explicitly and discard responses after cancellation.
  const result = await new Promise<Awaited<ReturnType<typeof CapacitorHttp.request>>>((resolve, reject) => {
    const abort = () => reject(signal.reason);
    signal.addEventListener('abort', abort, { once: true });
    CapacitorHttp.request({ url, method: options?.method ?? 'GET', headers: Object.fromEntries(headers.entries()), data, dataType,
      responseType: 'json', disableRedirects: true, connectTimeout: 10000, readTimeout: 55000 })
      .then(resolve, reject).finally(() => signal.removeEventListener('abort', abort));
  });
  signal.throwIfAborted();
  return new Response(result.status === 204 ? null : typeof result.data === 'string' ? result.data : JSON.stringify(result.data), { status: result.status, headers: result.headers });
}

export function requestMessage(error: unknown) {
  if (error instanceof DOMException && error.name === 'TimeoutError') return 'The request timed out. Try again or use a smaller document.';
  if (error instanceof TypeError) return 'Cannot reach the server. Make sure the API is running, then try again.';
  if (error instanceof SyntaxError) return 'The server returned an unreadable response. Please try again.';
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
