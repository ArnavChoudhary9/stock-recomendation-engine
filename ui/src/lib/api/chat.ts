import { APIError, NetworkError } from '@/lib/api/errors';
import { endpoints } from '@/lib/api/endpoints';
import type { APIErrorEnvelope, ChatMessage } from '@/lib/types';

const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

interface ChatRequestBody {
  messages: Array<{ role: ChatMessage['role']; content: string }>;
  context_symbols: string[];
}

interface StreamCallbacks {
  onDelta: (delta: string) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
  signal?: AbortSignal;
}

// Expected server wire format: newline-delimited JSON, one object per line.
//   { "delta": "partial text" }
//   { "done": true }
//   { "error": "..." }
// SSE-style `data: <json>\n\n` is also accepted — we strip the prefix.
export async function streamChat(body: ChatRequestBody, cb: StreamCallbacks): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${endpoints.chatStream}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
      signal: cb.signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') return;
    throw new NetworkError(err instanceof Error ? err.message : 'chat request failed');
  }

  if (!response.ok || !response.body) {
    // Try to parse our standard APIError envelope. If not JSON, fabricate one.
    let parsed: APIErrorEnvelope | null = null;
    try {
      parsed = (await response.json()) as APIErrorEnvelope;
    } catch {
      /* ignore */
    }
    throw new APIError(response.status, {
      code: parsed?.error.code ?? 'HTTP_ERROR',
      message: parsed?.error.message ?? response.statusText ?? `HTTP ${response.status}`,
    });
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;

      // Consume whole lines; keep the trailing partial in the buffer.
      let newline = buffer.indexOf('\n');
      while (newline !== -1) {
        const raw = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        newline = buffer.indexOf('\n');
        if (!raw) continue;
        const line = raw.startsWith('data:') ? raw.slice(5).trim() : raw;
        if (line === '[DONE]') {
          cb.onDone?.();
          return;
        }
        try {
          const obj = JSON.parse(line) as {
            delta?: string;
            done?: boolean;
            error?: string;
          };
          if (obj.error) throw new Error(obj.error);
          if (obj.delta) cb.onDelta(obj.delta);
          if (obj.done) {
            cb.onDone?.();
            return;
          }
        } catch (e) {
          if ((e as Error).message) throw e;
        }
      }
    }
    // Stream ended without an explicit [DONE] sentinel — still succeed.
    cb.onDone?.();
  } catch (err) {
    if ((err as Error).name === 'AbortError') return;
    cb.onError?.(err as Error);
    throw err;
  } finally {
    reader.releaseLock();
  }
}
