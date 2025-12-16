/**
 * Mitigation Entity
 * Representa una mitigación asociada a un dispositivo y opcionalmente a un threat
 */
export interface MitigationData {
  id: string;
  deviceId: string;
  threatId?: string;
  name: string;
  description?: string;
  mitigation_actions: string; // XML/JSON
  is_enforced: boolean;
  last_enforced?: string;
  enforcement_timestamp?: string;
}

export class Mitigation {
  id: string;
  deviceId: string;
  threatId?: string;
  name: string;
  description?: string;
  mitigation_actions: string;
  is_enforced: boolean;
  last_enforced?: string;
  enforcement_timestamp?: string;

  constructor({
    id,
    deviceId,
    threatId,
    name,
    description,
    mitigation_actions,
    is_enforced,
    last_enforced,
    enforcement_timestamp
  }: MitigationData) {
    this.id = id;
    this.deviceId = deviceId;
    this.threatId = threatId;
    this.name = name;
    this.description = description;
    this.mitigation_actions = mitigation_actions;
    this.is_enforced = is_enforced;
    this.last_enforced = last_enforced;
    this.enforcement_timestamp = enforcement_timestamp;
  }

  static fromJSON(json: MitigationData | any): Mitigation {
    return new Mitigation({
      id: json.id || '',
      deviceId: json.deviceId || json.device_id || '',
      threatId: json.threatId || json.threat_id,
      name: json.name || '',
      description: json.description,
      mitigation_actions: json.mitigation_actions || json.mitigationActions || '',
      is_enforced: json.is_enforced !== undefined ? json.is_enforced : (json.isEnforced !== undefined ? json.isEnforced : false),
      last_enforced: json.last_enforced || json.lastEnforced,
      enforcement_timestamp: json.enforcement_timestamp || json.enforcementTimestamp
    });
  }

  toJSON(): MitigationData {
    return {
      id: this.id,
      deviceId: this.deviceId,
      threatId: this.threatId,
      name: this.name,
      description: this.description,
      mitigation_actions: this.mitigation_actions,
      is_enforced: this.is_enforced,
      last_enforced: this.last_enforced,
      enforcement_timestamp: this.enforcement_timestamp
    };
  }
}
