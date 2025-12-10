import { IApiClient } from '../../ports/IApiClient';

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

export interface ApplyResult {
  status: string;
  message: string;
}

/**
 * Policy Service
 * Lógica de negocio para políticas MSPL
 */
export class PolicyService {
  constructor(private apiClient: IApiClient) {}

  /**
   * Valida que el XML MSPL tenga la estructura básica correcta
   */
  validateMSPL(msplXml: string): ValidationResult {
    if (!msplXml || typeof msplXml !== 'string') {
      return { valid: false, error: 'MSPL XML debe ser una cadena de texto' };
    }

    if (!msplXml.includes('<ITResourceOrchestration')) {
      return { valid: false, error: 'MSPL XML debe contener ITResourceOrchestration' };
    }

    return { valid: true };
  }

  /**
   * Aplica una política MSPL a un dispositivo
   */
  async applyPolicy(deviceId: string, msplXml: string): Promise<ApplyResult> {
    const validation = this.validateMSPL(msplXml);
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    return await this.apiClient.applyPolicy(deviceId, msplXml);
  }

  /**
   * Aplica un IDSP2 ID a un dispositivo
   */
  async applyIDSP2(deviceId: string, idsp2Id: string): Promise<ApplyResult> {
    if (!idsp2Id || typeof idsp2Id !== 'string' || idsp2Id.trim() === '') {
      throw new Error('IDSP2 ID es requerido');
    }

    return await this.apiClient.applyIDSP2(deviceId, idsp2Id.trim());
  }

  /**
   * Obtiene las políticas aplicadas de un dispositivo
   */
  async getDevicePolicies(deviceId: string) {
    return await this.apiClient.getDevicePolicies(deviceId);
  }

  /**
   * Obtiene el estado de enforcement de un dispositivo
   */
  async getEnforcementStatus(deviceId: string) {
    return await this.apiClient.getEnforcementStatus(deviceId);
  }
}

