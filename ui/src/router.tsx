import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { Dashboard } from '@/routes/Dashboard';
import { Stocks } from '@/routes/Stocks';
import { StockDetail } from '@/routes/StockDetail';
import { Recommendations } from '@/routes/Recommendations';
import { Portfolio } from '@/routes/Portfolio';
import { Chat } from '@/routes/Chat';
import { Settings } from '@/routes/Settings';
import { NotFound } from '@/routes/NotFound';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'stocks', element: <Stocks /> },
      { path: 'stocks/:symbol', element: <StockDetail /> },
      { path: 'recommendations', element: <Recommendations /> },
      { path: 'portfolio', element: <Portfolio /> },
      { path: 'chat', element: <Chat /> },
      { path: 'settings', element: <Settings /> },
      { path: '404', element: <NotFound /> },
      { path: '*', element: <Navigate to="/404" replace /> },
    ],
  },
]);
