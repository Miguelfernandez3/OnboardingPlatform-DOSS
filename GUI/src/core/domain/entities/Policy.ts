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
  policyType?: string;
  source?: string;
  canEnforce?: boolean;
}

export class Policy {
  id: string;
  deviceId: string;
  name?: string;
  msplXml: string;
  status: string;
  appliedAt?: string;
  enforcementStatus: string;
  policyType?: string;
  source?: string;
  canEnforce: boolean;

  constructor({
    id,
    deviceId,
    name,
    msplXml,
    status = 'pending',
    appliedAt,
    enforcementStatus = 'pending',
    policyType,
    source,
    canEnforce = true
  }: PolicyData) {
    this.id = id;
    this.deviceId = deviceId;
    this.name = name;
    this.msplXml = msplXml;
    this.status = status;
    this.appliedAt = appliedAt;
    this.enforcementStatus = enforcementStatus;
    this.policyType = policyType;
    this.source = source;
    this.canEnforce = canEnforce;
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
      enforcementStatus: this.enforcementStatus,
      policyType: this.policyType,
      source: this.source,
      canEnforce: this.canEnforce
    };
  }
}
