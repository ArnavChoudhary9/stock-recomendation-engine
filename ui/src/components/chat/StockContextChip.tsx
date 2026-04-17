import { TrendingUp, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils/cn';

interface StockContextChipProps {
  symbol: string;
  onRemove?: () => void;
  className?: string;
}

export function StockContextChip({ symbol, onRemove, className }: StockContextChipProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary',
        className,
      )}
    >
      <TrendingUp className="size-3" />
      {symbol}
      {onRemove && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onRemove}
          className="size-4 rounded-full p-0 hover:bg-primary/20"
          aria-label={`Remove ${symbol} from context`}
        >
          <X className="size-3" />
        </Button>
      )}
    </span>
  );
}
