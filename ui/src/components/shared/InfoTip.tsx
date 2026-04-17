import { HelpCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { INDICATORS } from '@/lib/indicators';
import { cn } from '@/lib/utils/cn';

interface InfoTipProps {
  /** Key into the indicator catalogue. Either provide this or `title`+`body`. */
  indicator?: keyof typeof INDICATORS;
  title?: ReactNode;
  body?: ReactNode;
  /** Optional "Read more" deep link into the Help page. */
  helpHref?: string;
  className?: string;
  iconSize?: number;
  /** Accessible label for screen readers when the trigger is only an icon. */
  label?: string;
}

export function InfoTip({
  indicator,
  title,
  body,
  helpHref,
  className,
  iconSize = 13,
  label,
}: InfoTipProps) {
  const entry = indicator ? INDICATORS[indicator] : undefined;
  const resolvedTitle = title ?? entry?.label;
  const resolvedBody =
    body ??
    (entry ? (
      <>
        <p>{entry.summary}</p>
        <p className="mt-1.5 text-muted-foreground">{entry.detail}</p>
        {entry.interpretation && (
          <p className="mt-1.5">
            <span className="font-medium">How to read it:</span> {entry.interpretation}
          </p>
        )}
      </>
    ) : null);

  const resolvedHref = helpHref ?? (indicator ? `/help#${indicator}` : undefined);
  const ariaLabel = label ?? (typeof resolvedTitle === 'string' ? `${resolvedTitle} help` : 'More info');

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={ariaLabel}
          className={cn(
            'inline-flex size-4 items-center justify-center rounded-full text-muted-foreground/70 transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            className,
          )}
        >
          <HelpCircle style={{ width: iconSize, height: iconSize }} />
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" align="start" className="max-w-sm">
        {resolvedTitle && (
          <div className="mb-1 text-xs font-semibold tracking-tight">{resolvedTitle}</div>
        )}
        <div className="text-[11px] leading-relaxed text-foreground">{resolvedBody}</div>
        {resolvedHref && (
          <Link
            to={resolvedHref}
            className="mt-2 inline-block text-[11px] font-medium text-primary hover:underline"
          >
            Learn more →
          </Link>
        )}
      </TooltipContent>
    </Tooltip>
  );
}
