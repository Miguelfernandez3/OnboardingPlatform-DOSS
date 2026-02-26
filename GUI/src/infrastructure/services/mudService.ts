import { apiClient } from '../../config';
import { MUD } from '../../core/domain/entities/MUD';

/**
 * MUD Service - Funciones para operaciones con MUDs
 * Encapsula las llamadas al apiClient para MUDs
 */
export const mudService = {
  /**
   * Obtiene el MUD de un dispositivo
   */
  getDeviceMUD: async (deviceId: string): Promise<MUD> => {
    return await apiClient.getDeviceMUD(deviceId);
  },
};
