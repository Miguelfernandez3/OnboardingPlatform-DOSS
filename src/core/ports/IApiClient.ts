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

export interface UserData {
  id: string;
  email: string;
  role: string;
  isActive: boolean;
  lastLogin?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: UserData;
}

export interface UsersResponse {
  users: UserData[];
  total: number;
  page: number;
  limit: number;
}

export interface UserFilters {
  email?: string;
  role?: string;
  isActive?: boolean;
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

  /**
   * Autenticación: Inicia sesión con email y password
   */
  abstract login(email: string, password: string): Promise<AuthResponse>;

  /**
   * Autenticación: Refresca el token de acceso usando el refresh token
   */
  abstract refreshToken(refreshToken: string): Promise<AuthResponse>;

  /**
   * Autenticación: Obtiene el usuario actual autenticado
   */
  abstract getCurrentUser(): Promise<UserData>;

  /**
   * Autenticación: Cambia la contraseña del usuario actual
   */
  abstract changePassword(oldPassword: string, newPassword: string): Promise<void>;

  /**
   * Usuarios: Obtiene la lista de usuarios con paginación y filtros
   */
  abstract getUsers(page?: number, limit?: number, filters?: UserFilters): Promise<UsersResponse>;

  /**
   * Usuarios: Obtiene un usuario por ID
   */
  abstract getUser(id: string): Promise<UserData>;

  /**
   * Usuarios: Crea un nuevo usuario (solo admin)
   */
  abstract createUser(email: string, password: string, role: string): Promise<UserData>;

  /**
   * Usuarios: Actualiza el rol de un usuario (solo admin)
   */
  abstract updateUserRole(id: string, role: string): Promise<UserData>;

  /**
   * Usuarios: Elimina un usuario (solo admin)
   */
  abstract deleteUser(id: string): Promise<void>;

  /**
   * Usuarios: Activa un usuario (solo admin)
   */
  abstract activateUser(id: string): Promise<UserData>;
}

