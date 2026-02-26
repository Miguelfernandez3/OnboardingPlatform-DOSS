import { AxiosInstance, AxiosError } from 'axios';
import { extractApiError } from '../errors/errorUtils';

/**
 * Interceptor global para manejar errores de forma consistente
 * Puede usarse para logging, analytics, etc.
 */
export function setupErrorInterceptor(axiosInstance: AxiosInstance): void {
  axiosInstance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      const apiError = extractApiError(error);
      
      // Logging en desarrollo
      if (import.meta.env.DEV) {
        console.error('API Error:', {
          code: apiError.code,
          message: apiError.message,
          statusCode: apiError.statusCode,
          details: apiError.details,
        });
      }

      // Aquí se puede agregar:
      // - Envío a servicios de analytics
      // - Logging a servidor
      // - Notificaciones especiales para ciertos errores
      
      return Promise.reject(apiError);
    }
  );
}
