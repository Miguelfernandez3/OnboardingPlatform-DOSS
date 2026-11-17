import { AdapterConfig } from '../../../core/adapters/config/ConfigProvider';

/**
 * JSON Server API Configuration
 * Configuración de endpoints para el adapter JSON Server
 */
export const jsonServerConfig: AdapterConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001',
  adapterType: 'json-server',
  endpoints: {
    devices: '/devices',
    registerDsp: '/devices',
    device: '/devices/:id',
    policies: '/policies?deviceId=:deviceId',
    passport: '/passports?deviceId=:deviceId',
    mud: '/muds?deviceId=:deviceId',
    threats: '/threats?deviceId=:deviceId',
    mitigations: '/mitigations?deviceId=:deviceId',
    applyIdsp2: '/devices/:id/apply-idsp2',
    applyPolicy: '/devices/:id/apply-policy',
    enforcePolicy: '/policies/:policyId',
    enforcementStatus: '/enforcementStatuses?deviceId=:deviceId',
    enforceMitigation: '/mitigations/:mitigationId',
    revokeMitigation: '/mitigations/:mitigationId',
    updateDevice: '/devices/:id',
    deleteDevice: '/devices/:id',
    login: '/auth/login',
    refresh: '/auth/refresh',
    me: '/auth/me',
    changePassword: '/auth/change-password',
    users: '/users',
    user: '/users/:id',
    userRole: '/users/:id',
    userActivate: '/users/:id',
    enforcementProfiles: '/admin/enforcement/profiles',
    enforcementProfile: '/admin/enforcement/profiles/:id',
    enforcementMappings: '/admin/enforcement/mappings',
    enforcementMapping: '/admin/enforcement/mappings/:id',
    enforcementSecrets: '/admin/enforcement/secrets',
    enforcementSecret: '/admin/enforcement/secrets/:id',
    enforcementTest: '/admin/enforcement/test',
    enforcementExecutions: '/admin/enforcement/executions',
    userMeSettings: '/users/me/settings',
    notificationSettings: '/users/me/notification-settings',
    myNotifications: '/users/me/notifications',
    notificationsUnreadCount: '/users/me/notifications/unread-count',
    notificationsReadAll: '/users/me/notifications/read-all',
    notificationRead: '/users/me/notifications/:nid/read',
    telegramLinkToken: '/users/me/telegram/link-token',
    telegramUnlink: '/users/me/telegram'
  }
};
