import { DossApiAdapter } from './doss/DossApiAdapter';
import { MockApiClient } from '../../../infrastructure/api/mock/MockApiClient';
import { IApiClient } from '../../ports/IApiClient';

/**
 * Factory para crear adapters de API
 * Permite cambiar fácilmente el adapter según configuración
 */
export function createApiClient(adapterType: string = 'doss'): IApiClient {
  switch (adapterType) {
    case 'doss':
      return new DossApiAdapter();
    case 'mock':
      return new MockApiClient();
    default:
      throw new Error(`Unknown adapter type: ${adapterType}`);
  }
}

