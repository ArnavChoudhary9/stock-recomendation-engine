import { useNavigate } from 'react-router-dom';
import {
  Briefcase,
  LayoutDashboard,
  LineChart,
  ListOrdered,
  MessageSquare,
  Plus,
  Settings as SettingsIcon,
  Star,
} from 'lucide-react';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { useStocks } from '@/features/stocks/useStocks';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/stocks', label: 'Stocks', icon: LineChart },
  { to: '/stocks/manage', label: 'Add / backfill symbols', icon: Plus },
  { to: '/watchlist', label: 'Watchlist', icon: Star },
  { to: '/recommendations', label: 'Recommendations', icon: ListOrdered },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
] as const;

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { data } = useStocks({ limit: 500 });
  const stocks = data?.data ?? [];

  function go(to: string) {
    onOpenChange(false);
    navigate(to);
  }

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search stocks or jump to a page…" />
      <CommandList>
        <CommandEmpty>No results.</CommandEmpty>

        <CommandGroup heading="Navigate">
          {NAV.map((item) => (
            <CommandItem key={item.to} onSelect={() => go(item.to)}>
              <item.icon />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>

        {stocks.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Jump to stock">
              {stocks.slice(0, 50).map((s) => (
                <CommandItem
                  key={s.symbol}
                  value={`${s.symbol} ${s.name}`}
                  onSelect={() => go(`/stocks/${s.symbol}`)}
                >
                  <LineChart />
                  <span className="font-medium">{s.symbol}</span>
                  <span className="truncate text-muted-foreground">{s.name}</span>
                  {s.sector && (
                    <span className="ml-auto text-xs text-muted-foreground">{s.sector}</span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}

