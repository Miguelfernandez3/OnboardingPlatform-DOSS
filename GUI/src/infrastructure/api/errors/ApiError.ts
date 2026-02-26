/**
 * Clase personalizada para errores de API
 * Extrae información estructurada de las respuestas de error del backend
 */
export class ApiError extends Error {
  public readonly code: string;
  public readonly statusCode: number;
  public readonly details: Record<string, unknown>;
  public readonly originalError: unknown;

  constructor(
    message: string,
    code: string,
    statusCode: number,
    details: Record<string, unknown> = {},
    originalError?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    this.originalError = originalError;
    
    // Mantener el stack trace correcto
    const errorConstructor = Error as ErrorConstructor & {
      captureStackTrace?: (targetObject: object, constructorOpt?: Function) => void;
    };
    if (errorConstructor.captureStackTrace) {
      errorConstructor.captureStackTrace(this, ApiError);
    }
  }

  /**
   * Verifica si el error es de un tipo específico
   */
  isCode(code: string): boolean {
    return this.code === code;
  }

  /**
   * Verifica si el error es de autenticación
   */
  isAuthenticationError(): boolean {
    return this.statusCode === 401 || 
           ['AUTHENTICATION_ERROR', 'TOKEN_EXPIRED', 'INVALID_CREDENTIALS'].includes(this.code);
  }

  /**
   * Verifica si el error es de autorización
   */
  isAuthorizationError(): boolean {
    return this.statusCode === 403 || this.code === 'AUTHORIZATION_ERROR';
  }

  /**
   * Verifica si el error es de validación
   */
  isValidationError(): boolean {
    return this.statusCode === 400 || this.code === 'INVALID_REQUEST';
  }

  /**
   * Verifica si el error es de recurso no encontrado
   */
  isNotFoundError(): boolean {
    return this.statusCode === 404 || this.code.includes('NOT_FOUND');
  }

  /**
   * Verifica si el error es del servidor
   */
  isServerError(): boolean {
    return this.statusCode >= 500 || 
           ['DATABASE_ERROR', 'INTERNAL_ERROR', 'INITIALIZATION_ERROR'].includes(this.code);
  }
}
