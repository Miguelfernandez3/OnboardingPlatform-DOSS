import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { mitigationService } from '../../infrastructure/services/mitigationService';
import { Mitigation } from '../../core/domain/entities/Mitigation';

interface UseMitigationsReturn {
  mitigations: Mitigation[];
  loading: boolean;
  error: string | null;
  enforceMitigation: (
    mitigationId: string,
    options?: { extraContext?: Record<string, unknown> }
  ) => Promise<void>;
  revokeMitigation: (mitigationId: string) => Promise<void>;
}

/**
 * Hook para gestionar mitigations de un dispositivo
 * Usa TanStack Query con optimistic updates para mejor UX
 */
export function useMitigations(deviceId: string | undefined): UseMitigationsReturn {
  const queryClient = useQueryClient();

  // Query para obtener mitigations
  const {
    data: mitigations = [],
    isLoading,
    isError,
    error,
    
  } = useQuery({
    queryKey: deviceId ? queryKeys.devices.mitigations(deviceId) : ['mitigations', 'invalid'],
    queryFn: () => {
      if (!deviceId) throw new Error('Device ID is required');
      return mitigationService.getDeviceMitigations(deviceId);
    },
    enabled: !!deviceId,
    staleTime: 1000 * 30,
    refetchInterval: 1000 * 10,
    refetchIntervalInBackground: true,
  });

  // Mutation para aplicar (enforce) mitigación
  const enforceMutation = useMutation({
    mutationFn: ({
      mitigationId,
      options,
    }: {
      mitigationId: string;
      options?: { extraContext?: Record<string, unknown> };
    }) => {
      if (!deviceId) throw new Error('Device ID is required');
      return mitigationService.enforceMitigation(deviceId, mitigationId, options);
    },
    onMutate: async (variables) => {
      const { mitigationId } = variables;
      // Cancelar queries en progreso
      await queryClient.cancelQueries({ queryKey: queryKeys.devices.mitigations(deviceId!) });

      // Snapshot del valor anterior
      const previousMitigations = queryClient.getQueryData<Mitigation[]>(
        queryKeys.devices.mitigations(deviceId!)
      );

      // Optimistic update
      queryClient.setQueryData<Mitigation[]>(
        queryKeys.devices.mitigations(deviceId!),
        (old) => {
          if (!old) return [];
          return old.map((m) =>
            m.id === mitigationId
              ? {
                  ...m,
                  is_enforced: true,
                  enforcement_timestamp: new Date().toISOString(),
                  last_enforced: new Date().toISOString(),
                } as Mitigation
              : m
          );
        }
      );

      return { previousMitigations };
    },
    onError: (err, _, context) => {
      // Rollback en caso de error
      if (context?.previousMitigations) {
        queryClient.setQueryData(
          queryKeys.devices.mitigations(deviceId!),
          context.previousMitigations
        );
      }
      console.error('Error al aplicar mitigation:', err);
    },
    onSuccess: (updatedMitigation) => {
      // Actualizar cache con respuesta del servidor
      queryClient.setQueryData<Mitigation[]>(
        queryKeys.devices.mitigations(deviceId!),
        (old) => {
          if (!old) return [updatedMitigation];
          return old.map((m) => (m.id === updatedMitigation.id ? updatedMitigation : m));
        }
      );
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.mitigations(deviceId!) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.detail(deviceId!) });
    },
  });

  // Mutation para revocar (revoke) mitigación
  const revokeMutation = useMutation({
    mutationFn: (mitigationId: string) => {
      if (!deviceId) throw new Error('Device ID is required');
      return mitigationService.revokeMitigation(deviceId, mitigationId);
    },
    onMutate: async (mitigationId) => {
      // Cancelar queries en progreso
      await queryClient.cancelQueries({ queryKey: queryKeys.devices.mitigations(deviceId!) });

      // Snapshot del valor anterior
      const previousMitigations = queryClient.getQueryData<Mitigation[]>(
        queryKeys.devices.mitigations(deviceId!)
      );

      // Optimistic update
      queryClient.setQueryData<Mitigation[]>(
        queryKeys.devices.mitigations(deviceId!),
        (old) => {
          if (!old) return old;
          return old.map((m) =>
            m.id === mitigationId ? new Mitigation({
              id: m.id,
              deviceId: m.deviceId,
              threatId: m.threatId,
              name: m.name,
              description: m.description,
              mitigation_actions: m.mitigation_actions,
              is_enforced: false,
              last_enforced: undefined,
              enforcement_timestamp: undefined,
              enforcementGaps: m.enforcementGaps,
            }) : m
          );
        }
      );

      return { previousMitigations };
    },
    onError: (err, _, context) => {
      // Rollback en caso de error
      if (context?.previousMitigations) {
        queryClient.setQueryData(
          queryKeys.devices.mitigations(deviceId!),
          context.previousMitigations
        );
      }
      console.error('Error al revocar mitigation:', err);
    },
    onSuccess: (updatedMitigation) => {
      // Actualizar cache con respuesta del servidor
      queryClient.setQueryData<Mitigation[]>(
        queryKeys.devices.mitigations(deviceId!),
        (old) => {
          if (!old) return [updatedMitigation];
          return old.map((m) => (m.id === updatedMitigation.id ? updatedMitigation : m));
        }
      );
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.mitigations(deviceId!) });
    },
  });

  const enforceMitigation = async (
    mitigationId: string,
    options?: { extraContext?: Record<string, unknown> }
  ): Promise<void> => {
    await enforceMutation.mutateAsync({ mitigationId, options });
  };

  const revokeMitigation = async (mitigationId: string): Promise<void> => {
    await revokeMutation.mutateAsync(mitigationId);
  };

  return {
    mitigations,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar mitigations' : null,
    enforceMitigation,
    revokeMitigation,
  };
}
