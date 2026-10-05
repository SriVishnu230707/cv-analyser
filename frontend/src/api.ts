let apiBaseUrl = '';
let requiresServer = false;

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
  if (requiresServer && !apiBaseUrl && url.startsWith('/')) throw new Error('Connect to your analysis server using Android server settings first.');
  return url.startsWith('/') ? apiBaseUrl + url : url;
}

export async function checkedFetch(url: string, options?: RequestInit) {
  const target = apiUrl(url);
  const timeout = AbortSignal.timeout(60000);
  const response = await fetch(target, { ...options, signal: options?.signal ? AbortSignal.any([options.signal, timeout]) : timeout });
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

export function requestMessage(error: unknown) {
  if (error instanceof DOMException && error.name === 'TimeoutError') return 'The request timed out. Try again or use a smaller document.';
  if (error instanceof TypeError) return 'Cannot reach the server. Make sure the API is running, then try again.';
  if (error instanceof SyntaxError) return 'The server returned an unreadable response. Please try again.';
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
