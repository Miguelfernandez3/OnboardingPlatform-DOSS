import { BaseApiClient } from '../../../core/adapters/api/base/BaseApiClient';
import { ConfigProvider } from '../../../core/adapters/config/ConfigProvider';
import { jsonServerConfig } from './json-server.config';
import { Device, DeviceData, Policy, PolicyData, MUD, MUDData, Passport, PassportData, Threat, ThreatData, Mitigation, MitigationData } from '../../../core/domain';
import { ApplyResult, EnforcementStatus } from '../../../core/ports';

/**
 * JsonServerApiClient - Implementación para JSON Server
 * Consume la API REST del servidor mock JSON Server
 */
export class JsonServerApiClient extends BaseApiClient {
  constructor() {
    const configProvider = new ConfigProvider(jsonServerConfig);
    super(configProvider);
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

  async applyPolicy(deviceId: string, msplXml: string): Promise<ApplyResult> {
    // Crear nueva política en JSON Server
    const newPolicy: PolicyData = {
      id: `policy-${Date.now()}`,
      deviceId,
      name: 'New Policy',
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
}
