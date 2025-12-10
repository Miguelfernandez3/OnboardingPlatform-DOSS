import { BaseApiClient } from '../base/BaseApiClient';
import { ConfigProvider } from '../../config/ConfigProvider';
import { dossConfig } from './doss.config';
import { Device, DeviceData, Policy, PolicyData, MUD, Passport, PassportData } from '../../../domain';
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
}

