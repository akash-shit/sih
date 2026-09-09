import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { router } from './router';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster
        position="bottom-right"
        theme="dark"
        toastOptions={{
          className:
            '!bg-space-950/90 !border !border-white/[0.12] !text-text-primary !shadow-glass !backdrop-blur-xl !font-mono !text-xs',
        }}
      />
    </QueryClientProvider>
  );
};
