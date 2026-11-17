import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { deviceService } from '../../infrastructure/services/deviceService';
import { Device } from '../../core/domain/entities/Device';

interface UseDeviceReturn {
  device: Device | null;
  loading: boolean;
  error: string | null;
  updateDevice: (data: Partial<Device>) => Promise<Device>;
  deleteDevice: () => Promise<void>;
  /** Tras borrar con éxito: desactiva refetch del detalle y permite apagar el resto de hooks del dispositivo. */
  isDeviceDeleted: boolean;
}

/**
 * Hook para obtener y gestionar un dispositivo específico
 * Usa TanStack Query para cacheo automático y mutations
 */
export function useDevice(deviceId: string | undefined): UseDeviceReturn {
  const queryClient = useQueryClient();

  // Mutation para eliminar dispositivo (definida antes del query para usar isSuccess en enabled)
  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!deviceId) throw new Error('Device ID is required');
      return deviceService.deleteDevice(deviceId);
    },
    onSuccess: () => {
      if (!deviceId) return;
      void queryClient.cancelQueries({
        predicate: (q) =>
          Array.isArray(q.queryKey) && q.queryKey[0] === 'devices' && q.queryKey[1] === deviceId,
      });
      queryClient.removeQueries({ queryKey: ['devices', deviceId] });
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all, exact: true });
    },
    onError: (err) => {
      console.error('Error al eliminar dispositivo:', err);
    },
  });

  useEffect(() => {
    deleteMutation.reset();
  }, [deviceId]); // eslint-disable-line react-hooks/exhaustive-deps -- reset al cambiar de dispositivo en la ruta

  // Query para obtener el dispositivo
  const {
    data: device = null,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: deviceId ? queryKeys.devices.detail(deviceId) : ['devices', 'invalid'],
    queryFn: () => {
      if (!deviceId) throw new Error('Device ID is required');
      return deviceService.getDevice(deviceId);
    },
    enabled: !!deviceId && !deleteMutation.isSuccess,
    staleTime: 1000 * 15,
    refetchInterval: 1000 * 15,
    refetchIntervalInBackground: true,
  });

  // Mutation para actualizar dispositivo
  const updateMutation = useMutation({ 
    mutationFn: (data: Partial<Device>) => {
      if (!deviceId) throw new Error('Device ID is required');
      return deviceService.updateDevice(deviceId, data);
    },
    onSuccess: (updatedDevice) => {
      // Invalidar y actualizar cache
      queryClient.setQueryData(queryKeys.devices.detail(deviceId!), updatedDevice);
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all, exact: true });
    },
    onError: (err) => {
      console.error('Error al actualizar dispositivo:', err);
    },
  });

  const updateDevice = async (data: Partial<Device>): Promise<Device> => {
    try {
      return await updateMutation.mutateAsync(data);
    } catch (err) {
      throw err;
    }
  };

  const deleteDevice = async (): Promise<void> => {
    try {
      await deleteMutation.mutateAsync();
    } catch (err) {
      throw err;
    }
  };

  return {
    device,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar dispositivo' : null,
    updateDevice,
    deleteDevice,
    isDeviceDeleted: deleteMutation.isSuccess,
  };
}
