import { apiClient } from '../../config';
import { Mitigation } from '../../core/domain/entities/Mitigation';

/**
 * Mitigation Service - Funciones para operaciones con mitigations
 * Encapsula las llamadas al apiClient para mitigations
 */
export const mitigationService = {
  /**
   * Obtiene las mitigations de un dispositivo
   */
  getDeviceMitigations: async (deviceId: string): Promise<Mitigation[]> => {
    return await apiClient.getDeviceMitigations(deviceId);
  },

  /**
   * Aplica (enforce) una mitigación
   */
  enforceMitigation: async (
    deviceId: string,
    mitigationId: string,
    options?: { extraContext?: Record<string, unknown> }
  ): Promise<Mitigation> => {
    return await apiClient.enforceMitigation(deviceId, mitigationId, options);
  },

  /**
   * Revoca (revoke) una mitigación
   */
  revokeMitigation: async (deviceId: string, mitigationId: string): Promise<Mitigation> => {
    return await apiClient.revokeMitigation(deviceId, mitigationId);
  },
};
