import axios, { AxiosError } from 'axios';
import { ApiError } from './ApiError';
import { ErrorCode, HTTP_STATUS_TO_ERROR_CODE } from './ErrorCode';

/**
 * Extrae información estructurada de un error de Axios
 */
export function extractApiError(error: unknown): ApiError {
  // Si ya es un ApiError, devolverlo directamente
  if (error instanceof ApiError) {
    return error;
  }

  // Si es un error de Axios
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{
      error?: string;
      code?: string;
      details?: Record<string, unknown>;
    }>;

    const statusCode = axiosError.response?.status || 0;
    const responseData = axiosError.response?.data;
    
    // Intentar extraer información estructurada del backend
    if (responseData && typeof responseData === 'object') {
      const errorMessage = responseData.error || axiosError.message || 'Unknown error';
      const errorCode = responseData.code || HTTP_STATUS_TO_ERROR_CODE[statusCode] || ErrorCode.GENERIC;
      const details = responseData.details || {};

      return new ApiError(
        errorMessage,
        errorCode,
        statusCode,
        details,
        error
      );
    }

    // Si no hay respuesta, es un error de red
    if (!axiosError.response) {
      return new ApiError(
        'Network error. Please check your connection.',
        ErrorCode.NETWORK_ERROR,
        0,
        {},
        error
      );
    }

    // Error genérico de Axios
    return new ApiError(
      axiosError.message || 'An error occurred',
      HTTP_STATUS_TO_ERROR_CODE[statusCode] || ErrorCode.GENERIC,
      statusCode,
      {},
      error
    );
  }

  // Si es un Error estándar
  if (error instanceof Error) {
    return new ApiError(
      error.message,
      ErrorCode.GENERIC,
      0,
      {},
      error
    );
  }

  // Error desconocido
  return new ApiError(
    'An unexpected error occurred',
    ErrorCode.GENERIC,
    0,
    {},
    error
  );
}

/**
 * Verifica si un error es recuperable
 */
export function isRecoverableError(error: ApiError): boolean {
  return !error.isServerError() && 
         !error.isAuthenticationError() && 
         !error.isAuthorizationError();
}
