import { useState } from 'react';
import { AlertTriangle, Check, Copy, User, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ReportMarkdown } from '@/components/report/ReportMarkdown';
import { TypingIndicator } from './TypingIndicator';
import { StockContextChip } from './StockContextChip';
import { cn } from '@/lib/utils/cn';
import type { ChatMessage as Msg } from '@/lib/types';

interface ChatMessageProps {
  message: Msg;
  streaming?: boolean;
}

export function ChatMessage({ message, streaming }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  async function copy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard denied */
    }
  }

  return (
    <article
      className={cn(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row',
      )}
    >
      <div
        className={cn(
          'flex size-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary/10 text-primary' : 'bg-muted text-foreground',
        )}
        aria-hidden
      >
        {isUser ? <User className="size-4" /> : <Sparkles className="size-4" />}
      </div>

      <div className={cn('min-w-0 max-w-[85%] space-y-1.5', isUser && 'text-right')}>
        {message.context_symbols && message.context_symbols.length > 0 && (
          <div
            className={cn(
              'flex flex-wrap gap-1',
              isUser && 'justify-end',
            )}
          >
            {message.context_symbols.map((s) => (
              <StockContextChip key={s} symbol={s} />
            ))}
          </div>
        )}

        <div
          className={cn(
            'inline-block rounded-lg px-3 py-2 text-sm text-left',
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'border bg-card text-foreground',
          )}
        >
          {message.content ? (
            <ReportMarkdown>{message.content}</ReportMarkdown>
          ) : streaming ? (
            <TypingIndicator />
          ) : (
            <span className="text-muted-foreground">(empty)</span>
          )}
        </div>

        {message.error && (
          <div className="inline-flex items-center gap-1 rounded-md border border-destructive/40 bg-destructive/10 px-2 py-1 text-xs text-destructive">
            <AlertTriangle className="size-3" />
            {message.error}
          </div>
        )}

        {!streaming && message.content && (
          <div className={cn('flex items-center gap-1 text-xs text-muted-foreground', isUser && 'justify-end')}>
            <Button
              variant="ghost"
              size="icon"
              className="size-6"
              onClick={copy}
              title="Copy"
              aria-label="Copy message"
            >
              {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
            </Button>
            <time dateTime={message.created_at}>
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </time>
          </div>
        )}
      </div>
    </article>
  );
}
