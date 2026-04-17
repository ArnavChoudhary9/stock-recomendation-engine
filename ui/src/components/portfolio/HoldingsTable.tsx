import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScoreRing } from '@/components/shared/ScoreRing';
import { cn } from '@/lib/utils/cn';
import { formatCurrency } from '@/lib/utils/format';
import type { Holding } from '@/lib/types';

interface HoldingsTableProps {
  holdings: Holding[];
  scoreOverlay?: Record<string, number>;
}

export function HoldingsTable({ holdings, scoreOverlay = {} }: HoldingsTableProps) {
  if (holdings.length === 0) {
    return (
      <p className="rounded-md border bg-muted/20 px-4 py-6 text-center text-sm text-muted-foreground">
        No holdings yet.
      </p>
    );
  }

  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead className="text-right">Avg</TableHead>
            <TableHead className="text-right">LTP</TableHead>
            <TableHead className="text-right">P&amp;L</TableHead>
            <TableHead className="text-right">Day</TableHead>
            <TableHead className="text-center">Score</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {holdings.map((h) => {
            const score = scoreOverlay[h.symbol];
            const pnlTone =
              h.pnl > 0 ? 'text-[hsl(var(--success))]' : h.pnl < 0 ? 'text-destructive' : '';
            const dayTone =
              h.day_change > 0
                ? 'text-[hsl(var(--success))]'
                : h.day_change < 0
                  ? 'text-destructive'
                  : '';
            return (
              <TableRow key={h.symbol}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/stocks/${h.symbol}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {h.symbol}
                    </Link>
                    <Badge variant="outline">{h.exchange}</Badge>
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">{h.quantity}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(h.average_price)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(h.last_price)}
                </TableCell>
                <TableCell className={cn('text-right font-medium tabular-nums', pnlTone)}>
                  <div>{formatCurrency(h.pnl)}</div>
                  <div className="text-xs opacity-80">
                    {h.pnl_pct >= 0 ? '+' : ''}
                    {h.pnl_pct.toFixed(2)}%
                  </div>
                </TableCell>
                <TableCell className={cn('text-right tabular-nums', dayTone)}>
                  <div>{formatCurrency(h.day_change)}</div>
                  <div className="text-xs opacity-80">
                    {h.day_change_pct >= 0 ? '+' : ''}
                    {h.day_change_pct.toFixed(2)}%
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  {score !== undefined ? (
                    <ScoreRing score={score} size={36} strokeWidth={4} />
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
