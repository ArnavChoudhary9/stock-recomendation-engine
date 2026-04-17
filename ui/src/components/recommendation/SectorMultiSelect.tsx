import { Check, Filter, X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils/cn';
import { useState } from 'react';

interface SectorMultiSelectProps {
  options: string[];
  value: string[];
  onChange: (next: string[]) => void;
}

export function SectorMultiSelect({ options, value, onChange }: SectorMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>(value);

  function toggle(sector: string) {
    setDraft((prev) =>
      prev.includes(sector) ? prev.filter((s) => s !== sector) : [...prev, sector],
    );
  }

  function apply() {
    onChange(draft);
    setOpen(false);
  }

  function clear() {
    setDraft([]);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) setDraft(value);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="default" className="justify-between gap-2">
          <span className="inline-flex items-center gap-2">
            <Filter className="size-4" />
            Sectors
          </span>
          {value.length > 0 ? (
            <span className="inline-flex size-5 items-center justify-center rounded-full bg-primary text-[10px] font-medium text-primary-foreground">
              {value.length}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">All</span>
          )}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Filter by sector</DialogTitle>
          <DialogDescription>Leave empty to include every sector.</DialogDescription>
        </DialogHeader>

        <div className="max-h-80 overflow-y-auto rounded-md border">
          {options.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">No sectors available.</div>
          ) : (
            <ul className="divide-y">
              {options.map((sector) => {
                const active = draft.includes(sector);
                return (
                  <li key={sector}>
                    <button
                      type="button"
                      onClick={() => toggle(sector)}
                      className={cn(
                        'flex w-full items-center justify-between px-3 py-2 text-sm transition-colors hover:bg-accent',
                        active && 'bg-accent/50',
                      )}
                    >
                      <span>{sector}</span>
                      {active && <Check className="size-4 text-primary" />}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={clear} disabled={draft.length === 0}>
            <X /> Clear
          </Button>
          <Button onClick={apply}>Apply</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
