import { useState, useEffect } from 'react';
import { apiClient } from '../../config';
import { Device } from '../../core/domain/entities/Device';

interface UseDevicesReturn {
  devices: Device[];
  loading: boolean;
  error: string | null;
}

/**
 * Hook para obtener la lista de dispositivos
 */
export function useDevices(): UseDevicesReturn {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDevices = async (): Promise<void> => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiClient.getDevices();
        setDevices(data);
      } catch (err) {
        setError((err as Error).message || 'Error al cargar dispositivos');
      } finally {
        setLoading(false);
      }
    };

    fetchDevices();
  }, []);

  return { devices, loading, error };
}

