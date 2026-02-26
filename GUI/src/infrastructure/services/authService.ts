import { apiClient } from '../../config';
import { AuthResponse, UserData } from '../../core/ports';
import { setTokens, clearTokens } from '../utils/tokenStorage';

/**
 * Auth Service - Funciones para operaciones de autenticación
 * Encapsula las llamadas al apiClient para autenticación
 */
export const authService = {
  /**
   * Inicia sesión con email y password
   */
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await apiClient.login(email, password);
    // Guardar tokens en localStorage
    setTokens(response.accessToken, response.refreshToken);
    return response;
  },

  /**
   * Refresca el token de acceso usando el refresh token
   */
  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    const response = await apiClient.refreshToken(refreshToken);
    // Actualizar tokens en localStorage
    setTokens(response.accessToken, response.refreshToken);
    return response;
  },

  /**
   * Obtiene el usuario actual autenticado
   */
  getCurrentUser: async (): Promise<UserData> => {
    return await apiClient.getCurrentUser();
  },

  /**
   * Cambia la contraseña del usuario actual
   */
  changePassword: async (oldPassword: string, newPassword: string): Promise<void> => {
    return await apiClient.changePassword(oldPassword, newPassword);
  },

  /**
   * Cierra sesión y limpia los tokens
   */
  logout: (): void => {
    clearTokens();
  },
};
