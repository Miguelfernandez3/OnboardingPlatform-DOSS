import { useState, useEffect } from 'react';
import { apiClient } from '../../config';
import { Device } from '../../core/domain/entities/Device';

interface UseDeviceReturn {
  device: Device | null;
  loading: boolean;
  error: string | null;
}

/**
 * Hook para obtener un dispositivo específico
 */
export function useDevice(deviceId: string | undefined): UseDeviceReturn {
  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!deviceId) {
      setLoading(false);
      return;
    }

    const fetchDevice = async (): Promise<void> => {
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
    };

    fetchDevice();
  }, [deviceId]);

  return { device, loading, error };
}

