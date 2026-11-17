import { apiClient } from '../../config';
import { UserData, UsersResponse, UserFilters, DeviceAccessRule, AccessRuleKind } from '../../core/ports';

/**
 * User Service - Funciones para operaciones con usuarios
 * Encapsula las llamadas al apiClient para gestión de usuarios
 */
export const userService = {
  /**
   * Obtiene la lista de usuarios con paginación y filtros
   */
  getUsers: async (page?: number, limit?: number, filters?: UserFilters): Promise<UsersResponse> => {
    return await apiClient.getUsers(page, limit, filters);
  },

  /**
   * Obtiene un usuario específico por ID
   */
  getUser: async (id: string): Promise<UserData> => {
    return await apiClient.getUser(id);
  },

  /**
   * Crea un nuevo usuario (solo admin)
   */
  createUser: async (email: string, password: string, role: string): Promise<UserData> => {
    return await apiClient.createUser(email, password, role);
  },

  /**
   * Actualiza el rol de un usuario (solo admin)
   */
  updateUserRole: async (id: string, role: string): Promise<UserData> => {
    return await apiClient.updateUserRole(id, role);
  },

  /**
   * Elimina un usuario (solo admin)
   */
  deleteUser: async (id: string): Promise<void> => {
    return await apiClient.deleteUser(id);
  },

  /**
   * Activa un usuario (solo admin)
   */
  activateUser: async (id: string): Promise<UserData> => {
    return await apiClient.activateUser(id);
  },

  /**
   * Desactiva un usuario (solo admin)
   */
  deactivateUser: async (id: string): Promise<UserData> => {
    return await apiClient.deactivateUser(id);
  },

  /** Lista las reglas de acceso a dispositivos de un usuario (solo admin) */
  getAccessRules: async (userId: string): Promise<DeviceAccessRule[]> => {
    return await apiClient.getAccessRules(userId);
  },

  /** Crea una regla de acceso para un usuario (solo admin) */
  createAccessRule: async (
    userId: string,
    matchKind: AccessRuleKind,
    matchValue: string
  ): Promise<DeviceAccessRule> => {
    return await apiClient.createAccessRule(userId, matchKind, matchValue);
  },

  /** Elimina una regla de acceso (solo admin) */
  deleteAccessRule: async (userId: string, ruleId: number): Promise<void> => {
    return await apiClient.deleteAccessRule(userId, ruleId);
  },
};
