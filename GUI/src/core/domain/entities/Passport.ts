/**
 * Passport Entity
 * Representa el pasaporte digital del dispositivo (JSON genérico)
 */
export interface PassportData {
  deviceId?: string;
  data?: Record<string, unknown>;
}

export class Passport {
  deviceId?: string;
  data?: Record<string, unknown>;

  constructor({ deviceId, data = {} }: PassportData) {
    this.deviceId = deviceId;
    this.data = data;
  }

  static fromJSON(json: PassportData | Record<string, unknown>): Passport {
    if ('deviceId' in json) {
      return new Passport({
        deviceId: json.deviceId as string,
        data: json.data as Record<string, unknown> || (json as Record<string, unknown>)
      });
    }
    // Si no tiene deviceId, asumimos que todo el objeto es data
    return new Passport({
      deviceId: 'unknown',
      data: json as Record<string, unknown>
    });
  }

  toJSON(): PassportData {  
    return new Passport({
      deviceId: this.deviceId as string,
      data: this.data
    });
  }
}

