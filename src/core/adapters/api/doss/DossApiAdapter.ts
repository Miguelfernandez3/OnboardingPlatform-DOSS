import { BaseApiClient } from '../base/BaseApiClient';
import { ConfigProvider } from '../../config/ConfigProvider';
import { dossConfig } from './doss.config';
import { Device, DeviceData, Policy, PolicyData, MUD, Passport, PassportData, Threat, ThreatData, Mitigation, MitigationData } from '../../../domain';
import { ApplyResult, EnforcementStatus } from '../../../ports';

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

/**
 * DossApiAdapter - Implementación específica para DOSS
 * Extiende BaseApiClient e implementa los métodos específicos de DOSS
 */
export class DossApiAdapter extends BaseApiClient {
  constructor() {
    const configProvider = new ConfigProvider(dossConfig);
    super(configProvider);
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

  async applyPolicy(deviceId: string, msplXml: string): Promise<ApplyResult> {
    const data = await this.postXml<ApplyResultApiResponse>('applyPolicy', msplXml, { id: deviceId });
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
}

