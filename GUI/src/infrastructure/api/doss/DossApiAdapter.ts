import { BaseApiClient } from '../base/BaseApiClient';
import { ConfigProvider } from '../../../core/adapters/config/ConfigProvider';
import { getAccessToken } from '../../utils/tokenStorage';
import { dossConfig } from './doss.config';
import { Device, DeviceData, Policy, PolicyData, MUD, Passport, PassportData, Threat, ThreatData, Mitigation, MitigationData } from '../../../core/domain';
import {
  ApplyResult,
  EnforcementStatus,
  AuthResponse,
  UserData,
  UsersResponse,
  UserFilters,
  DeviceAccessRule,
  AccessRuleKind,
  CreateDeviceFromDSPInput,
  EnforcementProfileData,
  EnforcementMappingData,
  EnforcementSecretMetadata,
  EnforcementExecutionLog,
  EnforcementTestRequest,
  EnforcementTestResponse,
  DeviceLogsResponse,
  ServiceLogsResponse,
  NotificationSettings,
  NotificationsListResponse,
  UnreadNotificationsCountResponse,
  TelegramLinkTokenResponse,
  UserUiSettings
} from '../../../core/ports';

/**
 * Interfaces para las respuestas de la API DOSS
 */
interface DevicesApiResponse {
  devices?: DeviceData[];
  data?: DeviceData[];
}

interface DeviceApiResponse {
  device?: DeviceData;
  data?: DeviceData;
}

interface PoliciesApiResponse {
  policies?: PolicyData[];
  data?: PolicyData[];
}

interface PassportApiResponse extends PassportData {
  deviceId?: string;
  [key: string]: unknown;
}

interface MUDApiResponse {
  id?: string;
  deviceId?: string;
  mudVersion?: number;
  mudUrl?: string;
  lastUpdate?: string;
  cacheValidity?: number;
  isSupported?: boolean;
  systeminfo?: string;
  mfgName?: string;
  documentation?: string;
  modelName?: string;
  mudData?: Record<string, unknown>;
  [key: string]: unknown;
}

interface ApplyResultApiResponse {
  status: string;
  message: string;
}

interface EnforcementStatusApiResponse {
  status: string;
  message: string;
  timestamp: string;
}

interface ThreatsApiResponse {
  threats?: ThreatData[];
  data?: ThreatData[];
}

interface MitigationsApiResponse {
  mitigations?: MitigationData[];
  data?: MitigationData[];
}

interface MitigationApiResponse {
  mitigation?: MitigationData;
  data?: MitigationData;
}

interface LoginApiResponse {
  access_token?: string;
  accessToken?: string;
  refresh_token?: string;
  refreshToken?: string;
  user: UserData;
}

interface UserApiResponse {
  user?: UserData;
  data?: UserData;
}

interface UsersApiResponse {
  users?: UserDataRaw[];
  data?: UserDataRaw[];
  total?: number;
  page?: number;
  limit?: number;
  pagination?: {
    total: number;
    page: number;
    per_page: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

interface EnforcementProfilesApiResponse {
  profiles?: EnforcementProfileData[];
  profile?: EnforcementProfileData;
}

interface EnforcementMappingsApiResponse {
  mappings?: EnforcementMappingData[];
  mapping?: EnforcementMappingData;
}

interface EnforcementSecretsApiResponse {
  secrets?: EnforcementSecretMetadata[];
  secret?: EnforcementSecretMetadata;
}

interface EnforcementExecutionsApiResponse {
  executions?: EnforcementExecutionLog[];
}

interface DeviceLogsApiResponse {
  onboardings?: Array<{
    correlationId?: string;
    startedAt?: string;
    totalElapsedMs?: number;
    bestCaseFetchDspMs?: number;
    steps?: Array<{
      id?: string | number;
      eventType?: string;
      stepName?: string;
      elapsedMs?: number;
      result?: string;
      executedAt?: string;
      errorMessage?: string;
      policyName?: string;
      requestPreview?: string;
    }>;
  }>;
}

// Raw user data from API (snake_case)
interface UserDataRaw {
  id: string | number;
  email: string;
  role: string;
  is_active?: boolean;
  isActive?: boolean;
  last_login?: string;
  lastLogin?: string;
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
}

// Transform user data from snake_case to camelCase
function transformUserData(raw: UserDataRaw): UserData {
  return {
    id: String(raw.id),
    email: raw.email,
    role: raw.role,
    isActive: raw.is_active ?? raw.isActive ?? false,
    lastLogin: raw.last_login ?? raw.lastLogin,
    createdAt: raw.created_at ?? raw.createdAt,
    updatedAt: raw.updated_at ?? raw.updatedAt,
  };
}


/**
 * DossApiAdapter - Implementación específica para DOSS
 * Extiende BaseApiClient e implementa los métodos específicos de DOSS
 */
export class DossApiAdapter extends BaseApiClient {
  constructor(onTokenRefresh?: () => Promise<void>, onAuthError?: () => void) {
    const configProvider = new ConfigProvider(dossConfig);
    super(configProvider, onTokenRefresh, onAuthError);
  }

  async getDevices(): Promise<Device[]> {
    const data = await this.get<DevicesApiResponse>('devices');
    const devices = data.devices || data.data || [];

    if (!Array.isArray(devices)) {
      return [];
    }

    return devices.map(device => Device.fromJSON(device));
  }

  async createDeviceFromDSP(data: CreateDeviceFromDSPInput): Promise<Device> {
    const payload = {
      device_id: data.deviceId,
      idsp_id: data.idspId,
      model: data.model,
      name: data.name,
      type: data.type,
      manufacturer: data.manufacturer,
      ip: data.ip,
      mac: data.mac,
      edk: data.edk
    };

    const endpoint = this.config.resolveEndpoint('registerDsp', {});
    console.info('[DSP register] POST', endpoint, 'payload:', { ...payload });
    try {
      const response = await this.post<DeviceApiResponse>('registerDsp', payload);
      const device = response.device || response.data;

      if (!device) {
        console.error('[DSP register] Response missing device:', response);
        throw new Error('Device registration did not return a device');
      }
      console.info('[DSP register] Success device_id:', (device as { device_id?: string; deviceId?: string }).device_id ?? (device as { device_id?: string; deviceId?: string }).deviceId);
      return Device.fromJSON(device);
    } catch (err) {
      console.error('[DSP register] Request failed:', err);
      throw err;
    }
  }

  async getDevice(id: string): Promise<Device> {
    const data = await this.get<DeviceApiResponse>('device', { id });
    const device = data.device || data.data;

    if (!device) {
      throw new Error(`Device with id ${id} not found`);
    }

    return Device.fromJSON(device);
  }

  async getDevicePassport(id: string): Promise<Passport> {
    const data = await this.get<PassportApiResponse>('passport', { id });
    return Passport.fromJSON({ deviceId: id, ...data });
  }

  async getDeviceMUD(id: string): Promise<MUD> {
    const data = await this.get<MUDApiResponse>('mud', { id });
    return MUD.fromJSON({ deviceId: id, ...data });
  }

  async getDevicePolicies(id: string): Promise<Policy[]> {
    const data = await this.get<PoliciesApiResponse>('policies', { id });
    const policies = data.policies || data.data || [];

    if (!Array.isArray(policies)) {
      return [];
    }

    return policies.map(policy => Policy.fromJSON(policy));
  }

  async applyIDSP2(deviceId: string, idsp2Id: string): Promise<ApplyResult> {
    const data = await this.post<ApplyResultApiResponse>('applyIdsp2', { idsp2Id }, { id: deviceId });
    return {
      status: data.status || 'pending',
      message: data.message || 'IDSP2 application initiated'
    };
  }

  async applyPolicy(deviceId: string, msplXml: string, name?: string): Promise<ApplyResult> {
    const data = await this.post<ApplyResultApiResponse>(
      'applyPolicy',
      { msplXml, name },
      { id: deviceId }
    );
    return {
      status: data.status || 'pending',
      message: data.message || 'Policy application initiated'
    };
  }

  async getEnforcementStatus(deviceId: string): Promise<EnforcementStatus> {
    const data = await this.get<EnforcementStatusApiResponse>('enforcementStatus', { id: deviceId });
    return {
      status: data.status || 'unknown',
      message: data.message || '',
      timestamp: data.timestamp || new Date().toISOString()
    };
  }

  async enforcePolicy(
    deviceId: string,
    policyId: string,
    options?: { extraContext?: Record<string, unknown> }
  ): Promise<ApplyResult> {
    const body =
      options?.extraContext && Object.keys(options.extraContext).length > 0
        ? { extraContext: options.extraContext }
        : {};
    const data = await this.post<ApplyResultApiResponse>(
      'enforcePolicy',
      body,
      { id: deviceId, policyId }
    );
    return {
      status: data.status || 'pending',
      message: data.message || 'Policy enforcement initiated'
    };
  }

  async getPolicyEnforcementGaps(
    deviceId: string,
    policyId: string
  ): Promise<{
    mode: string;
    profileId: string | null;
    missing: Array<Record<string, unknown>>;
    warnings: string[];
  }> {
    return this.get<{
      mode: string;
      profileId: string | null;
      missing: Array<Record<string, unknown>>;
      warnings: string[];
    }>('policyEnforcementGaps', { id: deviceId, policyId });
  }

  async postDeviceEnforcementGaps(
    deviceId: string,
    body: { msplXml: string; extraContext?: Record<string, unknown> }
  ): Promise<{
    mode: string;
    profileId: string | null;
    missing: Array<Record<string, unknown>>;
    warnings: string[];
  }> {
    const payload: Record<string, unknown> = { msplXml: body.msplXml };
    if (body.extraContext && Object.keys(body.extraContext).length > 0) {
      payload.extraContext = body.extraContext;
    }
    return this.post<{
      mode: string;
      profileId: string | null;
      missing: Array<Record<string, unknown>>;
      warnings: string[];
    }>('deviceEnforcementGaps', payload, { id: deviceId });
  }

  async getDeviceThreats(deviceId: string): Promise<Threat[]> {
    const data = await this.get<ThreatsApiResponse>('threats', { id: deviceId });
    const threats = data.threats || data.data || [];

    if (!Array.isArray(threats)) {
      return [];
    }

    return threats.map(threat => Threat.fromJSON({ ...threat, deviceId }));
  }

  async getDeviceLogs(deviceId: string): Promise<DeviceLogsResponse> {
    const data = await this.get<DeviceLogsApiResponse>('deviceLogs', { id: deviceId });
    const onboardings = (data.onboardings || []).map(group => ({
      correlationId: String(group.correlationId || ''),
      startedAt: group.startedAt,
      totalElapsedMs: group.totalElapsedMs,
      bestCaseFetchDspMs: group.bestCaseFetchDspMs,
      steps: (group.steps || []).map(step => ({
        id: String(step.id ?? ''),
        eventType: step.eventType,
        stepName: step.stepName,
        elapsedMs: step.elapsedMs,
        result: String(step.result ?? 'unknown'),
        executedAt: step.executedAt,
        errorMessage: step.errorMessage,
        policyName: step.policyName,
        requestPreview: step.requestPreview,
      })),
    }));
    return { onboardings };
  }

  async getServiceLogs(service: string, tail = 200): Promise<ServiceLogsResponse> {
    const data = await this.request<ServiceLogsResponse>(
      `/logs/${encodeURIComponent(service)}?tail=${tail}`,
      { method: 'GET' }
    );
    return {
      service: data.service ?? service,
      displayName: data.displayName ?? service,
      available: Boolean(data.available),
      lines: Array.isArray(data.lines) ? data.lines : [],
      truncated: Boolean(data.truncated),
    };
  }

  async getDeviceMitigations(deviceId: string): Promise<Mitigation[]> {
    const data = await this.get<MitigationsApiResponse>('mitigations', { id: deviceId });
    const mitigations = data.mitigations || data.data || [];

    if (!Array.isArray(mitigations)) {
      return [];
    }

    return mitigations.map(mitigation => Mitigation.fromJSON({ ...mitigation, deviceId }));
  }

  async enforceMitigation(
    deviceId: string,
    mitigationId: string,
    options?: { extraContext?: Record<string, unknown> }
  ): Promise<Mitigation> {
    const body =
      options?.extraContext && Object.keys(options.extraContext).length > 0
        ? { extraContext: options.extraContext }
        : {};
    const data = await this.post<MitigationApiResponse>(
      'enforceMitigation',
      body,
      { id: deviceId, mitigationId }
    );
    const mitigation = data.mitigation || data.data;

    if (!mitigation) {
      throw new Error(`Mitigation with id ${mitigationId} not found`);
    }

    return Mitigation.fromJSON({ ...mitigation, deviceId });
  }

  async revokeMitigation(deviceId: string, mitigationId: string): Promise<Mitigation> {
    const data = await this.post<MitigationApiResponse>(
      'revokeMitigation',
      {},
      { id: deviceId, mitigationId }
    );
    const mitigation = data.mitigation || data.data;

    if (!mitigation) {
      throw new Error(`Mitigation with id ${mitigationId} not found`);
    }

    return Mitigation.fromJSON({ ...mitigation, deviceId });
  }

  async updateDevice(deviceId: string, data: Partial<Device>): Promise<Device> {
    const src = data as Record<string, unknown> & { toJSON?: () => Record<string, unknown> };
    const body: Record<string, unknown> = typeof src.toJSON === 'function' ? { ...src.toJSON() } : { ...src };
    if ('bearerToken' in src) {
      body.bearerToken = src.bearerToken;
    }
    const updateData = await this.put<DeviceApiResponse>(
      'updateDevice',
      body,
      { id: deviceId }
    );
    const device = updateData.device || updateData.data;

    if (!device) {
      throw new Error(`Device with id ${deviceId} not found`);
    }

    return Device.fromJSON(device);
  }

  async deleteDevice(deviceId: string): Promise<void> {
    await this.delete<void>('deleteDevice', { id: deviceId });
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const data = await this.authPost<LoginApiResponse>('login', { email, password });
    // Soportar ambos formatos: snake_case (backend) y camelCase
    return {
      accessToken: data.access_token || data.accessToken || '',
      refreshToken: data.refresh_token || data.refreshToken || '',
      user: data.user
    };
  }

  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    // Backend espera refresh_token (snake_case)
    const data = await this.authPost<LoginApiResponse>('refresh', { refresh_token: refreshToken });
    // El backend solo devuelve access_token, mantener el refresh_token existente
    const accessToken = data.access_token || data.accessToken;
    if (!accessToken) {
      throw new Error('Invalid refresh response: no access token received');
    }
    // Obtener el usuario actual para devolverlo en la respuesta
    let user: UserData;
    try {
      user = data.user || await this.getCurrentUser();
    } catch (error) {
      // Si no se puede obtener el usuario, lanzar error
      throw new Error('Failed to get user after refresh');
    }
    return {
      accessToken: accessToken,
      refreshToken: refreshToken, // Mantener el refresh token existente
      user: user
    };
  }

  async getCurrentUser(): Promise<UserData> {
    const data = await this.get<UserApiResponse>('me');
    const user = data.user || data.data;
    if (!user) {
      throw new Error('User not found');
    }
    return user;
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.put<void>('changePassword', { oldPassword, newPassword });
  }

  async getUsers(page?: number, limit?: number, filters?: UserFilters): Promise<UsersResponse> {
    const params: Record<string, string> = {};
    if (page !== undefined) {
      params.page = page.toString();
    }
    if (limit !== undefined) {
      params.limit = limit.toString();
    }
    if (filters?.email) {
      params.email = filters.email;
    }
    if (filters?.role) {
      params.role = filters.role;
    }
    if (filters?.isActive !== undefined) {
      params.isActive = filters.isActive.toString();
    }

    const data = await this.get<UsersApiResponse>('users', params);
    const rawUsers = data.users || data.data || [];
    const users = rawUsers.map(transformUserData);

    // Support both direct fields and pagination object from API
    const pagination = data.pagination;
    return {
      users,
      total: pagination?.total ?? data.total ?? users.length,
      page: pagination?.page ?? data.page ?? page ?? 1,
      limit: pagination?.per_page ?? data.limit ?? limit ?? 10
    };
  }

  async getUser(id: string): Promise<UserData> {
    const data = await this.get<UserApiResponse>('user', { id });
    const user = data.user || data.data;
    if (!user) {
      throw new Error(`User with id ${id} not found`);
    }
    return user;
  }

  async createUser(email: string, password: string, role: string): Promise<UserData> {
    const data = await this.post<UserApiResponse>('users', { email, password, role });
    const user = data.user || data.data;
    if (!user) {
      throw new Error('Failed to create user');
    }
    return user;
  }

  async updateUserRole(id: string, role: string): Promise<UserData> {
    const data = await this.put<UserApiResponse>('userRole', { role }, { id });
    const user = data.user || data.data;
    if (!user) {
      throw new Error(`User with id ${id} not found`);
    }
    return user;
  }

  async deleteUser(id: string): Promise<void> {
    await this.delete<void>('user', { id });
  }

  async activateUser(id: string): Promise<UserData> {
    const data = await this.post<UserApiResponse>('userActivate', {}, { id });
    const user = data.user || data.data;
    if (!user) {
      throw new Error(`User with id ${id} not found`);
    }
    return user;
  }

  async deactivateUser(id: string): Promise<UserData> {
    const data = await this.post<UserApiResponse>('userDeactivate', {}, { id });
    const user = data.user || data.data;
    if (!user) {
      throw new Error(`User with id ${id} not found`);
    }
    return user;
  }

  async getAccessRules(userId: string): Promise<DeviceAccessRule[]> {
    const data = await this.request<{ rules: DeviceAccessRule[] }>(
      `/users/${userId}/access-rules`,
      { method: 'GET' }
    );
    return data.rules || [];
  }

  async createAccessRule(
    userId: string,
    matchKind: AccessRuleKind,
    matchValue: string
  ): Promise<DeviceAccessRule> {
    const data = await this.request<{ rule: DeviceAccessRule }>(
      `/users/${userId}/access-rules`,
      { method: 'POST', data: { matchKind, matchValue } }
    );
    if (!data.rule) {
      throw new Error('Failed to create access rule');
    }
    return data.rule;
  }

  async deleteAccessRule(userId: string, ruleId: number): Promise<void> {
    await this.request<void>(`/users/${userId}/access-rules/${ruleId}`, { method: 'DELETE' });
  }

  async getEnforcementProfiles(includeInactive: boolean = true): Promise<EnforcementProfileData[]> {
    const data = await this.request<EnforcementProfilesApiResponse>(
      `/admin/enforcement/profiles?include_inactive=${includeInactive ? 'true' : 'false'}`,
      { method: 'GET' }
    );
    return data.profiles || [];
  }

  async createEnforcementProfile(
    payload: Partial<EnforcementProfileData> & { name: string; mode: 'rest' | 'era' }
  ): Promise<EnforcementProfileData> {
    const data = await this.request<EnforcementProfilesApiResponse>(
      '/admin/enforcement/profiles',
      { method: 'POST', data: payload }
    );
    if (!data.profile) {
      throw new Error('Failed to create enforcement profile');
    }
    return data.profile;
  }

  async updateEnforcementProfile(
    id: string,
    payload: Partial<EnforcementProfileData>
  ): Promise<EnforcementProfileData> {
    const data = await this.request<EnforcementProfilesApiResponse>(
      `/admin/enforcement/profiles/${id}`,
      { method: 'PUT', data: payload }
    );
    if (!data.profile) {
      throw new Error(`Failed to update profile ${id}`);
    }
    return data.profile;
  }

  async deleteEnforcementProfile(id: string): Promise<void> {
    await this.request<void>(`/admin/enforcement/profiles/${id}`, { method: 'DELETE' });
  }

  async getEnforcementMappings(includeInactive: boolean = true): Promise<EnforcementMappingData[]> {
    const data = await this.request<EnforcementMappingsApiResponse>(
      `/admin/enforcement/mappings?include_inactive=${includeInactive ? 'true' : 'false'}`,
      { method: 'GET' }
    );
    return data.mappings || [];
  }

  async createEnforcementMapping(
    payload: Partial<EnforcementMappingData> & {
      matchKind: 'explicitProfile' | 'policyType' | 'capability';
      matchValue: string;
      profileId: number;
    }
  ): Promise<EnforcementMappingData> {
    const data = await this.request<EnforcementMappingsApiResponse>(
      '/admin/enforcement/mappings',
      { method: 'POST', data: payload }
    );
    if (!data.mapping) {
      throw new Error('Failed to create enforcement mapping');
    }
    return data.mapping;
  }

  async updateEnforcementMapping(
    id: string,
    payload: Partial<EnforcementMappingData>
  ): Promise<EnforcementMappingData> {
    const data = await this.request<EnforcementMappingsApiResponse>(
      `/admin/enforcement/mappings/${id}`,
      { method: 'PUT', data: payload }
    );
    if (!data.mapping) {
      throw new Error(`Failed to update mapping ${id}`);
    }
    return data.mapping;
  }

  async deleteEnforcementMapping(id: string): Promise<void> {
    await this.request<void>(`/admin/enforcement/mappings/${id}`, { method: 'DELETE' });
  }

  async getEnforcementSecrets(): Promise<EnforcementSecretMetadata[]> {
    const data = await this.request<EnforcementSecretsApiResponse>(
      '/admin/enforcement/secrets',
      { method: 'GET' }
    );
    return data.secrets || [];
  }

  async createEnforcementSecret(name: string, value: string): Promise<EnforcementSecretMetadata> {
    const data = await this.request<EnforcementSecretsApiResponse>(
      '/admin/enforcement/secrets',
      { method: 'POST', data: { name, value } }
    );
    if (!data.secret) {
      throw new Error('Failed to create secret');
    }
    return data.secret;
  }

  async updateEnforcementSecret(
    id: string,
    payload: { name?: string; value?: string }
  ): Promise<EnforcementSecretMetadata> {
    const data = await this.request<EnforcementSecretsApiResponse>(
      `/admin/enforcement/secrets/${id}`,
      { method: 'PUT', data: payload }
    );
    if (!data.secret) {
      throw new Error(`Failed to update secret ${id}`);
    }
    return data.secret;
  }

  async deleteEnforcementSecret(id: string): Promise<void> {
    await this.request<void>(`/admin/enforcement/secrets/${id}`, { method: 'DELETE' });
  }

  async testEnforcementProfile(payload: EnforcementTestRequest): Promise<EnforcementTestResponse> {
    const token = getAccessToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return await this.request<EnforcementTestResponse>(
      '/admin/enforcement/test',
      { method: 'POST', data: payload, headers }
    );
  }

  async getEnforcementExecutions(filters?: {
    from?: string;
    to?: string;
    result?: string;
    deviceId?: string;
    isTest?: boolean;
    profileId?: number;
    limit?: number;
  }): Promise<EnforcementExecutionLog[]> {
    const params = new URLSearchParams();
    if (filters?.from) params.set('from', filters.from);
    if (filters?.to) params.set('to', filters.to);
    if (filters?.result) params.set('result', filters.result);
    if (filters?.deviceId) params.set('deviceId', filters.deviceId);
    if (filters?.isTest !== undefined) params.set('isTest', String(filters.isTest));
    if (filters?.profileId !== undefined) params.set('profileId', String(filters.profileId));
    if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
    const query = params.toString();
    const data = await this.request<EnforcementExecutionsApiResponse>(
      `/admin/enforcement/executions${query ? `?${query}` : ''}`,
      { method: 'GET' }
    );
    return data.executions || [];
  }

  async getUserUiSettings(): Promise<UserUiSettings> {
    return await this.get<UserUiSettings>('userMeSettings');
  }

  async putUserUiSettings(data: { language: string }): Promise<UserUiSettings> {
    return await this.put<UserUiSettings>('userMeSettings', data);
  }

  async getNotificationSettings(): Promise<NotificationSettings> {
    return await this.get<NotificationSettings>('notificationSettings');
  }

  async putNotificationSettings(data: Partial<{
    telegramEnabled: boolean;
    inAppNotificationsEnabled: boolean;
  }>): Promise<NotificationSettings> {
    return await this.put<NotificationSettings>('notificationSettings', data);
  }

  async getNotifications(
    page = 1,
    perPage = 20,
    status?: string,
    readState?: 'unread' | 'read'
  ): Promise<NotificationsListResponse> {
    const qs = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (status) qs.set('status', status);
    if (readState) qs.set('read_state', readState);
    const path = this.config.resolveEndpoint('myNotifications', {});
    return await this.request<NotificationsListResponse>(`${path}?${qs.toString()}`, { method: 'GET' });
  }

  async getUnreadNotificationsCount(): Promise<UnreadNotificationsCountResponse> {
    return await this.get<UnreadNotificationsCountResponse>('notificationsUnreadCount');
  }

  async markNotificationRead(id: number): Promise<void> {
    await this.post<unknown>('notificationRead', {}, { nid: String(id) });
  }

  async markAllNotificationsRead(): Promise<{ updated: number }> {
    return await this.post<{ ok: boolean; updated: number }>('notificationsReadAll', {});
  }

  async createTelegramLinkToken(): Promise<TelegramLinkTokenResponse> {
    return await this.post<TelegramLinkTokenResponse>('telegramLinkToken', {});
  }

  async deleteTelegramLink(): Promise<void> {
    await this.delete<unknown>('telegramUnlink');
  }
}
