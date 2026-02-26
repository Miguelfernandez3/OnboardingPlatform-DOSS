import { DossApiAdapter } from './doss/DossApiAdapter';
import { JsonServerApiClient } from './mock/JsonServerApiClient';
import { IApiClient } from '../../core/ports/IApiClient';

/**
 * Factory para crear adapters de API
 * Permite cambiar fácilmente el adapter según configuración
 */
export function createApiClient(adapterType: string = 'doss'): IApiClient {
  switch (adapterType) {
    case 'doss':
      return new DossApiAdapter();
    case 'json-server':
      return new JsonServerApiClient();
    default:
      throw new Error(`Unknown adapter type: ${adapterType}`);
  }
}

