import { useState } from 'react';
import type { OverlayKey } from './PriceChart';

export function useOverlayState(initial?: Partial<Record<OverlayKey, boolean>>) {
  const [overlays, setOverlays] = useState<Partial<Record<OverlayKey, boolean>>>(
    initial ?? { sma20: true, sma50: true, sma200: true },
  );
  const toggle = (key: OverlayKey) =>
    setOverlays((prev) => ({ ...prev, [key]: !prev[key] }));
  // Group toggle flips all keys to the inverse of the current "all-on" state.
  const toggleGroup = (keys: readonly OverlayKey[]) =>
    setOverlays((prev) => {
      const allOn = keys.every((k) => prev[k] ?? false);
      const next = { ...prev };
      for (const k of keys) next[k] = !allOn;
      return next;
    });
  return { overlays, toggle, toggleGroup, setOverlays };
}
