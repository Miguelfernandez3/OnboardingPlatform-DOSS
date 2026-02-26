import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { deviceService } from '../../infrastructure/services/deviceService';
import { Device } from '../../core/domain/entities/Device';

interface UseDevicesReturn {
  devices: Device[];
  loading: boolean;
  error: string | null;
}

/**
 * Hook para obtener la lista de dispositivos
 * Usa TanStack Query para cacheo automático
 */
export function useDevices(): UseDevicesReturn {
  const { data: devices = [], isLoading, isError, error } = useQuery({
    queryKey: queryKeys.devices.all,
    queryFn: deviceService.getDevices,
    staleTime: 1000 * 5, // 5 segundos
  });

  return {
    devices,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar dispositivos' : null,
  };
}

