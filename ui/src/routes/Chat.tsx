import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PageHeader } from '@/components/shared/PageHeader';
import { ChatThread } from '@/components/chat/ChatThread';
import { ChatComposer } from '@/components/chat/ChatComposer';
import { ConversationsList } from '@/components/chat/ConversationsList';
import { APIError } from '@/lib/api/errors';
import { isNotImplemented } from '@/lib/api/isNotImplemented';
import { streamChat } from '@/lib/api/chat';
import { makeMessageId, useChatStore } from '@/store/chat';

export function Chat() {
  const [searchParams, setSearchParams] = useSearchParams();
  const conversations = useChatStore((s) => s.conversations);
  const activeId = useChatStore((s) => s.activeId);
  const setActive = useChatStore((s) => s.setActive);
  const createConversation = useChatStore((s) => s.createConversation);
  const contextSymbols = useChatStore((s) => s.contextSymbols);
  const addContextSymbol = useChatStore((s) => s.addContextSymbol);
  const appendMessage = useChatStore((s) => s.appendMessage);
  const appendDelta = useChatStore((s) => s.appendDelta);
  const setMessageError = useChatStore((s) => s.setMessageError);

  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [backendNotAvailable, setBackendNotAvailable] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // If we arrived with ?ctx=SYMBOL, add it to context once.
  useEffect(() => {
    const ctx = searchParams.get('ctx');
    if (ctx) {
      addContextSymbol(ctx);
      searchParams.delete('ctx');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams, addContextSymbol]);

  // Ensure a conversation exists and is active.
  useEffect(() => {
    if (!activeId && conversations.length === 0) {
      createConversation();
    } else if (!activeId && conversations[0]) {
      setActive(conversations[0].id);
    }
  }, [activeId, conversations, createConversation, setActive]);

  const active = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? null,
    [conversations, activeId],
  );

  const send = useCallback(
    async (text: string) => {
      if (!active) return;

      const userMsg = {
        id: makeMessageId(),
        role: 'user' as const,
        content: text,
        created_at: new Date().toISOString(),
        context_symbols: contextSymbols.length > 0 ? [...contextSymbols] : undefined,
      };
      appendMessage(active.id, userMsg);

      const assistantId = makeMessageId();
      appendMessage(active.id, {
        id: assistantId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      });
      setStreamingId(assistantId);

      const controller = new AbortController();
      abortRef.current = controller;

      const history = [...active.messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        await streamChat(
          { messages: history, context_symbols: contextSymbols },
          {
            onDelta: (delta) => appendDelta(active.id, delta),
            signal: controller.signal,
          },
        );
      } catch (err) {
        if (err instanceof APIError && isNotImplemented(err)) {
          setBackendNotAvailable(true);
          setMessageError(
            active.id,
            assistantId,
            "Chat backend isn't wired up yet — the UI is scaffolded and will start streaming once a /api/v1/chat/stream endpoint is available.",
          );
        } else {
          setMessageError(
            active.id,
            assistantId,
            err instanceof Error ? err.message : 'Unknown error',
          );
        }
      } finally {
        setStreamingId(null);
        abortRef.current = null;
      }
    },
    [active, contextSymbols, appendMessage, appendDelta, setMessageError],
  );

  function stop() {
    abortRef.current?.abort();
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Chat"
        description={
          backendNotAvailable
            ? 'UI ready — streaming endpoint pending on the backend.'
            : 'Conversational exploration with stock-context injection.'
        }
      />

      <div className="grid min-h-[70vh] gap-4 md:grid-cols-[240px_1fr]">
        <ConversationsList />

        <div className="flex min-h-0 flex-col gap-3">
          <div className="min-h-[420px] flex-1 overflow-y-auto rounded-lg border bg-background p-4">
            <ChatThread
              messages={active?.messages ?? []}
              streamingMessageId={streamingId}
            />
          </div>

          <ChatComposer
            streaming={streamingId !== null}
            onSubmit={send}
            onStop={stop}
            disabled={!active}
          />
        </div>
      </div>
    </div>
  );
}
