/**
 * Mitigation Entity
 * Representa una mitigación asociada a un dispositivo y opcionalmente a un threat
 */
export type MitigationEnforcementGaps = {
  missing: Array<Record<string, unknown>>;
  warnings: string[];
  ready: boolean;
};

function normalizeEnforcementGaps(
  raw: unknown
): MitigationEnforcementGaps | undefined {
  if (raw === null || raw === undefined || typeof raw !== 'object' || Array.isArray(raw)) {
    return undefined;
  }
  const o = raw as Record<string, unknown>;
  const missing = o.missing;
  const warnings = o.warnings;
  const ready = o.ready;
  return {
    missing: Array.isArray(missing) ? (missing as Array<Record<string, unknown>>) : [],
    warnings: Array.isArray(warnings) ? warnings.map((w) => String(w)) : [],
    ready: typeof ready === 'boolean' ? ready : (Array.isArray(missing) ? missing.length === 0 : true)
  };
}

export interface MitigationData {
  id: string;
  deviceId: string;
  threatId?: string;
  name: string;
  description?: string;
  mitigation_actions: string | string[]; // XML/JSON or multiple MSPLs
  is_enforced: boolean;
  last_enforced?: string;
  enforcement_timestamp?: string;
  /** Server-computed: missing context before enforce (same as enforcement-gaps MSPL) */
  enforcementGaps?: MitigationEnforcementGaps;
}

export class Mitigation {
  id: string;
  deviceId: string;
  threatId?: string;
  name: string;
  description?: string;
  mitigation_actions: string | string[];
  is_enforced: boolean;
  last_enforced?: string;
  enforcement_timestamp?: string;
  enforcementGaps?: MitigationEnforcementGaps;

  constructor({
    id,
    deviceId,
    threatId,
    name,
    description,
    mitigation_actions,
    is_enforced,
    last_enforced,
    enforcement_timestamp,
    enforcementGaps
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
    this.enforcementGaps = enforcementGaps;
  }

  static fromJSON(json: MitigationData | any): Mitigation {
    return new Mitigation({
      id: json.id || '',
      deviceId: json.deviceId || json.device_id || '',
      threatId: json.threatId || json.threat_id,
      name: json.name || '',
      description: json.description,
      mitigation_actions: json.mitigation_actions ?? json.mitigationActions ?? '',
      is_enforced: json.is_enforced !== undefined ? json.is_enforced : (json.isEnforced !== undefined ? json.isEnforced : false),
      last_enforced: json.last_enforced || json.lastEnforced,
      enforcement_timestamp: json.enforcement_timestamp || json.enforcementTimestamp,
      enforcementGaps: normalizeEnforcementGaps(
        json.enforcementGaps ?? json.enforcement_gaps
      )
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
      enforcement_timestamp: this.enforcement_timestamp,
      enforcementGaps: this.enforcementGaps
    };
  }
}
