import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../config';
import { DeviceLogsResponse } from '../../core/ports';

export interface UseDeviceLogsReturn {
  logs: DeviceLogsResponse | null;
  loading: boolean;
  error: string | null;
}

export function useDeviceLogs(deviceId: string | undefined): UseDeviceLogsReturn {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: deviceId ? ['devices', deviceId, 'logs'] : ['devices', 'invalid', 'logs'],
    queryFn: () => {
      if (!deviceId) throw new Error('Device ID is required');
      return apiClient.getDeviceLogs(deviceId);
    },
    enabled: !!deviceId,
    staleTime: 1000 * 60 * 3,
    refetchInterval: 1000 * 10,
    refetchIntervalInBackground: true,
  });

  return {
    logs: data ?? null,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar logs del dispositivo' : null,
  };
}

