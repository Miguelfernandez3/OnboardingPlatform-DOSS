/**
 * Device Entity
 * Representa un dispositivo en el sistema
 */
export interface DeviceData {
  id: string;
  name: string;
  type: string;
  manufacturer: string;
  model: string;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
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

  constructor({
    id,
    name,
    type,
    manufacturer,
    model,
    status = 'active',
    createdAt,
    updatedAt
  }: DeviceData) {
    this.id = id;
    this.name = name;
    this.type = type;
    this.manufacturer = manufacturer;
    this.model = model;
    this.status = status;
    this.createdAt = createdAt;
    this.updatedAt = updatedAt;
  }

  static fromJSON(json: DeviceData): Device {
    return new Device(json);
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
      updatedAt: this.updatedAt
    };
  }
}

