import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../config';
import { ServiceLogsResponse } from '../../core/ports';

export interface UseServiceLogsReturn {
  logs: ServiceLogsResponse | null;
  loading: boolean;
  error: string | null;
}

/**
 * Polling en vivo (~3s) de los logs de un servicio de la plataforma.
 * `enabled` debe ser false cuando el panel está cerrado para no pedir en balde.
 */
export function useServiceLogs(
  service: string | undefined,
  enabled: boolean,
  tail = 200
): UseServiceLogsReturn {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['serviceLogs', service ?? 'none', tail],
    queryFn: () => {
      if (!service) throw new Error('Service is required');
      return apiClient.getServiceLogs(service, tail);
    },
    enabled: enabled && !!service,
    staleTime: 0,
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  return {
    logs: data ?? null,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar logs del servicio' : null,
  };
}
