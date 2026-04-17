import { useState } from 'react';
import type { OverlayKey } from './PriceChart';

export function useOverlayState(initial?: Partial<Record<OverlayKey, boolean>>) {
  const [overlays, setOverlays] = useState<Partial<Record<OverlayKey, boolean>>>(
    initial ?? { sma20: true, sma50: true, sma200: true },
  );
  const toggle = (key: OverlayKey) =>
    setOverlays((prev) => ({ ...prev, [key]: !prev[key] }));
  return { overlays, toggle, setOverlays };
}
