import { createApiClient } from './core/adapters/api/index';
import { IApiClient } from './core/ports/IApiClient';

/**
 * Configuración centralizada de la aplicación
 * Determina qué adapter usar según variable de entorno o default
 */
const adapterType: string = import.meta.env.VITE_API_ADAPTER || 'json-server';

export const apiClient: IApiClient = createApiClient(adapterType);

