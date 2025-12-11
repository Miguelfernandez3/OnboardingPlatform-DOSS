import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { threatService } from '../../infrastructure/services/threatService';
import { Threat } from '../../core/domain/entities/Threat';

interface UseThreatsReturn {
  threats: Threat[];
  loading: boolean;
  error: string | null;
}

/**
 * Hook para gestionar threats de un dispositivo
 * Usa TanStack Query para cacheo automático
 */
export function useThreats(deviceId: string | undefined): UseThreatsReturn {
  const {
    data: threats = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: deviceId ? queryKeys.devices.threats(deviceId) : ['threats', 'invalid'],
    queryFn: () => {
      if (!deviceId) throw new Error('Device ID is required');
      return threatService.getDeviceThreats(deviceId);
    },
    enabled: !!deviceId,
    staleTime: 1000 * 60 * 3, // 3 minutos
  });

  return {
    threats,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar threats' : null,
  };
}
