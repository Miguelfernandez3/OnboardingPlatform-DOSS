import { IApiClient, ApplyResult, EnforcementStatus } from '../../../core/ports/IApiClient';
import { Device } from '../../../core/domain/entities/Device';
import { Policy } from '../../../core/domain/entities/Policy';
import { MUD } from '../../../core/domain/entities/MUD';
import { Passport } from '../../../core/domain/entities/Passport';

interface MockDeviceData {
  id: string;
  name: string;
  type: string;
  manufacturer: string;
  model: string;
  status: string;
  createdAt: string;
  updatedAt: string;
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
        updatedAt: '2024-01-20T14:30:00Z'
      },
      {
        id: 'device-2',
        name: 'Smart Camera 002',
        type: 'camera',
        manufacturer: 'SecureCam',
        model: 'SC-IP-CAM-4K',
        status: 'active',
        createdAt: '2024-01-16T09:00:00Z',
        updatedAt: '2024-01-21T11:20:00Z'
      },
      {
        id: 'device-3',
        name: 'Gateway Router 003',
        type: 'gateway',
        manufacturer: 'NetWorks',
        model: 'NW-GW-PRO',
        status: 'active',
        createdAt: '2024-01-17T08:00:00Z',
        updatedAt: '2024-01-22T16:45:00Z'
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
}

