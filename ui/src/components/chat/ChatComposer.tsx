import { useEffect, useRef, useState } from 'react';
import { Plus, Send, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StockContextChip } from './StockContextChip';
import { useChatStore } from '@/store/chat';
import { cn } from '@/lib/utils/cn';

interface ChatComposerProps {
  disabled?: boolean;
  streaming?: boolean;
  onSubmit: (text: string) => void;
  onStop?: () => void;
  className?: string;
}

export function ChatComposer({
  disabled,
  streaming,
  onSubmit,
  onStop,
  className,
}: ChatComposerProps) {
  const [text, setText] = useState('');
  const [newSymbol, setNewSymbol] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const contextSymbols = useChatStore((s) => s.contextSymbols);
  const addContextSymbol = useChatStore((s) => s.addContextSymbol);
  const removeContextSymbol = useChatStore((s) => s.removeContextSymbol);

  useEffect(() => {
    taRef.current?.focus();
  }, []);

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setText('');
  }

  function onKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function addSymbolFromInput() {
    if (newSymbol.trim()) {
      addContextSymbol(newSymbol);
      setNewSymbol('');
      setShowAdd(false);
    }
  }

  return (
    <div className={cn('space-y-2 rounded-lg border bg-card p-3', className)}>
      <div className="flex flex-wrap items-center gap-1.5">
        {contextSymbols.map((s) => (
          <StockContextChip
            key={s}
            symbol={s}
            onRemove={() => removeContextSymbol(s)}
          />
        ))}
        {showAdd ? (
          <div className="inline-flex items-center gap-1">
            <Input
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addSymbolFromInput();
                }
                if (e.key === 'Escape') setShowAdd(false);
              }}
              placeholder="RELIANCE"
              className="h-7 w-28 text-xs"
              autoFocus
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={addSymbolFromInput}
            >
              Add
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => setShowAdd(true)}
          >
            <Plus className="size-3" /> Add symbol
          </Button>
        )}
      </div>

      <div className="flex items-end gap-2">
        <textarea
          ref={taRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          disabled={disabled}
          placeholder="Ask about a stock, a signal, or the market…"
          rows={2}
          className="flex min-h-[44px] w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        />
        {streaming ? (
          <Button type="button" variant="outline" onClick={onStop} aria-label="Stop generating">
            <Square className="size-4" />
          </Button>
        ) : (
          <Button
            type="button"
            onClick={submit}
            disabled={disabled || !text.trim()}
            aria-label="Send message"
          >
            <Send className="size-4" />
          </Button>
        )}
      </div>
      <p className="text-[11px] text-muted-foreground">
        Enter to send · Shift + Enter for a newline
      </p>
    </div>
  );
}
