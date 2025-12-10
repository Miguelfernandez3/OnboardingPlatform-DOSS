import { Device } from '../domain/entities/Device';
import { Policy } from '../domain/entities/Policy';
import { MUD } from '../domain/entities/MUD';
import { Passport } from '../domain/entities/Passport';

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
   */
  abstract applyPolicy(deviceId: string, msplXml: string): Promise<ApplyResult>;

  /**
   * Obtiene el estado de enforcement de un dispositivo
   */
  abstract getEnforcementStatus(deviceId: string): Promise<EnforcementStatus>;
}

