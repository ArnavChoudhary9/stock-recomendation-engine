import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils/cn';

// Generated palette — HSL-evenly spaced so sectors have distinct hues.
const PALETTE = [
  'hsl(217 91% 60%)',
  'hsl(142 70% 45%)',
  'hsl(37 92% 50%)',
  'hsl(262 83% 58%)',
  'hsl(173 80% 40%)',
  'hsl(0 84% 60%)',
  'hsl(292 76% 60%)',
  'hsl(47 95% 53%)',
  'hsl(197 91% 58%)',
  'hsl(310 70% 55%)',
];

interface AllocationPieProps {
  allocation: Record<string, number>; // label → fraction 0..1
  title?: string;
  description?: string;
  className?: string;
}

export function AllocationPie({
  allocation,
  title = 'Allocation',
  description = 'By sector weight',
  className,
}: AllocationPieProps) {
  const entries = Object.entries(allocation)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a);

  const data = entries.map(([name, value], i) => ({
    name,
    value: value * 100,
    fill: PALETTE[i % PALETTE.length],
  }));

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No allocation data yet.
          </p>
        ) : (
          <div className="flex flex-col items-center gap-6 lg:flex-row">
            <div className="h-[220px] w-full max-w-[280px]">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={data}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={56}
                    outerRadius={90}
                    paddingAngle={2}
                    stroke="hsl(var(--background))"
                    strokeWidth={2}
                  >
                    {data.map((d) => (
                      <Cell key={d.name} fill={d.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    cursor={false}
                    contentStyle={{
                      background: 'hsl(var(--popover))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: 6,
                      fontSize: 12,
                    }}
                    labelStyle={{ color: 'hsl(var(--foreground))' }}
                    itemStyle={{ color: 'hsl(var(--foreground))' }}
                    formatter={(v: number) => [`${v.toFixed(1)}%`, 'Weight']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="min-w-0 flex-1 space-y-1.5 text-sm">
              {data.map((d) => (
                <li
                  key={d.name}
                  className="flex items-center justify-between gap-2 rounded-md border bg-muted/20 px-3 py-1.5"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span
                      className="size-2.5 shrink-0 rounded-sm"
                      style={{ backgroundColor: d.fill }}
                      aria-hidden
                    />
                    <span className="truncate">{d.name}</span>
                  </span>
                  <span className="shrink-0 font-medium tabular-nums">
                    {d.value.toFixed(1)}%
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
