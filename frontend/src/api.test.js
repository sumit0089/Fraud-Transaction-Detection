import { afterEach, describe, expect, it, vi } from 'vitest';
import { predict, predictCSV, request } from './api';
afterEach(() => {vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.useRealTimers();});
describe('API transport', () => {
  it('sends actual form values and reads model output and server timing', async () => {
    const payload = {amount:125, new_device:true};
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({result:{risk_score:.37}}), {headers:{'X-Request-Time-Ms':'2.5'}}));
    vi.stubGlobal('fetch', fetch);
    const result = await predict(payload);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(payload);
    expect(fetch.mock.calls[0][0]).toMatch(/\/api\/predict$/);
    expect(result.data.result.risk_score).toBe(.37);
    expect(result.timing.serverMs).toBe(2.5);
  });
  it('preserves server validation errors without submitting again', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({error:{message:'Invalid fields',fields:['body.amount']}}), {status:422}));
    vi.stubGlobal('fetch', fetch);
    await expect(predict({})).rejects.toThrow('body.amount');
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('explains network failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(request('/health')).rejects.toThrow('Cannot reach the API');
  });
  it('sends CSV as raw text', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{}'));
    vi.stubGlobal('fetch',fetch);
    await predictCSV('amount,hour\n10,4');
    expect(fetch.mock.calls[0][1].headers['Content-Type']).toBe('text/csv');
    expect(fetch.mock.calls[0][1].body).toBe('amount,hour\n10,4');
  });
  it('explains request timeouts', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch',vi.fn((url, {signal}) => new Promise((resolve,reject) => signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError'))))));
    const pending = expect(request('/health')).rejects.toThrow('60 seconds');
    await vi.advanceTimersByTimeAsync(60000);
    await pending;
  });
  it('rejects missing production API configuration instead of using localhost', async () => {
    vi.stubEnv('DEV',false);
    vi.stubEnv('VITE_API_BASE_URL','');
    vi.resetModules();
    const production = await import('./api');
    expect(production.BASE_URL).toBe('');
    await expect(production.request('/health')).rejects.toThrow('Backend URL is not configured');
  });
});
