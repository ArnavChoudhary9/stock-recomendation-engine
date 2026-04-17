import { useEffect, useRef } from 'react';
import { MessageSquare } from 'lucide-react';
import { EmptyState } from '@/components/shared/EmptyState';
import { ChatMessage } from './ChatMessage';
import type { ChatMessage as Msg } from '@/lib/types';

interface ChatThreadProps {
  messages: Msg[];
  streamingMessageId: string | null;
}

export function ChatThread({ messages, streamingMessageId }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages + streaming deltas.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, streamingMessageId]);

  if (messages.length === 0) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="Start a conversation"
        description="Ask about a stock, a signal, or compare tickers. Add a symbol as context to scope the conversation."
      />
    );
  }

  return (
    <div className="space-y-6">
      {messages.map((m) => (
        <ChatMessage key={m.id} message={m} streaming={streamingMessageId === m.id} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
