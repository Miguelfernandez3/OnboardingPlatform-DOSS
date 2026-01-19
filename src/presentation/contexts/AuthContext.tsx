/**
 * AuthContext - Contexto de autenticación
 * Proporciona estado y funciones de autenticación a toda la aplicación
 */
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User } from '../../core/domain/entities/User';
import { authService } from '../../infrastructure/services/authService';
import { getAccessToken, getRefreshToken, isTokenExpired } from '../../infrastructure/utils/tokenStorage';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const isAuthenticated = user !== null;
  const isAdmin = user?.role === 'admin' || false;

  /**
   * Verifica y refresca el token si es necesario
   */
  const refreshAuth = useCallback(async () => {
    try {
      const accessToken = getAccessToken();
      const refreshToken = getRefreshToken();

      if (!accessToken || !refreshToken) {
        setUser(null);
        return;
      }

      // Si el token está expirado o próximo a expirar (menos de 5 minutos), refrescar
      if (isTokenExpired(accessToken)) {
        const response = await authService.refreshToken(refreshToken);
        const userData = await authService.getCurrentUser();
        setUser(User.fromJSON(userData));
      } else {
        // Solo obtener el usuario si el token es válido
        const userData = await authService.getCurrentUser();
        setUser(User.fromJSON(userData));
      }
    } catch (error) {
      console.error('Error refreshing auth:', error);
      setUser(null);
      authService.logout();
    }
  }, []);

  /**
   * Verifica la autenticación al iniciar la app
   */
  const checkAuth = useCallback(async () => {
    setIsLoading(true);
    try {
      const accessToken = getAccessToken();
      if (!accessToken) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      // Si el token está expirado, intentar refrescar
      if (isTokenExpired(accessToken)) {
        await refreshAuth();
      } else {
        // Obtener el usuario actual
        const userData = await authService.getCurrentUser();
        setUser(User.fromJSON(userData));
      }
    } catch (error) {
      console.error('Error checking auth:', error);
      setUser(null);
      authService.logout();
    } finally {
      setIsLoading(false);
    }
  }, [refreshAuth]);

  /**
   * Inicia sesión
   */
  const login = useCallback(async (email: string, password: string) => {
    try {
      const response = await authService.login(email, password);
      const userData = response.user;
      setUser(User.fromJSON(userData));
    } catch (error) {
      console.error('Error logging in:', error);
      throw error;
    }
  }, []);

  /**
   * Cierra sesión
   */
  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  // Verificar autenticación al montar el componente
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Verificar periódicamente si el token necesita refrescarse
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      const accessToken = getAccessToken();
      if (accessToken && isTokenExpired(accessToken)) {
        refreshAuth();
      }
    }, 60000); // Verificar cada minuto

    return () => clearInterval(interval);
  }, [isAuthenticated, refreshAuth]);

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    isAdmin,
    login,
    logout,
    refreshAuth,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook para usar el contexto de autenticación
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
