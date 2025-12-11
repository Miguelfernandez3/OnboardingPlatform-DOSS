/**
 * Threat Entity
 * Representa una amenaza asociada a un dispositivo
 */
export interface ThreatData {
  id: string;
  identifier: string;
  threat_mud_url?: string;
  threat_mud_file?: string;
  mitigation_actions?: string;
  deviceId?: string;
}

export class Threat {
  id: string;
  identifier: string;
  threat_mud_url?: string;
  threat_mud_file?: string;
  mitigation_actions?: string;
  deviceId?: string;

  constructor({
    id,
    identifier,
    threat_mud_url,
    threat_mud_file,
    mitigation_actions,
    deviceId
  }: ThreatData) {
    this.id = id;
    this.identifier = identifier;
    this.threat_mud_url = threat_mud_url;
    this.threat_mud_file = threat_mud_file;
    this.mitigation_actions = mitigation_actions;
    this.deviceId = deviceId;
  }

  static fromJSON(json: ThreatData | any): Threat {
    return new Threat({
      id: json.id || '',
      identifier: json.identifier || '',
      threat_mud_url: json.threat_mud_url || json.threatMudUrl,
      threat_mud_file: json.threat_mud_file || json.threatMudFile,
      mitigation_actions: json.mitigation_actions || json.mitigationActions,
      deviceId: json.deviceId || json.device_id
    });
  }

  toJSON(): ThreatData {
    return {
      id: this.id,
      identifier: this.identifier,
      threat_mud_url: this.threat_mud_url,
      threat_mud_file: this.threat_mud_file,
      mitigation_actions: this.mitigation_actions,
      deviceId: this.deviceId
    };
  }
}
