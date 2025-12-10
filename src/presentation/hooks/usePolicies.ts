import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../config';
import { PolicyService } from '../../core/domain/services/PolicyService';
import { Policy } from '../../core/domain/entities/Policy';
import { ApplyResult, EnforcementStatus } from '../../core/ports/IApiClient';

interface UsePoliciesReturn {
  policies: Policy[];
  loading: boolean;
  error: string | null;
  enforcementStatus: EnforcementStatus | null;
  applyPolicy: (msplXml: string) => Promise<ApplyResult>;
  applyIDSP2: (idsp2Id: string) => Promise<ApplyResult>;
  refresh: () => Promise<void>;
}

/**
 * Hook para gestionar políticas de un dispositivo
 */
export function usePolicies(deviceId: string | undefined): UsePoliciesReturn {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [enforcementStatus, setEnforcementStatus] = useState<EnforcementStatus | null>(null);

  const policyService = new PolicyService(apiClient);

  const fetchPolicies = useCallback(async (): Promise<void> => {
    if (!deviceId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await policyService.getDevicePolicies(deviceId);
      setPolicies(data);
    } catch (err) {
      setError((err as Error).message || 'Error al cargar políticas');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  const fetchEnforcementStatus = useCallback(async (): Promise<void> => {
    if (!deviceId) return;

    try {
      const status = await policyService.getEnforcementStatus(deviceId);
      setEnforcementStatus(status);
    } catch (err) {
      console.error('Error al obtener estado de enforcement:', err);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchPolicies();
    fetchEnforcementStatus();
  }, [fetchPolicies, fetchEnforcementStatus]);

  const applyPolicy = async (msplXml: string): Promise<ApplyResult> => {
    if (!deviceId) throw new Error('Device ID is required');
    try {
      setError(null);
      const result = await policyService.applyPolicy(deviceId, msplXml);
      await fetchPolicies();
      await fetchEnforcementStatus();
      return result;
    } catch (err) {
      setError((err as Error).message || 'Error al aplicar política');
      throw err;
    }
  };

  const applyIDSP2 = async (idsp2Id: string): Promise<ApplyResult> => {
    if (!deviceId) throw new Error('Device ID is required');
    try {
      setError(null);
      const result = await policyService.applyIDSP2(deviceId, idsp2Id);
      await fetchPolicies();
      await fetchEnforcementStatus();
      return result;
    } catch (err) {
      setError((err as Error).message || 'Error al aplicar IDSP2');
      throw err;
    }
  };

  return {
    policies,
    loading,
    error,
    enforcementStatus,
    applyPolicy,
    applyIDSP2,
    refresh: fetchPolicies
  };
}

