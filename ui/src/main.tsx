import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryProvider } from '@/providers/QueryProvider';
import { ThemeProvider } from '@/providers/ThemeProvider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { router } from '@/router';
import '@/styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryProvider>
        <TooltipProvider delayDuration={200} skipDelayDuration={80}>
          <RouterProvider router={router} />
        </TooltipProvider>
      </QueryProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
