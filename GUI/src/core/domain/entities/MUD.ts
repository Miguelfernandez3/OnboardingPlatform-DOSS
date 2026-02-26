/**
 * MUD Entity
 * Representa un archivo MUD (Manufacturer Usage Description)
 */
export interface MUDData {
  id?: string;
  deviceId: string;
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
}

export class MUD {
  id?: string;
  deviceId: string;
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

  constructor(data: MUDData) {
    this.id = data.id;
    this.deviceId = data.deviceId;
    this.mudVersion = data.mudVersion;
    this.mudUrl = data.mudUrl;
    this.lastUpdate = data.lastUpdate;
    this.cacheValidity = data.cacheValidity;
    this.isSupported = data.isSupported;
    this.systeminfo = data.systeminfo;
    this.mfgName = data.mfgName;
    this.documentation = data.documentation;
    this.modelName = data.modelName;
    this.mudData = data.mudData;
  }

  static fromJSON(json: MUDData): MUD {
    return new MUD(json);
  }

  toJSON(): MUDData {
    return {
      id: this.id,
      deviceId: this.deviceId,
      mudVersion: this.mudVersion,
      mudUrl: this.mudUrl,
      lastUpdate: this.lastUpdate,
      cacheValidity: this.cacheValidity,
      isSupported: this.isSupported,
      systeminfo: this.systeminfo,
      mfgName: this.mfgName,
      documentation: this.documentation,
      modelName: this.modelName,
      mudData: this.mudData
    };
  }
}

