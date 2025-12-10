/**
 * Policy Entity
 * Representa una política MSPL aplicada
 */
export interface PolicyData {
  id: string;
  deviceId: string;
  name?: string;
  msplXml: string;
  status?: string;
  appliedAt?: string;
  enforcementStatus?: string;
}

export class Policy {
  id: string;
  deviceId: string;
  name?: string;
  msplXml: string;
  status: string;
  appliedAt?: string;
  enforcementStatus: string;

  constructor({
    id,
    deviceId,
    name,
    msplXml,
    status = 'pending',
    appliedAt,
    enforcementStatus = 'pending'
  }: PolicyData) {
    this.id = id;
    this.deviceId = deviceId;
    this.name = name;
    this.msplXml = msplXml;
    this.status = status;
    this.appliedAt = appliedAt;
    this.enforcementStatus = enforcementStatus;
  }

  static fromJSON(json: PolicyData): Policy {
    return new Policy(json);
  }

  toJSON(): PolicyData {
    return {
      id: this.id,
      deviceId: this.deviceId,
      name: this.name,
      msplXml: this.msplXml,
      status: this.status,
      appliedAt: this.appliedAt,
      enforcementStatus: this.enforcementStatus
    };
  }
}

