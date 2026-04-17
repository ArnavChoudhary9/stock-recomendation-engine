import { Link2, Link2Off, Clock, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { isNotImplemented } from '@/lib/api/isNotImplemented';
import { useKiteAuthUrl, useKiteStatus } from '@/features/portfolio/useKite';
import { cn } from '@/lib/utils/cn';

export function KiteConnectBanner() {
  const { data, isLoading, isError, error, refetch } = useKiteStatus();
  const authUrl = useKiteAuthUrl();

  // Phase 4B pending — show friendly notice, no actions.
  if (isError && isNotImplemented(error)) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex items-center gap-3 py-4 text-sm">
          <Clock className="size-4 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <div className="font-medium">Kite integration pending (Phase 4B)</div>
            <div className="text-muted-foreground">
              The UI is ready; backend will expose live holdings and P&amp;L once Phase 4B ships.
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return <Skeleton className="h-16 w-full" />;
  }

  const connected = data?.connected ?? false;
  const expired = data && !connected && data.expires_at;

  return (
    <Card className={cn(connected ? 'border-[hsl(var(--success))]/40' : 'border-dashed')}>
      <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {connected ? (
            <Link2 className="size-4 text-[hsl(var(--success))]" />
          ) : (
            <Link2Off className="size-4 text-muted-foreground" />
          )}
          <div>
            <div className="font-medium">
              {connected ? 'Kite connected' : expired ? 'Kite session expired' : 'Kite not connected'}
              {data?.user_id && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  · {data.user_id}
                </span>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              {connected
                ? 'Live holdings, positions, and P&L are refreshed on demand.'
                : 'Connect your Zerodha account to view holdings with P&L.'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            aria-label="Re-check Kite connection status"
            title="Re-check status"
          >
            <RefreshCw className="size-4" />
          </Button>
          {!connected && (
            <Button
              size="sm"
              onClick={async () => {
                const res = await authUrl.mutateAsync();
                window.location.href = res.url;
              }}
              disabled={authUrl.isPending}
            >
              {authUrl.isPending ? 'Opening…' : 'Connect Kite'}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
