import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../config';
import { Threat } from '../../core/domain/entities/Threat';

interface UseThreatsReturn {
  threats: Threat[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * Hook para gestionar threats de un dispositivo
 */
export function useThreats(deviceId: string | undefined): UseThreatsReturn {
  const [threats, setThreats] = useState<Threat[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchThreats = useCallback(async (): Promise<void> => {
    if (!deviceId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getDeviceThreats(deviceId);
      setThreats(data);
    } catch (err) {
      setError((err as Error).message || 'Error al cargar threats');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchThreats();
  }, [fetchThreats]);

  return {
    threats,
    loading,
    error,
    refresh: fetchThreats
  };
}
