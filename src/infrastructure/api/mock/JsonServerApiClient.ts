import { BaseApiClient } from '../base/BaseApiClient';
import { ConfigProvider } from '../../../core/adapters/config/ConfigProvider';
import { jsonServerConfig } from './json-server.config';
import { Device, DeviceData, Policy, PolicyData, MUD, MUDData, Passport, PassportData, Threat, ThreatData, Mitigation, MitigationData } from '../../../core/domain';
import { ApplyResult, EnforcementStatus, AuthResponse, UserData, UsersResponse, UserFilters } from '../../../core/ports';

/**
 * JsonServerApiClient - Implementación para JSON Server
 * Consume la API REST del servidor mock JSON Server
 */
export class JsonServerApiClient extends BaseApiClient {
  constructor(onTokenRefresh?: () => Promise<void>, onAuthError?: () => void) {
    const configProvider = new ConfigProvider(jsonServerConfig);
    super(configProvider, onTokenRefresh, onAuthError);
  }

  async getDevices(): Promise<Device[]> {
    // JSON Server devuelve directamente el array
    const devices = await this.get<DeviceData[]>('devices');

    if (!Array.isArray(devices)) {
      return [];
    }

    return devices.map(device => Device.fromJSON(device));
  }

  async getDevice(id: string): Promise<Device> {
    // JSON Server devuelve directamente el objeto
    const device = await this.get<DeviceData>('device', { id });

    if (!device) {
      throw new Error(`Device with id ${id} not found`);
    }

    return Device.fromJSON(device);
  }

  async getDevicePassport(id: string): Promise<Passport> {
    // JSON Server devuelve un array filtrado, tomar el primer elemento
    const passports = await this.get<PassportData[]>('passport', { deviceId: id });

    if (!Array.isArray(passports) || passports.length === 0) {
      // Si no existe, crear uno por defecto
      return Passport.fromJSON({
        deviceId: id,
        data: {
          deviceId: id,
          serialNumber: `SN-${id.toUpperCase()}`,
          firmwareVersion: '1.0.0',
          hardwareVersion: '1.0',
          manufacturer: 'Unknown',
          model: 'Unknown',
          certification: 'CE-2024',
          productionDate: new Date().toISOString().split('T')[0],
          metadata: {
            onboardingDate: new Date().toISOString().split('T')[0],
            lastUpdate: new Date().toISOString()
          }
        }
      });
    }

    return Passport.fromJSON(passports[0]);
  }

  async getDeviceMUD(id: string): Promise<MUD> {
    // JSON Server devuelve un array filtrado, tomar el primer elemento
    const muds = await this.get<MUDData[]>('mud', { deviceId: id });

    if (!Array.isArray(muds) || muds.length === 0) {
      // Si no existe, crear uno por defecto
      return MUD.fromJSON({
        id: `mud-${id}`,
        deviceId: id,
        mudVersion: 1,
        mudUrl: `https://example.com/mud/${id}`,
        lastUpdate: new Date().toISOString(),
        cacheValidity: 48,
        isSupported: true,
        systeminfo: 'Linux 5.4.0',
        mfgName: 'Unknown',
        documentation: 'https://example.com/docs',
        modelName: 'Unknown',
        mudData: {
          'ietf-mud:mud': {
            'mud-version': 1,
            'mud-url': `https://example.com/mud/${id}`,
            'last-update': new Date().toISOString(),
            'cache-validity': 48,
            'is-supported': true,
            'systeminfo': 'Linux 5.4.0',
            'mfg-name': 'Unknown',
            'documentation': 'https://example.com/docs',
            'model-name': 'Unknown'
          }
        }
      });
    }

    return MUD.fromJSON(muds[0]);
  }

  async getDevicePolicies(id: string): Promise<Policy[]> {
    // JSON Server devuelve directamente el array filtrado
    const policies = await this.get<PolicyData[]>('policies', { deviceId: id });

    if (!Array.isArray(policies)) {
      return [];
    }

    return policies.map(policy => Policy.fromJSON(policy));
  }

  async applyIDSP2(deviceId: string, idsp2Id: string): Promise<ApplyResult> {
    // Para JSON Server, crear una nueva política con el IDSP2
    const newPolicy: PolicyData = {
      id: `policy-${Date.now()}`,
      deviceId,
      name: `IDSP2 Policy: ${idsp2Id}`,
      msplXml: `<ITResourceOrchestration id="${idsp2Id}"><ITResource id="idsp2_${idsp2Id}"/></ITResourceOrchestration>`,
      status: 'pending',
      appliedAt: new Date().toISOString(),
      enforcementStatus: 'pending'
    };

    // Crear la política directamente en la colección policies
    await this.request<PolicyData>('/policies', {
      method: 'POST',
      data: newPolicy
    });

    return {
      status: 'pending',
      message: `IDSP2 ${idsp2Id} application initiated for device ${deviceId}`
    };
  }

  async applyPolicy(deviceId: string, msplXml: string, name?: string): Promise<ApplyResult> {
    // Crear nueva política en JSON Server
    const newPolicy: PolicyData = {
      id: `policy-${Date.now()}`,
      deviceId,
      name: name || 'New Policy',
      msplXml,
      status: 'pending',
      appliedAt: new Date().toISOString(),
      enforcementStatus: 'pending'
    };

    // Crear la política directamente en la colección policies
    await this.request<PolicyData>('/policies', {
      method: 'POST',
      data: newPolicy
    });

    return {
      status: 'pending',
      message: `Policy application initiated for device ${deviceId}`
    };
  }

  async getEnforcementStatus(deviceId: string): Promise<EnforcementStatus> {
    // JSON Server devuelve un array filtrado, tomar el primer elemento
    const statuses = await this.get<EnforcementStatus[]>('enforcementStatus', { deviceId });

    if (!Array.isArray(statuses) || statuses.length === 0) {
      // Si no existe, crear uno por defecto
      return {
        status: 'pending',
        message: 'Enforcement status: pending',
        timestamp: new Date().toISOString()
      };
    }

    return statuses[0];
  }

  async enforcePolicy(deviceId: string, policyId: string): Promise<ApplyResult> {
    const existingPolicy = await this.request<PolicyData>(`/policies/${policyId}`, {
      method: 'GET'
    });

    if (!existingPolicy) {
      throw new Error(`Policy with id ${policyId} not found`);
    }

    const now = new Date().toISOString();
    await this.patch<PolicyData>(
      'enforcePolicy',
      {
        status: 'active',
        enforcementStatus: 'completed',
        appliedAt: now
      },
      { policyId }
    );

    return {
      status: 'completed',
      message: `Policy ${policyId} enforced for device ${deviceId}`
    };
  }

  async getDeviceThreats(deviceId: string): Promise<Threat[]> {
    // JSON Server devuelve directamente el array filtrado
    const threats = await this.get<ThreatData[]>('threats', { deviceId });

    if (!Array.isArray(threats)) {
      return [];
    }

    return threats.map(threat => Threat.fromJSON({ ...threat, deviceId }));
  }

  async getDeviceMitigations(deviceId: string): Promise<Mitigation[]> {
    // JSON Server devuelve directamente el array filtrado
    const mitigations = await this.get<MitigationData[]>('mitigations', { deviceId });

    if (!Array.isArray(mitigations)) {
      return [];
    }

    return mitigations.map(mitigation => Mitigation.fromJSON(mitigation));
  }

  async enforceMitigation(deviceId: string, mitigationId: string): Promise<Mitigation> {
    // Obtener la mitigación actual directamente por ID usando request con endpoint relativo
    const mitigation = await this.request<MitigationData>(
      `/mitigations/${mitigationId}`,
      { method: 'GET' }
    );

    if (!mitigation) {
      throw new Error(`Mitigation with id ${mitigationId} not found`);
    }

    // Actualizar con PATCH usando el método helper de BaseApiClient
    const updatedMitigation = await this.patch<MitigationData>(
      'enforceMitigation',
      {
        is_enforced: true,
        enforcement_timestamp: new Date().toISOString(),
        last_enforced: new Date().toISOString()
      },
      { mitigationId }
    );

    return Mitigation.fromJSON({ ...updatedMitigation, deviceId });
  }

  async revokeMitigation(deviceId: string, mitigationId: string): Promise<Mitigation> {
    // Obtener la mitigación actual directamente por ID usando request con endpoint relativo
    const mitigation = await this.request<MitigationData>(
      `/mitigations/${mitigationId}`,
      { method: 'GET' }
    );

    if (!mitigation) {
      throw new Error(`Mitigation with id ${mitigationId} not found`);
    }

    // Actualizar con PATCH usando el método helper de BaseApiClient
    const updatedMitigation = await this.patch<MitigationData>(
      'revokeMitigation',
      {
        is_enforced: false,
        enforcement_timestamp: null,
        last_enforced: null
      },
      { mitigationId }
    );

    return Mitigation.fromJSON({ ...updatedMitigation, deviceId });
  }

  async updateDevice(deviceId: string, data: Partial<Device>): Promise<Device> {
    // Obtener el dispositivo actual
    const currentDevice = await this.get<DeviceData>('device', { id: deviceId });

    if (!currentDevice) {
      throw new Error(`Device with id ${deviceId} not found`);
    }

    // Preparar datos de actualización
    const updateData: Partial<DeviceData> = {
      ...currentDevice,
      ...(data.toJSON ? data.toJSON() : data),
      updatedAt: new Date().toISOString()
    };

    // Actualizar con PUT
    const updatedDevice = await this.put<DeviceData>('updateDevice', updateData, { id: deviceId });

    return Device.fromJSON(updatedDevice);
  }

  async deleteDevice(deviceId: string): Promise<void> {
    await this.delete<void>('deleteDevice', { id: deviceId });
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    // Mock: buscar usuario en la colección users
    const users = await this.get<UserData[]>('users');
    const user = users.find(u => u.email === email);

    if (!user) {
      throw new Error('Invalid credentials');
    }

    // Mock: validar password (en producción esto sería un hash)
    // Para el mock, asumimos que el password es válido si el usuario existe
    // En un mock real, podrías tener un campo password_hash y compararlo

    // Generar tokens mock (en producción estos serían JWT reales)
    const accessToken = `mock_access_token_${user.id}_${Date.now()}`;
    const refreshToken = `mock_refresh_token_${user.id}_${Date.now()}`;

    return {
      accessToken,
      refreshToken,
      user
    };
  }

  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    // Mock: validar refresh token y generar nuevos tokens
    // En un mock real, podrías almacenar los tokens y validarlos
    const tokenParts = refreshToken.split('_');
    if (tokenParts.length < 4 || tokenParts[0] !== 'mock' || tokenParts[1] !== 'refresh') {
      throw new Error('Invalid refresh token');
    }

    const userId = tokenParts[2];
    const user = await this.getUser(userId);

    // Generar nuevos tokens
    const newAccessToken = `mock_access_token_${user.id}_${Date.now()}`;
    const newRefreshToken = `mock_refresh_token_${user.id}_${Date.now()}`;

    return {
      accessToken: newAccessToken,
      refreshToken: newRefreshToken,
      user
    };
  }

  async getCurrentUser(): Promise<UserData> {
    // Mock: obtener usuario del token (simplificado)
    // En producción, el backend decodificaría el token
    const users = await this.get<UserData[]>('users');
    // Por ahora, devolver el primer usuario (en producción vendría del token)
    if (users.length === 0) {
      throw new Error('User not found');
    }
    return users[0];
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    // Mock: actualizar password del usuario actual
    // En producción, esto validaría el oldPassword y actualizaría el hash
    const user = await this.getCurrentUser();
    // En un mock real, actualizarías el password en la base de datos
    // Por ahora, solo validamos que el usuario existe
    if (!user) {
      throw new Error('User not found');
    }
  }

  async getUsers(page?: number, limit?: number, filters?: UserFilters): Promise<UsersResponse> {
    // JSON Server soporta paginación con _page y _limit
    const params: Record<string, string> = {};
    if (page !== undefined) {
      params._page = page.toString();
    }
    if (limit !== undefined) {
      params._limit = limit.toString();
    }
    if (filters?.email) {
      params.email_like = filters.email;
    }
    if (filters?.role) {
      params.role = filters.role;
    }
    if (filters?.isActive !== undefined) {
      params.isActive = filters.isActive.toString();
    }

    const users = await this.get<UserData[]>('users', params);
    const total = users.length; // En un mock real, necesitarías un endpoint que devuelva el total

    return {
      users: users || [],
      total,
      page: page || 1,
      limit: limit || 10
    };
  }

  async getUser(id: string): Promise<UserData> {
    const user = await this.get<UserData>('user', { id });
    if (!user) {
      throw new Error(`User with id ${id} not found`);
    }
    return user;
  }

  async createUser(email: string, password: string, role: string): Promise<UserData> {
    const newUser: UserData = {
      id: `user_${Date.now()}`,
      email,
      role,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    const user = await this.post<UserData>('users', newUser);
    return user;
  }

  async updateUserRole(id: string, role: string): Promise<UserData> {
    const currentUser = await this.getUser(id);
    const updatedUser = await this.put<UserData>('user', { ...currentUser, role }, { id });
    return updatedUser;
  }

  async deleteUser(id: string): Promise<void> {
    await this.delete<void>('user', { id });
  }

  async activateUser(id: string): Promise<UserData> {
    const currentUser = await this.getUser(id);
    const updatedUser = await this.put<UserData>('user', { ...currentUser, isActive: true }, { id });
    return updatedUser;
  }

  async deactivateUser(id: string): Promise<UserData> {
    const currentUser = await this.getUser(id);
    const updatedUser = await this.put<UserData>('user', { ...currentUser, isActive: false }, { id });
    return updatedUser;
  }
}
