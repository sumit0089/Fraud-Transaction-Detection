const configured = import.meta.env.VITE_API_BASE_URL;
export const BASE_URL = (configured || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')).replace(/\/$/, '');

export async function request(path, options = {}) {
  if (!BASE_URL) throw new Error('Backend URL is not configured. Set VITE_API_BASE_URL and rebuild.');
  const start = performance.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(`${BASE_URL}${path}`, {...options, signal: controller.signal});
    const data = await response.json();
    if (!response.ok) {
      const fields = data.error?.fields?.length ? ` Fields: ${data.error.fields.join(', ')}.` : '';
      throw new Error((data.error?.message || `API returned ${response.status}.`) + fields);
    }
    const roundTripMs = performance.now() - start;
    const header = response.headers.get('X-Request-Time-Ms');
    const serverMs = header === null ? null : Number(header);
    return {data, timing: {roundTripMs, serverMs, overheadMs: serverMs === null ? null : Math.max(0, roundTripMs - serverMs)}};
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The API took over 60 seconds. A sleeping host may be starting; check system health and retry.');
    if (error instanceof TypeError) throw new Error('Cannot reach the API. Check your connection, backend URL, and allowed CORS origin.');
    throw error;
  } finally { clearTimeout(timer); }
}

export const predict = transaction => request('/api/predict', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(transaction)});
export const predictCSV = text => request('/api/predict/csv', {method: 'POST', headers: {'Content-Type': 'text/csv'}, body: text});
