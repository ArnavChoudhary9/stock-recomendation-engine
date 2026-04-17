import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface PipelineState {
  lastTriggeredAt: string | null;
  lastCompletedAt: string | null;
  symbolsCount: number | null;
  isRunning: boolean;
  markTriggered: (symbolsCount: number) => void;
  markCompleted: () => void;
}

const STORAGE_KEY = 'pipeline-status-v1';

export const usePipelineStore = create<PipelineState>()(
  persist(
    (set) => ({
      lastTriggeredAt: null,
      lastCompletedAt: null,
      symbolsCount: null,
      isRunning: false,
      markTriggered: (symbolsCount) =>
        set({
          lastTriggeredAt: new Date().toISOString(),
          symbolsCount,
          isRunning: true,
        }),
      markCompleted: () =>
        set({
          lastCompletedAt: new Date().toISOString(),
          isRunning: false,
        }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (s) => ({
        lastTriggeredAt: s.lastTriggeredAt,
        lastCompletedAt: s.lastCompletedAt,
        symbolsCount: s.symbolsCount,
      }),
    },
  ),
);
