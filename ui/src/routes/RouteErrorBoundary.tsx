import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom';
import { AlertTriangle, Home, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { APIError } from '@/lib/api/errors';

export function RouteErrorBoundary() {
  const error = useRouteError();

  const { title, message } = describeError(error);

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="max-w-md space-y-4 text-center">
        <div className="mx-auto inline-flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertTriangle className="size-6" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="text-sm text-muted-foreground">{message}</p>
        <div className="flex justify-center gap-2">
          <Button onClick={() => window.location.reload()}>
            <RefreshCw className="size-4" /> Try again
          </Button>
          <Button variant="outline" asChild>
            <Link to="/">
              <Home className="size-4" /> Dashboard
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

function describeError(error: unknown): { title: string; message: string } {
  if (isRouteErrorResponse(error)) {
    return {
      title: `${error.status} ${error.statusText}`,
      message: typeof error.data === 'string' ? error.data : 'This page failed to load.',
    };
  }
  if (error instanceof APIError) {
    return { title: `API error ${error.status}`, message: error.message };
  }
  if (error instanceof Error) {
    return { title: 'Something went wrong', message: error.message };
  }
  return { title: 'Something went wrong', message: 'Unknown error.' };
}
