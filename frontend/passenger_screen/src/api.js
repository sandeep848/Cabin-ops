/** Surface failed server operations, including expired sessions. */
export async function apiFetch(url, options = {}) {
  const response = await globalThis.fetch(url, options);
  if (!response.ok && response.status !== 401) {
    const body = await response.clone().json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`;
    throw new Error(detail);
  }
  if (response.status === 401 && !url.includes('/auth/')) {
    window.dispatchEvent(new Event('cabinops-session-expired'));
    throw new Error('Your session expired. Please sign in again.');
  }
  return response;
}
