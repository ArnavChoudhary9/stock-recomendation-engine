import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage, Conversation } from '@/lib/types';

interface ChatState {
  conversations: Conversation[];
  activeId: string | null;
  contextSymbols: string[];

  createConversation: () => string;
  deleteConversation: (id: string) => void;
  setActive: (id: string | null) => void;
  renameConversation: (id: string, title: string) => void;

  appendMessage: (conversationId: string, message: ChatMessage) => void;
  // Replace the last assistant message's content (used to accumulate streaming deltas).
  appendDelta: (conversationId: string, delta: string) => void;
  setMessageError: (conversationId: string, messageId: string, error: string) => void;

  addContextSymbol: (symbol: string) => void;
  removeContextSymbol: (symbol: string) => void;
  clearContextSymbols: () => void;
}

function now() {
  return new Date().toISOString();
}

function makeId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      conversations: [],
      activeId: null,
      contextSymbols: [],

      createConversation: () => {
        const id = makeId();
        const convo: Conversation = {
          id,
          title: 'New chat',
          messages: [],
          created_at: now(),
          updated_at: now(),
        };
        set((s) => ({
          conversations: [convo, ...s.conversations],
          activeId: id,
        }));
        return id;
      },

      deleteConversation: (id) =>
        set((s) => {
          const remaining = s.conversations.filter((c) => c.id !== id);
          const activeId =
            s.activeId === id ? (remaining[0]?.id ?? null) : s.activeId;
          return { conversations: remaining, activeId };
        }),

      setActive: (id) => set({ activeId: id }),

      renameConversation: (id, title) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === id ? { ...c, title, updated_at: now() } : c,
          ),
        })),

      appendMessage: (conversationId, message) =>
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== conversationId) return c;
            // Auto-title from the first user message.
            const title =
              c.messages.length === 0 && message.role === 'user'
                ? message.content.slice(0, 40).trim() || c.title
                : c.title;
            return {
              ...c,
              title,
              messages: [...c.messages, message],
              updated_at: now(),
            };
          }),
        })),

      appendDelta: (conversationId, delta) =>
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== conversationId) return c;
            const messages = [...c.messages];
            const last = messages[messages.length - 1];
            if (!last || last.role !== 'assistant') return c;
            messages[messages.length - 1] = { ...last, content: last.content + delta };
            return { ...c, messages, updated_at: now() };
          }),
        })),

      setMessageError: (conversationId, messageId, error) =>
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== conversationId) return c;
            return {
              ...c,
              messages: c.messages.map((m) => (m.id === messageId ? { ...m, error } : m)),
              updated_at: now(),
            };
          }),
        })),

      addContextSymbol: (symbol) =>
        set((s) => {
          const up = symbol.trim().toUpperCase();
          if (!up || s.contextSymbols.includes(up)) return s;
          return { contextSymbols: [...s.contextSymbols, up] };
        }),

      removeContextSymbol: (symbol) =>
        set((s) => ({
          contextSymbols: s.contextSymbols.filter((x) => x !== symbol),
        })),

      clearContextSymbols: () => set({ contextSymbols: [] }),
    }),
    {
      name: 'stock-ui-chat',
      // Only persist conversations + active id, not transient context.
      partialize: (s) => ({
        conversations: s.conversations,
        activeId: s.activeId,
      }),
    },
  ),
);

export function makeMessageId() {
  return makeId();
}
