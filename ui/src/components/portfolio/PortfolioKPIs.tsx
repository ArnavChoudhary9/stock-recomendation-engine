import { ArrowDownRight, ArrowUpRight, TrendingUp, Wallet } from 'lucide-react';
import { StatCard } from '@/components/shared/StatCard';
import { formatCurrency, formatPercent } from '@/lib/utils/format';
import type { PortfolioOverview } from '@/lib/types';

interface PortfolioKPIsProps {
  overview: PortfolioOverview;
}

export function PortfolioKPIs({ overview }: PortfolioKPIsProps) {
  const pnlTrend = overview.total_pnl > 0 ? 'up' : overview.total_pnl < 0 ? 'down' : 'neutral';
  const dayTrend = overview.day_pnl > 0 ? 'up' : overview.day_pnl < 0 ? 'down' : 'neutral';
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Invested"
        value={formatCurrency(overview.total_investment)}
        icon={Wallet}
      />
      <StatCard
        label="Current value"
        value={formatCurrency(overview.current_value)}
        icon={TrendingUp}
      />
      <StatCard
        label="Total P&L"
        value={formatCurrency(overview.total_pnl)}
        hint={formatPercent(overview.total_pnl_pct / 100, true)}
        icon={overview.total_pnl >= 0 ? ArrowUpRight : ArrowDownRight}
        trend={pnlTrend}
      />
      <StatCard
        label="Day P&L"
        value={formatCurrency(overview.day_pnl)}
        hint="since yesterday's close"
        icon={overview.day_pnl >= 0 ? ArrowUpRight : ArrowDownRight}
        trend={dayTrend}
      />
    </div>
  );
}
