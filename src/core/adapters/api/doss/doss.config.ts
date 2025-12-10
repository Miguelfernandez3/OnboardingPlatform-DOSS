import { AdapterConfig } from '../../config/ConfigProvider';

/**
 * DOSS API Configuration
 * Configuración de endpoints para el adapter DOSS
 */
export const dossConfig: AdapterConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api',
  adapterType: 'doss',
  endpoints: {
    devices: '/devices',
    device: '/devices/:id',
    passport: '/devices/:id/passport',
    mud: '/devices/:id/mud',
    policies: '/devices/:id/policies',
    applyIdsp2: '/devices/:id/apply-idsp2',
    applyPolicy: '/devices/:id/apply-policy',
    enforcementStatus: '/devices/:id/enforcement-status'
  }
};

