import { Search } from 'lucide-react';
import { ThemeToggle } from '@/components/shared/ThemeToggle';
import { HealthPill } from '@/components/shared/HealthPill';
import { useCommandPaletteStore } from '@/store/commandPalette';

export function TopBar() {
  const setOpen = useCommandPaletteStore((s) => s.setOpen);
  const isMac =
    typeof navigator !== 'undefined' && /Mac|iPhone|iPad/i.test(navigator.platform);

  return (
    <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background/80 px-6 backdrop-blur">
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group inline-flex w-full max-w-md items-center gap-2 rounded-md border bg-background px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Search className="size-4" />
        <span className="flex-1 truncate">Search stocks or jump to a page…</span>
        <kbd className="hidden rounded border bg-muted px-1.5 py-0.5 text-[10px] font-medium sm:inline-flex">
          {isMac ? '⌘' : 'Ctrl'} K
        </kbd>
      </button>
      <div className="ml-auto flex items-center gap-2">
        <HealthPill />
        <ThemeToggle />
      </div>
    </header>
  );
}
