import { apiClient } from '../../config';
import { Device } from '../../core/domain/entities/Device';
import { CreateDeviceFromDSPInput } from '../../core/ports';

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
   * Crea un dispositivo directamente a partir de un DSP ID.
   */
  createDeviceFromDSP: async (data: CreateDeviceFromDSPInput): Promise<Device> => {
    return await apiClient.createDeviceFromDSP(data);
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
   * Gaps de enforcement a partir de MSPL arbitrario (mitigaciones, etc.)
   */
  postDeviceEnforcementGaps: async (
    deviceId: string,
    body: { msplXml: string; extraContext?: Record<string, unknown> }
  ) => {
    return await apiClient.postDeviceEnforcementGaps(deviceId, body);
  },

  /**
   * Elimina un dispositivo
   */
  deleteDevice: async (id: string): Promise<void> => {
    return await apiClient.deleteDevice(id);
  },
};
