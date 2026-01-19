import { BaseApiClient } from '../base/BaseApiClient';
import { ConfigProvider } from '../../../core/adapters/config/ConfigProvider';
import { dossConfig } from './doss.config';
import { Device, DeviceData, Policy, PolicyData, MUD, Passport, PassportData, Threat, ThreatData, Mitigation, MitigationData } from '../../../core/domain';
import { ApplyResult, EnforcementStatus, AuthResponse, UserData, UsersResponse, UserFilters } from '../../../core/ports';

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
  users?: UserData[];
  data?: UserData[];
  total?: number;
  page?: number;
  limit?: number;
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
    // Si se proporciona un nombre, incluirlo en los parámetros de la petición
    const params: Record<string, string> = { id: deviceId };
    if (name) {
      params.name = name;
    }
    
    const data = await this.postXml<ApplyResultApiResponse>('applyPolicy', msplXml, params);
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

  async getDeviceThreats(deviceId: string): Promise<Threat[]> {
    const data = await this.get<ThreatsApiResponse>('threats', { id: deviceId });
    const threats = data.threats || data.data || [];
    
    if (!Array.isArray(threats)) {
      return [];
    }
    
    return threats.map(threat => Threat.fromJSON({ ...threat, deviceId }));
  }

  async getDeviceMitigations(deviceId: string): Promise<Mitigation[]> {
    const data = await this.get<MitigationsApiResponse>('mitigations', { id: deviceId });
    const mitigations = data.mitigations || data.data || [];
    
    if (!Array.isArray(mitigations)) {
      return [];
    }
    
    return mitigations.map(mitigation => Mitigation.fromJSON({ ...mitigation, deviceId }));
  }

  async enforceMitigation(deviceId: string, mitigationId: string): Promise<Mitigation> {
    const data = await this.post<MitigationApiResponse>(
      'enforceMitigation',
      {},
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
    const updateData = await this.put<DeviceApiResponse>(
      'updateDevice',
      data.toJSON ? data.toJSON() : data,
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
    return {
      users: data.users || data.data || [],
      total: data.total || (data.users || data.data || []).length,
      page: data.page || page || 1,
      limit: data.limit || limit || 10
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
}

