import { Device, Policy, MUD, Passport, Threat, Mitigation } from '../domain';

export interface ApplyResult {
  status: string;
  message: string;
}

export interface EnforcementStatus {
  status: string;
  message: string;
  timestamp: string;
}

/**
 * IApiClient - Interface/Contrato para API Client
 * Define los métodos que debe implementar cualquier adapter de API
 */
export abstract class IApiClient {
  /**
   * Obtiene la lista de dispositivos
   */
  abstract getDevices(): Promise<Device[]>;

  /**
   * Obtiene un dispositivo por ID
   */
  abstract getDevice(id: string): Promise<Device>;

  /**
   * Obtiene el pasaporte digital de un dispositivo
   */
  abstract getDevicePassport(id: string): Promise<Passport>;

  /**
   * Obtiene el archivo MUD de un dispositivo
   */
  abstract getDeviceMUD(id: string): Promise<MUD>;

  /**
   * Obtiene las políticas aplicadas de un dispositivo
   */
  abstract getDevicePolicies(id: string): Promise<Policy[]>;

  /**
   * Aplica un IDSP2 ID a un dispositivo
   */
  abstract applyIDSP2(deviceId: string, idsp2Id: string): Promise<ApplyResult>;

  /**
   * Aplica una política MSPL directamente a un dispositivo
   * @param deviceId ID del dispositivo
   * @param msplXml XML de la política MSPL
   * @param name Nombre opcional de la política
   */
  abstract applyPolicy(deviceId: string, msplXml: string, name?: string): Promise<ApplyResult>;

  /**
   * Obtiene el estado de enforcement de un dispositivo
   */
  abstract getEnforcementStatus(deviceId: string): Promise<EnforcementStatus>;

  /**
   * Obtiene las threats asociadas a un dispositivo
   */
  abstract getDeviceThreats(deviceId: string): Promise<Threat[]>;

  /**
   * Obtiene las mitigations asociadas a un dispositivo
   */
  abstract getDeviceMitigations(deviceId: string): Promise<Mitigation[]>;

  /**
   * Aplica (enforce) una mitigación en un dispositivo
   */
  abstract enforceMitigation(deviceId: string, mitigationId: string): Promise<Mitigation>;

  /**
   * Revoca (revoke) una mitigación en un dispositivo
   */
  abstract revokeMitigation(deviceId: string, mitigationId: string): Promise<Mitigation>;

  /**
   * Actualiza información de un dispositivo
   */
  abstract updateDevice(deviceId: string, data: Partial<Device>): Promise<Device>;

  /**
   * Elimina un dispositivo
   */
  abstract deleteDevice(deviceId: string): Promise<void>;
}

