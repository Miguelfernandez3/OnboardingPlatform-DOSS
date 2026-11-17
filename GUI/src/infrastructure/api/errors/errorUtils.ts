import axios, { AxiosError } from 'axios';
import { ApiError } from './ApiError';
import { ErrorCode, HTTP_STATUS_TO_ERROR_CODE } from './ErrorCode';

/**
 * Si el cuerpo de error viene como string (p. ej. proxy o serialización), intenta JSON.parse.
 */
function parseErrorResponseData(data: unknown): unknown {
  if (typeof data === 'string' && data.trim().length > 0) {
    try {
      return JSON.parse(data) as unknown;
    } catch {
      return data;
    }
  }
  return data;
}

/**
 * `instanceof ApiError` falla si hay dos copias de la clase (p. ej. bundling / chunks).
 * Un ApiError "real" siempre trae code + statusCode + details; si se trata luego como Error
 * genérico se pierde el 409 y nunca se abre el modal de contexto.
 */
function looksLikeSerializedApiError(
  error: unknown
): error is {
  message: string;
  code: string;
  statusCode: number;
  details: Record<string, unknown>;
  originalError?: unknown;
} {
  if (error === null || typeof error !== 'object') {
    return false;
  }
  const o = error as Record<string, unknown>;
  return (
    typeof o.message === 'string' &&
    typeof o.code === 'string' &&
    typeof o.statusCode === 'number' &&
    typeof o.details === 'object' &&
    o.details !== null &&
    !Array.isArray(o.details)
  );
}

/**
 * 409 con datos de enforcement: código explícito o cuerpo con `missing` (aunque `code` se mapee por status).
 */
export function isEnforcementPrerequisitesConflict(error: unknown): boolean {
  const api = extractApiError(error);
  if (api.statusCode !== 409) {
    return false;
  }
  if (api.code === 'ENFORCEMENT_PREREQUISITES') {
    return true;
  }
  const m = getEnforcementPrerequisitesMissingEx(api);
  return m.length > 0;
}

/**
 * Interno: reutiliza un ApiError ya resuelto para no duplicar trabajo.
 */
function getEnforcementPrerequisitesMissingEx(api: ApiError): Array<Record<string, unknown>> {
  const m = api.details.missing;
  if (Array.isArray(m) && m.length > 0) {
    return m as Array<Record<string, unknown>>;
  }
  const orig = api.originalError;
  if (axios.isAxiosError(orig)) {
    const raw = orig.response?.data;
    const parsed = parseErrorResponseData(raw) as
      | { missing?: unknown; code?: string }
      | null
      | undefined;
    if (parsed && typeof parsed === 'object' && 'missing' in parsed) {
      const fromBody = (parsed as { missing?: unknown }).missing;
      if (Array.isArray(fromBody) && fromBody.length > 0) {
        return fromBody as Array<Record<string, unknown>>;
      }
    }
  }
  return [];
}

/**
 * Lista de claves faltantes para enforcement (409 ENFORCEMENT_PREREQUISITES o variante con body parcial).
 */
export function getEnforcementPrerequisitesMissing(
  error: unknown
): Array<Record<string, unknown>> {
  const api = extractApiError(error);
  return getEnforcementPrerequisitesMissingEx(api);
}

/**
 * Extrae información estructurada de un error de Axios
 */
export function extractApiError(error: unknown): ApiError {
  // Si ya es un ApiError, devolverlo directamente
  if (error instanceof ApiError) {
    return error;
  }

  // Misma forma que ApiError pero otra instancia de clase (instanceof falla) — rehidratar
  if (looksLikeSerializedApiError(error)) {
    return new ApiError(
      error.message,
      error.code,
      error.statusCode,
      error.details,
      error.originalError
    );
  }

  // Si es un error de Axios
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{
      error?: string;
      code?: string;
      details?: Record<string, unknown>;
    }>;

    const statusCode = axiosError.response?.status || 0;
    const responseData = parseErrorResponseData(axiosError.response?.data);
    
    // Intentar extraer información estructurada del backend
    if (responseData && typeof responseData === 'object' && !Array.isArray(responseData)) {
      const data = responseData as {
        error?: string;
        code?: string;
        details?: Record<string, unknown>;
        missing?: unknown;
      };
      const errorMessage = data.error || axiosError.message || 'Unknown error';
      const errorCode = data.code || HTTP_STATUS_TO_ERROR_CODE[statusCode] || ErrorCode.GENERIC;
      const baseDetails = data.details && typeof data.details === 'object' && !Array.isArray(data.details) ? data.details as Record<string, unknown> : {};
      const details: Record<string, unknown> = {
        ...baseDetails
      };
      if (data.missing !== undefined && data.missing !== null) {
        details.missing = data.missing;
      }

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
