import { QueryClient, QueryClientProvider as TanStackQueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ReactNode } from 'react';
import { extractApiError } from '../api/errors/errorUtils';

// Crear QueryClient con configuración por defecto y manejo global de errores
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutos
      retry: (failureCount, error) => {
        // No reintentar en errores de autenticación/autorización
        const apiError = extractApiError(error);
        if (apiError.isAuthenticationError() || apiError.isAuthorizationError()) {
          return false;
        }
        // Reintentar hasta 2 veces para otros errores
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false, // No reintentar mutations por defecto
    },
  },
});

interface QueryClientProviderProps {
  children: ReactNode;
}

/**
 * QueryClientProvider - Provider de TanStack Query
 * Envuelve la aplicación y proporciona el QueryClient
 */
export function QueryClientProvider({ children }: QueryClientProviderProps) {
  return (
    <TanStackQueryClientProvider client={queryClient}>
      {children}
      {import.meta.env.VITE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </TanStackQueryClientProvider>
  );
}
