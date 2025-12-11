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
};
