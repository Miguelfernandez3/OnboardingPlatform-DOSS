import { apiClient } from '../../config';
import { Threat } from '../../core/domain/entities/Threat';

/**
 * Threat Service - Funciones para operaciones con threats
 * Encapsula las llamadas al apiClient para threats
 */
export const threatService = {
  /**
   * Obtiene las threats de un dispositivo
   */
  getDeviceThreats: async (deviceId: string): Promise<Threat[]> => {
    return await apiClient.getDeviceThreats(deviceId);
  },
};
