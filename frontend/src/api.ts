export async function checkedFetch(url: string, options?: RequestInit) {
  const timeout = AbortSignal.timeout(60000);
  const response = await fetch(url, { ...options, signal: options?.signal ? AbortSignal.any([options.signal, timeout]) : timeout });
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
