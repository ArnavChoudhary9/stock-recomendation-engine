import { AlertTriangle } from 'lucide-react';

interface ConcentrationWarningsProps {
  warnings: string[];
}

export function ConcentrationWarnings({ warnings }: ConcentrationWarningsProps) {
  if (warnings.length === 0) return null;
  return (
    <div className="flex items-start gap-3 rounded-md border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 px-4 py-3 text-sm">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[hsl(var(--warning))]" />
      <div className="min-w-0 space-y-1">
        <div className="font-medium text-foreground">Concentration risk</div>
        <ul className="space-y-0.5 text-muted-foreground">
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
