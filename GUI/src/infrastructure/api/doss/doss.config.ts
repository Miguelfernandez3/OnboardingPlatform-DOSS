import { AdapterConfig } from '../../../core/adapters/config/ConfigProvider';

/**
 * DOSS API Configuration
 * Configuración de endpoints para el adapter DOSS
 */
export const dossConfig: AdapterConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api',
  adapterType: 'doss',
  endpoints: {
    devices: '/devices',
    registerDsp: '/dsp',
    device: '/devices/:id',
    passport: '/devices/:id/passport',
    mud: '/devices/:id/mud',
    policies: '/devices/:id/policies',
    deviceLogs: '/devices/:id/logs',
    applyIdsp2: '/devices/:id/apply-idsp2',
    applyPolicy: '/devices/:id/apply-policy',
    enforcePolicy: '/devices/:id/policies/:policyId/enforce',
    policyEnforcementGaps: '/devices/:id/policies/:policyId/enforcement-gaps',
    enforcementStatus: '/devices/:id/enforcement-status',
    threats: '/devices/:id/threats',
    mitigations: '/devices/:id/mitigations',
    enforceMitigation: '/devices/:id/mitigations/:mitigationId/enforce',
    revokeMitigation: '/devices/:id/mitigations/:mitigationId/revoke',
    updateDevice: '/devices/:id',
    deviceEnforcementGaps: '/devices/:id/enforcement-gaps',
    deleteDevice: '/devices/:id',
    login: '/auth/login',
    refresh: '/auth/refresh',
    me: '/auth/me',
    changePassword: '/auth/change-password',
    users: '/users',
    user: '/users/:id',
    userRole: '/users/:id/role',
    userActivate: '/users/:id/activate',
    userDeactivate: '/users/:id/deactivate',
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
