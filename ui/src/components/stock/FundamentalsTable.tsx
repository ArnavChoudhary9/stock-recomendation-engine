import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCompact, formatPercent } from '@/lib/utils/format';
import type { Fundamentals } from '@/lib/types';

interface FundamentalsTableProps {
  fundamentals: Fundamentals | null;
}

export function FundamentalsTable({ fundamentals }: FundamentalsTableProps) {
  if (!fundamentals) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fundamentals</CardTitle>
          <CardDescription>No fundamentals on record yet.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const rows: Array<{ label: string; value: string }> = [
    { label: 'P/E', value: fundamentals.pe !== null ? fundamentals.pe.toFixed(2) : '—' },
    { label: 'Market cap', value: formatCompact(fundamentals.market_cap) },
    {
      label: 'ROE',
      value:
        fundamentals.roe !== null ? formatPercent(fundamentals.roe) : '—',
    },
    { label: 'EPS', value: fundamentals.eps !== null ? fundamentals.eps.toFixed(2) : '—' },
    {
      label: 'Debt / equity',
      value: fundamentals.debt_equity !== null ? fundamentals.debt_equity.toFixed(2) : '—',
    },
    {
      label: 'Promoter holding',
      value: formatPercent(fundamentals.promoter_holding),
    },
    {
      label: 'Dividend yield',
      value: formatPercent(fundamentals.dividend_yield),
    },
    { label: 'As of', value: fundamentals.date },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Fundamentals</CardTitle>
        <CardDescription>Latest recorded snapshot</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-2 sm:grid-cols-2">
          {rows.map((r) => (
            <div
              key={r.label}
              className="flex items-center justify-between rounded-md border bg-muted/20 px-3 py-2 text-sm"
            >
              <dt className="text-muted-foreground">{r.label}</dt>
              <dd className="font-medium">{r.value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
