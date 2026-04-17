import { APIError, NetworkError } from '@/lib/api/errors';
import type { APIErrorEnvelope, APIResponse, PaginatedResponse } from '@/lib/types';

// In dev, VITE_API_BASE_URL is empty and the Vite proxy routes /api/* to :8000.
// In prod (served by FastAPI), it's also empty because the API is same-origin.
const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

type BodyShape<T> =
  | APIResponse<T>
  | PaginatedResponse<T extends readonly (infer U)[] ? U : never>
  | APIErrorEnvelope;

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(path: string, params?: RequestOptions['params']) {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, headers, ...rest } = options;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    throw new NetworkError(err instanceof Error ? err.message : 'network request failed');
  }

  let parsed: BodyShape<T> | undefined;
  try {
    parsed = (await response.json()) as BodyShape<T>;
  } catch {
    // Non-JSON response body — surface the status as a generic error.
    if (!response.ok) {
      throw new APIError(response.status, {
        code: 'HTTP_ERROR',
        message: response.statusText || `HTTP ${response.status}`,
      });
    }
    throw new NetworkError('expected JSON response');
  }

  if (!response.ok || (parsed as APIErrorEnvelope).error !== undefined) {
    const envelope = parsed as APIErrorEnvelope;
    throw new APIError(response.status, envelope.error);
  }

  // Both APIResponse and PaginatedResponse have a `data` key. Caller picks the shape.
  return (parsed as APIResponse<T>).data;
}

// Paginated variant that also returns pagination metadata.
async function requestPaginated<T>(
  path: string,
  options: RequestOptions = {},
): Promise<PaginatedResponse<T>> {
  const { body, params, headers, ...rest } = options;
  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    throw new NetworkError(err instanceof Error ? err.message : 'network request failed');
  }

  const parsed = (await response.json()) as PaginatedResponse<T> | APIErrorEnvelope;
  if (!response.ok || (parsed as APIErrorEnvelope).error !== undefined) {
    throw new APIError(response.status, (parsed as APIErrorEnvelope).error);
  }
  return parsed as PaginatedResponse<T>;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'GET' }),
  getPaginated: <T>(path: string, options?: RequestOptions) =>
    requestPaginated<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'DELETE' }),
};
