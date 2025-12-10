/**
 * IConfigProvider - Interface/Contrato para Config Provider
 * Define los métodos para obtener configuración
 */
export abstract class IConfigProvider {
  /**
   * Obtiene la URL base de la API
   */
  abstract getApiBaseUrl(): string;

  /**
   * Obtiene los endpoints de la API
   */
  abstract getEndpoints(): Record<string, string>;

  /**
   * Obtiene el tipo de adapter
   */
  abstract getAdapterType(): string;

  /**
   * Resuelve un endpoint reemplazando parámetros
   */
  abstract resolveEndpoint(endpointKey: string, params?: Record<string, string>): string;
}

