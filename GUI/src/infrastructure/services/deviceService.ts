import { apiClient } from '../../config';
import { Device } from '../../core/domain/entities/Device';

/**
 * Device Service - Funciones para operaciones con dispositivos
 * Encapsula las llamadas al apiClient para dispositivos
 */
export const deviceService = {
  /**
   * Obtiene la lista de todos los dispositivos
   */
  getDevices: async (): Promise<Device[]> => {
    return await apiClient.getDevices();
  },

  /**
   * Obtiene un dispositivo específico por ID
   */
  getDevice: async (id: string): Promise<Device> => {
    return await apiClient.getDevice(id);
  },

  /**
   * Actualiza un dispositivo
   */
  updateDevice: async (id: string, data: Partial<Device>): Promise<Device> => {
    return await apiClient.updateDevice(id, data);
  },

  /**
   * Elimina un dispositivo
   */
  deleteDevice: async (id: string): Promise<void> => {
    return await apiClient.deleteDevice(id);
  },
};
