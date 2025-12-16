import { apiClient } from '../../config';
import { Passport } from '../../core/domain/entities/Passport';

/**
 * Passport Service - Funciones para operaciones con passports
 * Encapsula las llamadas al apiClient para passports
 */
export const passportService = {
  /**
   * Obtiene el passport de un dispositivo
   */
  getDevicePassport: async (deviceId: string): Promise<Passport> => {
    return await apiClient.getDevicePassport(deviceId);
  },
};
