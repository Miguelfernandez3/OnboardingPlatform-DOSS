import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../config';
import { Device } from '../../core/domain/entities/Device';

interface UseDeviceReturn {
  device: Device | null;
  loading: boolean;
  error: string | null;
  updateDevice: (data: Partial<Device>) => Promise<Device>;
  deleteDevice: () => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Hook para obtener y gestionar un dispositivo específico
 */
export function useDevice(deviceId: string | undefined): UseDeviceReturn {
  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevice = useCallback(async (): Promise<void> => {
    if (!deviceId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getDevice(deviceId);
      setDevice(data);
    } catch (err) {
      setError((err as Error).message || 'Error al cargar dispositivo');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchDevice();
  }, [fetchDevice]);

  const updateDevice = useCallback(async (data: Partial<Device>): Promise<Device> => {
    if (!deviceId) {
      throw new Error('Device ID is required');
    }

    try {
      setError(null);
      const updatedDevice = await apiClient.updateDevice(deviceId, data);
      setDevice(updatedDevice);
      return updatedDevice;
    } catch (err) {
      setError((err as Error).message || 'Error al actualizar dispositivo');
      throw err;
    }
  }, [deviceId]);

  const deleteDevice = useCallback(async (): Promise<void> => {
    if (!deviceId) {
      throw new Error('Device ID is required');
    }

    try {
      setError(null);
      await apiClient.deleteDevice(deviceId);
      setDevice(null);
    } catch (err) {
      setError((err as Error).message || 'Error al eliminar dispositivo');
      throw err;
    }
  }, [deviceId]);

  return { 
    device, 
    loading, 
    error, 
    updateDevice, 
    deleteDevice,
    refresh: fetchDevice
  };
}

