/**
 * Device Entity
 * Representa un dispositivo en el sistema
 * Compatible con estructura legacy y Domain-Manager
 */
export interface DeviceData {
  id: string;
  name?: string;
  type?: string;
  manufacturer?: string;
  model: string;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
  // Campos del Domain-Manager
  ip?: string;
  mac?: string;
  identifier?: string; // uuid, diferente de id
  mudurl?: string;
  mudfile?: string;
  mitigation_actions?: string;
  inventory_id?: string;
  edk?: string;
}

export class Device {
  id: string;
  name: string;
  type: string;
  manufacturer: string;
  model: string;
  status: string;
  createdAt?: string;
  updatedAt?: string;
  // Campos del Domain-Manager
  ip?: string;
  mac?: string;
  identifier?: string; // uuid
  mudurl?: string;
  mudfile?: string;
  mitigation_actions?: string;
  inventory_id?: string;
  edk?: string;

  constructor({
    id,
    name = '',
    type = '',
    manufacturer = '',
    model,
    status = 'active',
    createdAt,
    updatedAt,
    // Campos del Domain-Manager
    ip,
    mac,
    identifier,
    mudurl,
    mudfile,
    mitigation_actions,
    inventory_id,
    edk
  }: DeviceData) {
    this.id = id;
    this.name = name;
    this.type = type;
    this.manufacturer = manufacturer;
    this.model = model;
    this.status = status;
    this.createdAt = createdAt;
    this.updatedAt = updatedAt;
    // Campos del Domain-Manager
    this.ip = ip;
    this.mac = mac;
    this.identifier = identifier;
    this.mudurl = mudurl;
    this.mudfile = mudfile;
    this.mitigation_actions = mitigation_actions;
    this.inventory_id = inventory_id;
    this.edk = edk;
  }

  static fromJSON(json: DeviceData | any): Device {
    // Mapeo para compatibilidad con ambos formatos
    // Si viene del Domain-Manager, usar identifier como id si no hay id
    const deviceId = json.id || json.identifier || '';
    const deviceName = json.name || json.model || '';
    const deviceType = json.type || '';
    const deviceManufacturer = json.manufacturer || '';
    const deviceModel = json.model || '';

    return new Device({
      id: deviceId,
      name: deviceName,
      type: deviceType,
      manufacturer: deviceManufacturer,
      model: deviceModel,
      status: json.status || 'active',
      createdAt: json.createdAt || json.created_at,
      updatedAt: json.updatedAt || json.updated_at,
      // Campos del Domain-Manager
      ip: json.ip,
      mac: json.mac,
      identifier: json.identifier || json.id,
      mudurl: json.mudurl || json.mud_url,
      mudfile: json.mudfile || json.mud_file,
      mitigation_actions: json.mitigation_actions,
      inventory_id: json.inventory_id || json.inventoryId,
      edk: json.edk
    });
  }

  toJSON(): DeviceData {
    return {
      id: this.id,
      name: this.name,
      type: this.type,
      manufacturer: this.manufacturer,
      model: this.model,
      status: this.status,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt,
      // Campos del Domain-Manager
      ip: this.ip,
      mac: this.mac,
      identifier: this.identifier,
      mudurl: this.mudurl,
      mudfile: this.mudfile,
      mitigation_actions: this.mitigation_actions,
      inventory_id: this.inventory_id,
      edk: this.edk
    };
  }
}

