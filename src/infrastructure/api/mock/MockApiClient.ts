import { IApiClient, ApplyResult, EnforcementStatus } from '../../../core/ports/IApiClient';
import { Device } from '../../../core/domain/entities/Device';
import { Policy } from '../../../core/domain/entities/Policy';
import { MUD } from '../../../core/domain/entities/MUD';
import { Passport } from '../../../core/domain/entities/Passport';
import { Threat } from '../../../core/domain/entities/Threat';
import { Mitigation } from '../../../core/domain/entities/Mitigation';

interface MockDeviceData {
  id: string;
  name: string;
  type: string;
  manufacturer: string;
  model: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  ip?: string;
  mac?: string;
  identifier?: string;
  mudurl?: string;
  mudfile?: string;
  mitigation_actions?: string;
  inventory_id?: string;
  edk?: string;
}

interface MockPolicyData {
  id: string;
  deviceId: string;
  name: string;
  msplXml: string;
  status: string;
  appliedAt: string;
  enforcementStatus: string;
}

/**
 * MockApiClient - Implementación mock para desarrollo y testing
 * Devuelve datos de ejemplo sin necesidad de backend
 */
export class MockApiClient extends IApiClient {
  private mockDevices: MockDeviceData[];
  private mockPolicies: Record<string, MockPolicyData[]>;
  private mockThreats: Record<string, any[]>;
  private mockMitigations: Record<string, any[]>;

  constructor() {
    super();
    this.mockDevices = [
      {
        id: 'device-1',
        name: 'IoT Sensor 001',
        type: 'sensor',
        manufacturer: 'TechCorp',
        model: 'TC-SENSOR-V2',
        status: 'active',
        createdAt: '2024-01-15T10:00:00Z',
        updatedAt: '2024-01-20T14:30:00Z',
        ip: '192.168.1.100',
        mac: '00:1B:44:11:3A:B7',
        identifier: 'a1b2c3d4-e5f6-7890-1234-567890abcdef',
        mudurl: 'https://example.com/mud/device-1.json',
        inventory_id: 'INV-001'
      },
      {
        id: 'device-2',
        name: 'Smart Camera 002',
        type: 'camera',
        manufacturer: 'SecureCam',
        model: 'SC-IP-CAM-4K',
        status: 'active',
        createdAt: '2024-01-16T09:00:00Z',
        updatedAt: '2024-01-21T11:20:00Z',
        ip: '192.168.1.101',
        mac: '00:1B:44:11:3A:B8',
        identifier: 'b2c3d4e5-f6a7-8901-2345-678901bcdefg',
        mudurl: 'https://example.com/mud/device-2.json',
        inventory_id: 'INV-002'
      },
      {
        id: 'device-3',
        name: 'Gateway Router 003',
        type: 'gateway',
        manufacturer: 'NetWorks',
        model: 'NW-GW-PRO',
        status: 'active',
        createdAt: '2024-01-17T08:00:00Z',
        updatedAt: '2024-01-22T16:45:00Z',
        ip: '192.168.1.1',
        mac: '00:1B:44:11:3A:B9',
        identifier: 'c3d4e5f6-a7b8-9012-3456-789012cdefgh',
        mudurl: 'https://example.com/mud/device-3.json',
        inventory_id: 'INV-003'
      }
    ];

    this.mockPolicies = {
      'device-1': [
        {
          id: 'policy-1',
          deviceId: 'device-1',
          name: 'Firewall Policy',
          msplXml: '<ITResourceOrchestration id="omspl_123"><ITResource id="mspl_456"/></ITResourceOrchestration>',
          status: 'active',
          appliedAt: '2024-01-20T14:30:00Z',
          enforcementStatus: 'completed'
        }
      ],
      'device-2': [],
      'device-3': []
    };

    this.mockThreats = {
      'device-1': [
        {
          id: 'threat-1',
          identifier: 'CVE-2024-0001',
          threat_mud_url: 'https://example.com/threats/cve-2024-0001.json',
          threat_mud_file: '{"ietf-threatmud:mud": {"threat-description": "Example threat"}}',
          mitigation_actions: '<mitigation>Example mitigation</mitigation>'
        }
      ],
      'device-2': [],
      'device-3': []
    };

    this.mockMitigations = {
      'device-1': [
        {
          id: 'mitigation-1',
          deviceId: 'device-1',
          threatId: 'threat-1',
          name: 'Firewall Rule Block',
          description: 'Block malicious traffic from threat source',
          mitigation_actions: '<configuration-action><firewall><block>true</block></firewall></configuration-action>',
          is_enforced: false,
          last_enforced: undefined,
          enforcement_timestamp: undefined
        },
        {
          id: 'mitigation-2',
          deviceId: 'device-1',
          threatId: 'threat-1',
          name: 'Port Filtering',
          description: 'Filter specific ports',
          mitigation_actions: '{"action": "filter", "ports": [8080, 8443]}',
          is_enforced: true,
          last_enforced: '2024-01-20T14:30:00Z',
          enforcement_timestamp: '2024-01-20T14:30:00Z'
        }
      ],
      'device-2': [],
      'device-3': []
    };
  }

  // Simula delay de red
  private async delay(ms: number = 500): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async getDevices(): Promise<Device[]> {
    await this.delay(300);
    console.log('getDevices');
    return this.mockDevices.map(device => Device.fromJSON(device));
  }

  async getDevice(id: string): Promise<Device> {
    await this.delay(200);
    console.log('getDevice', id);
    const device = this.mockDevices.find(d => d.id === id);
    if (!device) {
      throw new Error(`Device with id ${id} not found`);
    }
    return Device.fromJSON(device);
  }

  async getDevicePassport(id: string): Promise<Passport> {
    await this.delay(200);
    return Passport.fromJSON({
      deviceId: id,
      data: {
        deviceId: id,
        serialNumber: `SN-${id.toUpperCase()}`,
        firmwareVersion: '1.2.3',
        hardwareVersion: '2.0',
        manufacturer: 'TechCorp',
        model: 'TC-SENSOR-V2',
        certification: 'CE-2024',
        productionDate: '2024-01-01',
        metadata: {
          onboardingDate: '2024-01-15',
          lastUpdate: '2024-01-20'
        }
      }
    });
  }

  async getDeviceMUD(id: string): Promise<MUD> {
    await this.delay(200);
    console.log('getDeviceMUD', id);
    return MUD.fromJSON({
      id: `mud-${id}`,
      deviceId: id,
      mudVersion: 1,
      mudUrl: `https://example.com/mud/${id}`,
      lastUpdate: '2024-01-20T14:30:00Z',
      cacheValidity: 48,
      isSupported: true,
      systeminfo: 'Linux 5.4.0',
      mfgName: 'TechCorp',
      documentation: 'https://example.com/docs',
      modelName: 'TC-SENSOR-V2',
      mudData: {
        'ietf-mud:mud': {
          'mud-version': 1,
          'mud-url': `https://example.com/mud/${id}`,
          'last-update': '2024-01-20T14:30:00Z',
          'cache-validity': 48,
          'is-supported': true,
          'systeminfo': 'Linux 5.4.0',
          'mfg-name': 'TechCorp',
          'documentation': 'https://example.com/docs',
          'model-name': 'TC-SENSOR-V2'
        }
      }
    });
  }

  async getDevicePolicies(id: string): Promise<Policy[]> {
    await this.delay(200);
    const policies = this.mockPolicies[id] || [];
    return policies.map(policy => Policy.fromJSON(policy));
  }

  async applyIDSP2(deviceId: string, idsp2Id: string): Promise<ApplyResult> {
    await this.delay(1000);
    // Simula éxito
    console.log('applyIDSP2', deviceId, idsp2Id);
    return {
      status: 'pending',
      message: `IDSP2 ${idsp2Id} application initiated for device ${deviceId}`
    };
  }

  async applyPolicy(deviceId: string, msplXml: string): Promise<ApplyResult> {
    await this.delay(1000);
    // Simula éxito
    console.log('applyPolicy', deviceId, msplXml);
    const newPolicy: MockPolicyData = {
      id: `policy-${Date.now()}`,
      deviceId,
      name: 'New Policy',
      msplXml,
      status: 'pending',
      appliedAt: new Date().toISOString(),
      enforcementStatus: 'pending'
    };
    
    if (!this.mockPolicies[deviceId]) {
      this.mockPolicies[deviceId] = [];
    }
    this.mockPolicies[deviceId].push(newPolicy);

    return {
      status: 'pending',
      message: `Policy application initiated for device ${deviceId}`
    };
  }

  async getEnforcementStatus(deviceId: string): Promise<EnforcementStatus> {
    await this.delay(200);
    console.log('getEnforcementStatus', deviceId);
    // Simula estado aleatorio para testing
    const statuses: string[] = ['pending', 'completed', 'error'];
    const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
    
    return {
      status: randomStatus,
      message: `Enforcement status: ${randomStatus}`,
      timestamp: new Date().toISOString()
    };
  }

  async getDeviceThreats(deviceId: string): Promise<Threat[]> {
    await this.delay(300);
    console.log('getDeviceThreats', deviceId);
    const threats = this.mockThreats[deviceId] || [];
    return threats.map(threat => Threat.fromJSON({ ...threat, deviceId }));
  }

  async getDeviceMitigations(deviceId: string): Promise<Mitigation[]> {
    await this.delay(300);
    console.log('getDeviceMitigations', deviceId);
    const mitigations = this.mockMitigations[deviceId] || [];
    return mitigations.map(mitigation => Mitigation.fromJSON(mitigation));
  }

  async enforceMitigation(deviceId: string, mitigationId: string): Promise<Mitigation> {
    await this.delay(800);
    console.log('enforceMitigation', deviceId, mitigationId);
    const mitigations = this.mockMitigations[deviceId] || [];
    const mitigation = mitigations.find(m => m.id === mitigationId);
    
    if (!mitigation) {
      throw new Error(`Mitigation with id ${mitigationId} not found`);
    }

    // Actualizar estado
    mitigation.is_enforced = true;
    mitigation.enforcement_timestamp = new Date().toISOString();
    mitigation.last_enforced = new Date().toISOString();

    return Mitigation.fromJSON(mitigation);
  }

  async revokeMitigation(deviceId: string, mitigationId: string): Promise<Mitigation> {
    await this.delay(800);
    console.log('revokeMitigation', deviceId, mitigationId);
    const mitigations = this.mockMitigations[deviceId] || [];
    const mitigation = mitigations.find(m => m.id === mitigationId);
    
    if (!mitigation) {
      throw new Error(`Mitigation with id ${mitigationId} not found`);
    }

    // Actualizar estado
    mitigation.is_enforced = false;
    mitigation.enforcement_timestamp = undefined;
    mitigation.last_enforced = undefined;

    return Mitigation.fromJSON(mitigation);
  }

  async updateDevice(deviceId: string, data: Partial<Device>): Promise<Device> {
    await this.delay(500);
    console.log('updateDevice', deviceId, data);
    const device = this.mockDevices.find(d => d.id === deviceId);
    
    if (!device) {
      throw new Error(`Device with id ${deviceId} not found`);
    }

    // Actualizar campos permitidos
    if (data.ip !== undefined) device.ip = data.ip;
    if (data.mac !== undefined) device.mac = data.mac;
    if (data.model !== undefined) device.model = data.model;
    if (data.mudurl !== undefined) device.mudurl = data.mudurl;
    device.updatedAt = new Date().toISOString();

    return Device.fromJSON(device as any);
  }

  async deleteDevice(deviceId: string): Promise<void> {
    await this.delay(500);
    console.log('deleteDevice', deviceId);
    const index = this.mockDevices.findIndex(d => d.id === deviceId);
    
    if (index === -1) {
      throw new Error(`Device with id ${deviceId} not found`);
    }

    this.mockDevices.splice(index, 1);
    delete this.mockPolicies[deviceId];
    delete this.mockThreats[deviceId];
    delete this.mockMitigations[deviceId];
  }
}

