import { apiClient } from '../../config';
import { PolicyService as DomainPolicyService } from '../../core/domain/services/PolicyService';
import { Policy } from '../../core/domain/entities/Policy';
import { ApplyResult, EnforcementStatus } from '../../core/ports/IApiClient';

// Crear instancia del PolicyService del dominio
const policyService = new DomainPolicyService(apiClient);

/**
 * Policy Service - Funciones para operaciones con políticas
 * Encapsula las llamadas al PolicyService del dominio
 */
export const policyServiceActions = {
  /**
   * Obtiene las políticas de un dispositivo
   */
  getDevicePolicies: async (deviceId: string): Promise<Policy[]> => {
    return await policyService.getDevicePolicies(deviceId);
  },

  /**
   * Aplica una política MSPL a un dispositivo
   */
  applyPolicy: async (deviceId: string, msplXml: string): Promise<ApplyResult> => {
    return await policyService.applyPolicy(deviceId, msplXml);
  },

  /**
   * Aplica un IDSP2 ID a un dispositivo
   */
  applyIDSP2: async (deviceId: string, idsp2Id: string): Promise<ApplyResult> => {
    return await policyService.applyIDSP2(deviceId, idsp2Id);
  },

  /**
   * Obtiene el estado de enforcement de un dispositivo
   */
  getEnforcementStatus: async (deviceId: string): Promise<EnforcementStatus> => {
    return await policyService.getEnforcementStatus(deviceId);
  },
};
