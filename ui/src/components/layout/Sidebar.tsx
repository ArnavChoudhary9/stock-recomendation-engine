import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  LineChart,
  ListOrdered,
  Briefcase,
  MessageSquare,
  Settings as SettingsIcon,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils/cn';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/stocks', label: 'Stocks', icon: LineChart },
  { to: '/recommendations', label: 'Recommendations', icon: ListOrdered },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
];

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 border-r bg-card md:flex md:flex-col">
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <TrendingUp className="size-5 text-primary" />
        <span className="text-sm font-semibold tracking-tight">Stock Intelligence</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
              )
            }
          >
            <item.icon className="size-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t p-3 text-xs text-muted-foreground">v0.1.0 · local only</div>
    </aside>
  );
}
