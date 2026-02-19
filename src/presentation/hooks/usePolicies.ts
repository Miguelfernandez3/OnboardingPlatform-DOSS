import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { policyServiceActions } from '../../infrastructure/services/policyService';
import { Policy } from '../../core/domain/entities/Policy';
import { ApplyResult, EnforcementStatus } from '../../core/ports/IApiClient';

interface UsePoliciesReturn {
  policies: Policy[];
  loading: boolean;
  error: string | null;
  enforcementStatus: EnforcementStatus | null;
  applyPolicy: (msplXml: string, name?: string) => Promise<ApplyResult>;
  applyIDSP2: (idsp2Id: string) => Promise<ApplyResult>;
  enforcePolicy: (policyId: string) => Promise<ApplyResult>;
}

/**
 * Hook para gestionar políticas de un dispositivo
 * Usa TanStack Query para cacheo automático y mutations
 */
export function usePolicies(deviceId: string | undefined): UsePoliciesReturn {
  const queryClient = useQueryClient();

  // Query para obtener políticas
  const {
    data: policies = [],
    isLoading: policiesLoading,
    isError: policiesError,
    error: policiesErrorData,
  } = useQuery({
    queryKey: deviceId ? queryKeys.devices.policies(deviceId) : ['policies', 'invalid'],
    queryFn: () => {
      if (!deviceId) throw new Error('Device ID is required');
      return policyServiceActions.getDevicePolicies(deviceId);
    },
    enabled: !!deviceId,
  });

  // Query para obtener estado de enforcement
  const {
    data: enforcementStatus = null,
    isLoading: enforcementLoading,
  } = useQuery({
    queryKey: deviceId ? queryKeys.devices.enforcementStatus(deviceId) : ['enforcement', 'invalid'],
    queryFn: () => {
      if (!deviceId) throw new Error('Device ID is required');
      return policyServiceActions.getEnforcementStatus(deviceId);
    },
    enabled: !!deviceId,
    staleTime: 1000 * 60 * 2, // 2 minutos
  });

  // Mutation para aplicar política
  const applyPolicyMutation = useMutation({
    mutationFn: ({ msplXml, name }: { msplXml: string; name?: string }) => {
      if (!deviceId) throw new Error('Device ID is required');
      return policyServiceActions.applyPolicy(deviceId, msplXml, name);
    },
    onSuccess: () => {
      // Invalidar cache de políticas y enforcement status
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.policies(deviceId!) });
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.enforcementStatus(deviceId!) });
    },
    onError: (err) => {
      console.error('Error al aplicar política:', err);
    },
  });

  // Mutation para aplicar IDSP2
  const applyIDSP2Mutation = useMutation({
    mutationFn: (idsp2Id: string) => {
      if (!deviceId) throw new Error('Device ID is required');
      return policyServiceActions.applyIDSP2(deviceId, idsp2Id);
    },
    onSuccess: () => {
      // Invalidar cache de políticas y enforcement status
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.policies(deviceId!) });
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.enforcementStatus(deviceId!) });
    },
    onError: (err) => {
      console.error('Error al aplicar IDSP2:', err);
    },
  });

  // Mutation para ejecutar enforcement de una policy concreta
  const enforcePolicyMutation = useMutation({
    mutationFn: (policyId: string) => {
      if (!deviceId) throw new Error('Device ID is required');
      return policyServiceActions.enforcePolicy(deviceId, policyId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.policies(deviceId!) });
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.enforcementStatus(deviceId!) });
    },
    onError: (err) => {
      console.error('Error al ejecutar enforcement de policy:', err);
    },
  });

  const applyPolicy = async (msplXml: string, name?: string): Promise<ApplyResult> => {
    try {
      return await applyPolicyMutation.mutateAsync({ msplXml, name });
    } catch (err) {
      throw err;
    }
  };

  const applyIDSP2 = async (idsp2Id: string): Promise<ApplyResult> => {
    try {
      return await applyIDSP2Mutation.mutateAsync(idsp2Id);
    } catch (err) {
      throw err;
    }
  };

  const enforcePolicy = async (policyId: string): Promise<ApplyResult> => {
    try {
      return await enforcePolicyMutation.mutateAsync(policyId);
    } catch (err) {
      throw err;
    }
  };

  return {
    policies,
    loading: policiesLoading || enforcementLoading,
    error: policiesError ? (policiesErrorData as Error)?.message || 'Error al cargar políticas' : null,
    enforcementStatus,
    applyPolicy,
    applyIDSP2,
    enforcePolicy,
  };
}
