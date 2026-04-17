import { describe, expect, test, beforeEach, vi, afterEach } from 'vitest';
import { apiClient } from './client';
import { APIError } from './errors';

type Fetch = typeof globalThis.fetch;

function mockResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'content-type': 'application/json' },
    ...init,
  });
}

describe('apiClient', () => {
  let originalFetch: Fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  test('GET unwraps the APIResponse envelope to return just `data`', async () => {
    globalThis.fetch = vi.fn(async () =>
      mockResponse({
        data: { status: 'ok', components: {}, uptime_seconds: 42 },
        meta: { timestamp: '2026-04-17T00:00:00Z', version: 'v1' },
      }),
    ) as Fetch;

    const out = await apiClient.get<{ status: string; uptime_seconds: number }>(
      '/api/v1/health',
    );
    expect(out.status).toBe('ok');
    expect(out.uptime_seconds).toBe(42);
  });

  test('throws APIError carrying status + code when the envelope signals an error', async () => {
    globalThis.fetch = vi.fn(async () =>
      mockResponse(
        {
          error: { code: 'NOT_IMPLEMENTED', message: 'portfolio overview' },
          meta: { timestamp: '2026-04-17T00:00:00Z', version: 'v1' },
        },
        { status: 501 },
      ),
    ) as Fetch;

    await expect(
      apiClient.get('/api/v1/portfolio/overview'),
    ).rejects.toMatchObject({
      name: 'APIError',
      status: 501,
      code: 'NOT_IMPLEMENTED',
    });
  });

  test('APIError instance check works for downstream narrowing', async () => {
    globalThis.fetch = vi.fn(async () =>
      mockResponse(
        { error: { code: 'STOCK_NOT_FOUND', message: 'missing' } },
        { status: 404 },
      ),
    ) as Fetch;

    try {
      await apiClient.get('/api/v1/stocks/NOPE');
      expect.fail('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(APIError);
      if (err instanceof APIError) {
        expect(err.status).toBe(404);
        expect(err.code).toBe('STOCK_NOT_FOUND');
      }
    }
  });
});
