import type { ErrorDetail } from '@/lib/types';

export class APIError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown> | null;

  constructor(status: number, detail: ErrorDetail) {
    super(detail.message);
    this.name = 'APIError';
    this.status = status;
    this.code = detail.code;
    this.details = detail.details ?? null;
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}
