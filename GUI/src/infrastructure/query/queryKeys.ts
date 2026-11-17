import { UserFilters } from '../../core/ports';

/**
 * Query Keys - Factory functions para query keys de TanStack Query
 * Centraliza todas las keys para facilitar invalidación y mantenimiento
 */
export const queryKeys = {
  devices: {
    all: ['devices'] as const,
    detail: (id: string) => ['devices', id] as const,
    policies: (id: string) => ['devices', id, 'policies'] as const,
    threats: (id: string) => ['devices', id, 'threats'] as const,
    mitigations: (id: string) => ['devices', id, 'mitigations'] as const,
    passport: (id: string) => ['devices', id, 'passport'] as const,
    mud: (id: string) => ['devices', id, 'mud'] as const,
    enforcementStatus: (id: string) => ['devices', id, 'enforcement-status'] as const,
  },
  auth: {
    currentUser: ['auth', 'currentUser'] as const,
  },
  users: {
    all: (page?: number, limit?: number, filters?: UserFilters) => 
      ['users', page, limit, filters] as const,
    detail: (id: string) => ['users', id] as const,
  },
  enforcement: {
    profiles: ['enforcement', 'profiles'] as const,
    mappings: ['enforcement', 'mappings'] as const,
    secrets: ['enforcement', 'secrets'] as const,
    executions: (filters?: Record<string, unknown>) =>
      ['enforcement', 'executions', { ...filters }] as const,
    all: ['enforcement'] as const,
  },
  notifications: {
    all: ['notifications'] as const,
    list: (readState: 'unread' | 'read', page: number, perPage: number) =>
      ['notifications', 'list', readState, page, perPage] as const,
    unreadCount: ['notifications', 'unread-count'] as const,
  },
  settings: {
    notification: ['settings', 'notification'] as const,
  },
};
