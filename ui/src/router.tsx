import type { ComponentType } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { Dashboard } from '@/routes/Dashboard';
import { Stocks } from '@/routes/Stocks';
import { NotFound } from '@/routes/NotFound';
import { RouteErrorBoundary } from '@/routes/RouteErrorBoundary';

// React Router v6 `lazy` takes an async importer that returns `{ Component }`.
// Heavier routes (chart libs, markdown, Recharts) become on-demand chunks —
// Dashboard and Stocks stay eager so the first paint is fast.
function lazyRoute<K extends string>(
  importer: () => Promise<Record<K, ComponentType>>,
  key: K,
) {
  return async () => ({ Component: (await importer())[key] });
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    errorElement: <RouteErrorBoundary />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'stocks', element: <Stocks /> },
      {
        path: 'stocks/manage',
        lazy: lazyRoute(() => import('@/routes/ManageStocks'), 'ManageStocks'),
      },
      {
        path: 'stocks/:symbol',
        lazy: lazyRoute(() => import('@/routes/StockDetail'), 'StockDetail'),
      },
      {
        path: 'watchlist',
        lazy: lazyRoute(() => import('@/routes/Watchlist'), 'Watchlist'),
      },
      {
        path: 'recommendations',
        lazy: lazyRoute(() => import('@/routes/Recommendations'), 'Recommendations'),
      },
      {
        path: 'recommendations/history',
        lazy: lazyRoute(
          () => import('@/routes/RecommendationsHistory'),
          'RecommendationsHistory',
        ),
      },
      {
        path: 'portfolio',
        lazy: lazyRoute(() => import('@/routes/Portfolio'), 'Portfolio'),
      },
      {
        path: 'portfolio/alerts',
        lazy: lazyRoute(() => import('@/routes/Alerts'), 'Alerts'),
      },
      {
        path: 'chat',
        lazy: lazyRoute(() => import('@/routes/Chat'), 'Chat'),
      },
      {
        path: 'settings',
        lazy: lazyRoute(() => import('@/routes/Settings'), 'Settings'),
      },
      {
        path: 'help',
        lazy: lazyRoute(() => import('@/routes/Help'), 'Help'),
      },
      { path: '404', element: <NotFound /> },
      { path: '*', element: <Navigate to="/404" replace /> },
    ],
  },
]);
