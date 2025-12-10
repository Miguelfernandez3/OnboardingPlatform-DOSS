import { IConfigProvider } from '../../ports/IConfigProvider';

export interface AdapterConfig {
  baseUrl: string;
  adapterType: string;
  endpoints: Record<string, string>;
}

/**
 * ConfigProvider - Implementación de IConfigProvider
 */
export class ConfigProvider extends IConfigProvider {
  constructor(private config: AdapterConfig) {
    super();
  }

  getApiBaseUrl(): string {
    return this.config.baseUrl || '';
  }

  getEndpoints(): Record<string, string> {
    return this.config.endpoints || {};
  }

  getAdapterType(): string {
    return this.config.adapterType || 'doss';
  }

  resolveEndpoint(endpointKey: string, params: Record<string, string> = {}): string {
    let endpoint = this.config.endpoints[endpointKey];
    if (!endpoint) {
      throw new Error(`Endpoint '${endpointKey}' not found in configuration`);
    }

    // Reemplazar parámetros en el endpoint (ej: /devices/:id -> /devices/123)
    Object.keys(params).forEach(key => {
      endpoint = endpoint.replace(`:${key}`, params[key]);
    });

    return endpoint;
  }
}

