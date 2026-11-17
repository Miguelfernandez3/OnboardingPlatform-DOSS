import { Device, Policy, MUD, Passport, Threat, Mitigation } from '../domain';

export interface ApplyResult {
  status: string;
  message: string;
}

export interface CreateDeviceFromDSPInput {
  deviceId: string;
  idspId: string;
  model?: string;
  name?: string;
  type?: string;
  manufacturer?: string;
  ip?: string;
  mac?: string;
  edk?: string;
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

export interface EnforcementProfileData {
  id: string;
  name: string;
  mode: 'rest' | 'era';
  method: string;
  endpointTemplate?: string;
  headersTemplate?: string;
  payloadTemplate?: string;
  timeoutSeconds: number;
  dryRun: boolean;
  isDefault: boolean;
  isActive: boolean;
  autoEnforceOnRegistration: boolean;
  authType: 'none' | 'bearer';
  authSecretId?: number | null;
  allowMsplToken: boolean;
  contextSpec?: unknown;
  createdAt?: string;
  updatedAt?: string;
}

export interface EnforcementMappingData {
  id: string;
  matchKind: 'explicitProfile' | 'policyType' | 'capability';
  matchValue: string;
  profileId: number;
  priority: number;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface EnforcementSecretMetadata {
  id: string;
  name: string;
  keyVersion: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface EnforcementExecutionLog {
  id: string;
  deviceId?: string;
  policyId?: string;
  policyName?: string;
  profileId?: number;
  runMode: string;
  eventType?: string;
  correlationId?: string;
  stepName?: string;
  elapsedMs?: number;
  result: string;
  isTest: boolean;
  requestPreview?: string;
  responseStatus?: number;
  responseExcerpt?: string;
  errorMessage?: string;
  requestedBy?: string;
  executedAt?: string;
  createdAt?: string;
}

export interface DeviceLogStep {
  id: string;
  eventType?: string;
  stepName?: string;
  elapsedMs?: number;
  result: string;
  executedAt?: string;
  errorMessage?: string;
  policyName?: string;
  requestPreview?: string;
}

export interface DeviceLogGroup {
  correlationId: string;
  startedAt?: string;
  totalElapsedMs?: number;
  bestCaseFetchDspMs?: number;
  steps: DeviceLogStep[];
}

export interface DeviceLogsResponse {
  onboardings: DeviceLogGroup[];
}

export interface EnforcementTestRequest {
  profileId: number;
  runMode: 'preview' | 'execute';
  context?: Record<string, unknown>;
}

export interface EnforcementTestResponse {
  status: string;
  profileId: string;
  execution: Record<string, unknown>;
}

export interface NotificationSettings {
  language: string;
  telegramEnabled: boolean;
  telegramLinked: boolean;
  inAppNotificationsEnabled: boolean;
}

/** Preferencias de UI persistidas en el servidor (p. ej. idioma). */
export interface UserUiSettings {
  language: string;
}

export interface AppNotification {
  id: number;
  message: string;
  notificationType: string;
  status: string;
  language: string;
  deviceId: string | null;
  policyId: string | null;
  threatId: string | null;
  mitigationId: string | null;
  threatMudUrl: string | null;
  deduplicationKey: string;
  error: string | null;
  createdAt: string | null;
  sentAt: string | null;
  readAt: string | null;
}

export interface NotificationsListResponse {
  notifications: AppNotification[];
  pagination: { page: number; perPage: number; total: number; pages: number };
}

export interface UnreadNotificationsCountResponse {
  count: number;
}

export interface TelegramLinkTokenResponse {
  botUsername: string;
  startUrl: string;
  expiresAt: string;
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
   * Crea un dispositivo directamente a partir de un DSP ID.
   */
  abstract createDeviceFromDSP(data: CreateDeviceFromDSPInput): Promise<Device>;

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
   * Ejecuta el enforcement de una política. Opcionalmente envía `extraContext` (p. ej. credenciales de operador).
   */
  abstract enforcePolicy(
    deviceId: string,
    policyId: string,
    options?: { extraContext?: Record<string, unknown> }
  ): Promise<ApplyResult>;

  /**
   * Lista requisitos de contexto faltantes para el enforcement (sin llamar al dispositivo).
   */
  abstract getPolicyEnforcementGaps(deviceId: string, policyId: string): Promise<{
    mode: string;
    profileId: string | null;
    missing: Array<Record<string, unknown>>;
    warnings: string[];
  }>;

  /**
   * Gaps para un MSPL arbitrario (p. ej. acciones de mitigación).
   */
  abstract postDeviceEnforcementGaps(
    deviceId: string,
    body: { msplXml: string; extraContext?: Record<string, unknown> }
  ): Promise<{
    mode: string;
    profileId: string | null;
    missing: Array<Record<string, unknown>>;
    warnings: string[];
  }>;

  /**
   * Obtiene las amenazas (threats) asociadas a un dispositivo
   */
  abstract getDeviceThreats(deviceId: string): Promise<Threat[]>;

  /**
   * Obtiene las mitigations asociadas a un dispositivo
   */
  abstract getDeviceMitigations(deviceId: string): Promise<Mitigation[]>;

  /**
   * Obtiene los logs de un dispositivo (agrupados por correlationId cuando aplique).
   */
  abstract getDeviceLogs(deviceId: string): Promise<DeviceLogsResponse>;

  /**
   * Aplica (enforce) una mitigación. Opcionalmente `extraContext` (fusionado con threat_id internos).
   */
  abstract enforceMitigation(
    deviceId: string,
    mitigationId: string,
    options?: { extraContext?: Record<string, unknown> }
  ): Promise<Mitigation>;

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

  /**
   * Usuarios: Desactiva un usuario (solo admin)
   */
  abstract deactivateUser(id: string): Promise<UserData>;

  abstract getEnforcementProfiles(includeInactive?: boolean): Promise<EnforcementProfileData[]>;
  abstract createEnforcementProfile(
    payload: Partial<EnforcementProfileData> & { name: string; mode: 'rest' | 'era' }
  ): Promise<EnforcementProfileData>;
  abstract updateEnforcementProfile(
    id: string,
    payload: Partial<EnforcementProfileData>
  ): Promise<EnforcementProfileData>;
  abstract deleteEnforcementProfile(id: string): Promise<void>;

  abstract getEnforcementMappings(includeInactive?: boolean): Promise<EnforcementMappingData[]>;
  abstract createEnforcementMapping(
    payload: Partial<EnforcementMappingData> & {
      matchKind: 'explicitProfile' | 'policyType' | 'capability';
      matchValue: string;
      profileId: number;
    }
  ): Promise<EnforcementMappingData>;
  abstract updateEnforcementMapping(
    id: string,
    payload: Partial<EnforcementMappingData>
  ): Promise<EnforcementMappingData>;
  abstract deleteEnforcementMapping(id: string): Promise<void>;

  abstract getEnforcementSecrets(): Promise<EnforcementSecretMetadata[]>;
  abstract createEnforcementSecret(name: string, value: string): Promise<EnforcementSecretMetadata>;
  abstract updateEnforcementSecret(
    id: string,
    payload: { name?: string; value?: string }
  ): Promise<EnforcementSecretMetadata>;
  abstract deleteEnforcementSecret(id: string): Promise<void>;

  abstract testEnforcementProfile(payload: EnforcementTestRequest): Promise<EnforcementTestResponse>;
  abstract getEnforcementExecutions(filters?: {
    from?: string;
    to?: string;
    result?: string;
    deviceId?: string;
    isTest?: boolean;
    profileId?: number;
    limit?: number;
  }): Promise<EnforcementExecutionLog[]>;

  abstract getUserUiSettings(): Promise<UserUiSettings>;
  abstract putUserUiSettings(data: { language: string }): Promise<UserUiSettings>;

  abstract getNotificationSettings(): Promise<NotificationSettings>;
  abstract putNotificationSettings(data: Partial<{
    telegramEnabled: boolean;
    inAppNotificationsEnabled: boolean;
  }>): Promise<NotificationSettings>;
  abstract getNotifications(
    page?: number,
    perPage?: number,
    status?: string,
    readState?: 'unread' | 'read'
  ): Promise<NotificationsListResponse>;
  abstract getUnreadNotificationsCount(): Promise<UnreadNotificationsCountResponse>;
  abstract markNotificationRead(id: number): Promise<void>;
  abstract markAllNotificationsRead(): Promise<{ updated: number }>;
  abstract createTelegramLinkToken(): Promise<TelegramLinkTokenResponse>;
  abstract deleteTelegramLink(): Promise<void>;
}
