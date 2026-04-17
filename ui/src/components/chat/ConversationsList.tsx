import { MessageSquarePlus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useChatStore } from '@/store/chat';
import { cn } from '@/lib/utils/cn';

export function ConversationsList() {
  const conversations = useChatStore((s) => s.conversations);
  const activeId = useChatStore((s) => s.activeId);
  const createConversation = useChatStore((s) => s.createConversation);
  const setActive = useChatStore((s) => s.setActive);
  const deleteConversation = useChatStore((s) => s.deleteConversation);

  return (
    <aside className="flex h-full min-h-0 w-60 shrink-0 flex-col rounded-lg border bg-card">
      <div className="border-b p-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start"
          onClick={() => createConversation()}
        >
          <MessageSquarePlus className="size-4" /> New chat
        </Button>
      </div>
      <ol className="min-h-0 flex-1 space-y-0.5 overflow-y-auto p-2">
        {conversations.length === 0 && (
          <li className="rounded-md px-2 py-4 text-center text-xs text-muted-foreground">
            No conversations yet.
          </li>
        )}
        {conversations.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => setActive(c.id)}
              className={cn(
                'group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors',
                c.id === activeId
                  ? 'bg-accent text-accent-foreground'
                  : 'text-foreground/80 hover:bg-accent/50',
              )}
            >
              <span className="min-w-0 flex-1 truncate">{c.title}</span>
              <Button
                asChild
                variant="ghost"
                size="icon"
                className="size-6 opacity-0 group-hover:opacity-100"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(c.id);
                }}
                aria-label={`Delete ${c.title}`}
              >
                <span>
                  <Trash2 className="size-3" />
                </span>
              </Button>
            </button>
          </li>
        ))}
      </ol>
    </aside>
  );
}
