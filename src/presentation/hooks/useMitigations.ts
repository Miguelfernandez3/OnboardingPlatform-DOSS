import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../config';
import { Mitigation } from '../../core/domain/entities/Mitigation';

interface UseMitigationsReturn {
  mitigations: Mitigation[];
  loading: boolean;
  error: string | null;
  enforceMitigation: (mitigationId: string) => Promise<void>;
  revokeMitigation: (mitigationId: string) => Promise<void>;
  refreshMitigations: () => Promise<void>;
}

/**
 * Hook para gestionar mitigations de un dispositivo
 * Incluye optimistic updates para mejor UX
 */
export function useMitigations(deviceId: string | undefined): UseMitigationsReturn {
  const [mitigations, setMitigations] = useState<Mitigation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMitigations = useCallback(async (): Promise<void> => {
    if (!deviceId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getDeviceMitigations(deviceId);
      setMitigations(data);
    } catch (err) {
      setError((err as Error).message || 'Error al cargar mitigations');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchMitigations();
  }, [fetchMitigations]);

  const enforceMitigation = useCallback(async (mitigationId: string): Promise<void> => {
    if (!deviceId) {
      throw new Error('Device ID is required');
    }

    // Optimistic update
    const previousMitigations = [...mitigations];
    setMitigations(prev => prev.map(m => 
      m.id === mitigationId 
        ? { ...m, is_enforced: true, enforcement_timestamp: new Date().toISOString(), last_enforced: new Date().toISOString() }
        : m
    ));

    try {
      setError(null);
      const updatedMitigation = await apiClient.enforceMitigation(deviceId, mitigationId);
      // Actualizar con la respuesta del servidor
      setMitigations(prev => prev.map(m => 
        m.id === mitigationId ? updatedMitigation : m
      ));
    } catch (err) {
      // Rollback en caso de error
      setMitigations(previousMitigations);
      setError((err as Error).message || 'Error al aplicar mitigation');
      throw err;
    }
  }, [deviceId, mitigations]);

  const revokeMitigation = useCallback(async (mitigationId: string): Promise<void> => {
    if (!deviceId) {
      throw new Error('Device ID is required');
    }

    // Optimistic update
    const previousMitigations = [...mitigations];
    setMitigations(prev => prev.map(m => 
      m.id === mitigationId 
        ? { ...m, is_enforced: false, enforcement_timestamp: undefined, last_enforced: undefined }
        : m
    ));

    try {
      setError(null);
      const updatedMitigation = await apiClient.revokeMitigation(deviceId, mitigationId);
      // Actualizar con la respuesta del servidor
      setMitigations(prev => prev.map(m => 
        m.id === mitigationId ? updatedMitigation : m
      ));
    } catch (err) {
      // Rollback en caso de error
      setMitigations(previousMitigations);
      setError((err as Error).message || 'Error al revocar mitigation');
      throw err;
    }
  }, [deviceId, mitigations]);

  return {
    mitigations,
    loading,
    error,
    enforceMitigation,
    revokeMitigation,
    refreshMitigations: fetchMitigations
  };
}
