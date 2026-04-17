import { APIError } from './errors';

// Phase 4B portfolio endpoints return 501 NOT_IMPLEMENTED. Chat endpoint
// doesn't exist yet and returns 404 until a streaming responder is wired up.
// Either case is a feature-not-available signal — callers render a
// first-class "coming soon" state instead of an error toast.
export function isNotImplemented(err: unknown): boolean {
  if (!(err instanceof APIError)) return false;
  return err.status === 501 || err.status === 404 || err.code === 'NOT_IMPLEMENTED';
}
