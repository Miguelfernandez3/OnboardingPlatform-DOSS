import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { deviceService } from '../../infrastructure/services/deviceService';
import { Device } from '../../core/domain/entities/Device';
import { CreateDeviceFromDSPInput } from '../../core/ports';

interface UseDevicesReturn {
  devices: Device[];
  loading: boolean;
  error: string | null;
  createDeviceFromDSP: (data: CreateDeviceFromDSPInput) => Promise<Device>;
}

/**
 * Hook para obtener la lista de dispositivos
 * Usa TanStack Query para cacheo automático
 */
export function useDevices(): UseDevicesReturn {
  const queryClient = useQueryClient();
  const { data: devices = [], isLoading, isError, error } = useQuery({
    queryKey: queryKeys.devices.all,
    queryFn: deviceService.getDevices,
    staleTime: 1000 * 5, // 5 segundos
    refetchInterval: 1000 * 15, // 15 segundos
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateDeviceFromDSPInput) => deviceService.createDeviceFromDSP(data),
    onSuccess: (createdDevice) => {
      queryClient.setQueryData(queryKeys.devices.detail(createdDevice.id), createdDevice);
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all, exact: true });
    },
    onError: (err) => {
      console.error('Error al crear dispositivo desde DSP:', err);
    },
  });

  const createDeviceFromDSP = async (data: CreateDeviceFromDSPInput): Promise<Device> => {
    return await createMutation.mutateAsync(data);
  };

  return {
    devices,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar dispositivos' : null,
    createDeviceFromDSP,
  };
}
