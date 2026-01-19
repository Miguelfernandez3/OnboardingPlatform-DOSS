/**
 * Auth Interceptor - Interceptor de axios para autenticación
 * Agrega tokens a las peticiones y maneja refresh automático
 */
import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError, AxiosResponse } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens, isTokenExpired } from '../../utils/tokenStorage';

// Endpoints que no requieren token
const PUBLIC_ENDPOINTS = ['/auth/login', '/auth/refresh'];

/**
 * Verifica si un endpoint es público (no requiere token)
 */
function isPublicEndpoint(url: string): boolean {
  return PUBLIC_ENDPOINTS.some(endpoint => url.includes(endpoint));
}

/**
 * Configura el interceptor de autenticación para una instancia de axios
 * @param axiosInstance Instancia de axios a configurar
 * @param onTokenRefresh Callback para refrescar el token (opcional)
 * @param onAuthError Callback para manejar errores de autenticación (opcional)
 */
export function setupAuthInterceptor(
  axiosInstance: AxiosInstance,
  onTokenRefresh?: () => Promise<void>,
  onAuthError?: () => void
): void {
  let isRefreshing = false;
  let failedQueue: Array<{
    resolve: (value?: unknown) => void;
    reject: (reason?: unknown) => void;
  }> = [];

  const processQueue = (error: AxiosError | null, token: string | null = null) => {
    failedQueue.forEach(prom => {
      if (error) {
        prom.reject(error);
      } else {
        prom.resolve(token);
      }
    });
    failedQueue = [];
  };

  // Request interceptor: Agregar token a las peticiones
  axiosInstance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const url = config.url || '';
      
      // No agregar token a endpoints públicos
      if (isPublicEndpoint(url)) {
        return config;
      }

      const token = getAccessToken();
      if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    },
    (error: AxiosError) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor: Manejar errores 401 y refresh automático
  axiosInstance.interceptors.response.use(
    (response: AxiosResponse) => {
      return response;
    },
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

      // Si no es un error 401 o ya se reintentó, rechazar
      if (!error.response || error.response.status !== 401 || originalRequest._retry) {
        // Si es 403, es un error de permisos
        if (error.response?.status === 403) {
          return Promise.reject(new Error('No tienes permisos para realizar esta acción'));
        }
        return Promise.reject(error);
      }

      // Si el endpoint es público, no intentar refresh
      if (originalRequest.url && isPublicEndpoint(originalRequest.url)) {
        return Promise.reject(error);
      }

      // Si ya se está refrescando, encolar la petición
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            const token = getAccessToken();
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return axiosInstance(originalRequest);
          })
          .catch(err => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        isRefreshing = false;
        clearTokens();
        if (onAuthError) {
          onAuthError();
        }
        processQueue(error as AxiosError, null);
        return Promise.reject(error);
      }

      // Verificar que el refresh token no esté expirado antes de intentar refresh
      if (isTokenExpired(refreshToken)) {
        isRefreshing = false;
        clearTokens();
        if (onAuthError) {
          onAuthError();
        }
        processQueue(error as AxiosError, null);
        return Promise.reject(error);
      }

      try {
        // Intentar refrescar el token
        if (onTokenRefresh) {
          await onTokenRefresh();
        } else {
          // Si no hay callback, intentar refresh directamente usando axios
          const baseURL = originalRequest.baseURL || '';
          const response = await axios.post(
            `${baseURL}/auth/refresh`,
            { refresh_token: refreshToken }, // Backend espera refresh_token (snake_case)
            {
              headers: {
                'Content-Type': 'application/json',
              },
            }
          );
          
          // El backend solo devuelve access_token, mantener el refresh_token existente
          const accessToken = response.data.access_token || response.data.accessToken;
          if (accessToken) {
            const currentRefreshToken = getRefreshToken();
            if (currentRefreshToken) {
              setTokens(accessToken, currentRefreshToken);
            } else {
              throw new Error('No refresh token available');
            }
          } else {
            throw new Error('Invalid refresh response');
          }
        }

        const newToken = getAccessToken();
        if (newToken && originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }

        processQueue(null, newToken);
        isRefreshing = false;

        // Reintentar la petición original
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        isRefreshing = false;
        clearTokens();
        processQueue(refreshError as AxiosError, null);
        
        if (onAuthError) {
          onAuthError();
        }
        
        return Promise.reject(refreshError);
      }
    }
  );
}
