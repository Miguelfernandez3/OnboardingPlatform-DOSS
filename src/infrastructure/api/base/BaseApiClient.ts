import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import { IConfigProvider, IApiClient, ApplyResult, EnforcementStatus } from '../../../core/ports';
import { Device, Policy, MUD, Passport } from '../../../core/domain';
import { setupAuthInterceptor } from '../interceptors/authInterceptor';
import { setupErrorInterceptor } from '../interceptors/errorInterceptor';
import { extractApiError } from '../errors/errorUtils';

/**
 * BaseApiClient - Clase base abstracta para adapters de API
 * Proporciona funcionalidad común y métodos helper
 */
export abstract class BaseApiClient extends IApiClient {
  protected config: IConfigProvider;
  protected axiosInstance: AxiosInstance;

  constructor(configProvider: IConfigProvider, onTokenRefresh?: () => Promise<void>, onAuthError?: () => void) {
    super();
    this.config = configProvider;
    
    // Crear instancia de axios con la base URL
    this.axiosInstance = axios.create({
      baseURL: this.config.getApiBaseUrl(),
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Configurar interceptor de autenticación
    setupAuthInterceptor(this.axiosInstance, onTokenRefresh, onAuthError);
    
    // Configurar interceptor de errores para logging
    setupErrorInterceptor(this.axiosInstance);
  }

  /**
   * Realiza una petición HTTP usando la instancia de axios
   * @protected
   */
  protected async request<T>(endpoint: string, options: AxiosRequestConfig = {}): Promise<T> {
    const defaultOptions: AxiosRequestConfig = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    };

    try {
      const response = await this.axiosInstance<T>(endpoint, defaultOptions);
      return response.data;
    } catch (error) {
      // Usar extractApiError para obtener un ApiError estructurado
      throw extractApiError(error);
    }
  }

  /**
   * Realiza una petición POST sin token (para login/refresh)
   * @protected
   */
  protected async authPost<T>(endpoint: string, data: unknown, params: Record<string, string> = {}): Promise<T> {
    const resolvedEndpoint = this.config.resolveEndpoint(endpoint, params);
    return await this.request<T>(resolvedEndpoint, {
      method: 'POST',
      data: data
    });
  }

  /**
   * Realiza una petición GET
   * @protected
   */
  protected async get<T>(endpoint: string, params: Record<string, string> = {}): Promise<T> {
    const resolvedEndpoint = this.config.resolveEndpoint(endpoint, params);
    return await this.request<T>(resolvedEndpoint, { method: 'GET' });
  }

  /**
   * Realiza una petición POST
   * @protected
   */
  protected async post<T>(endpoint: string, data: unknown, params: Record<string, string> = {}): Promise<T> {
    const resolvedEndpoint = this.config.resolveEndpoint(endpoint, params);
    return await this.request<T>(resolvedEndpoint, {
      method: 'POST',
      data: data
    });
  }

  /**
   * Realiza una petición POST con XML
   * @protected
   */
  protected async postXml<T>(endpoint: string, xmlData: string, params: Record<string, string> = {}): Promise<T> {
    const resolvedEndpoint = this.config.resolveEndpoint(endpoint, params);
    return await this.request<T>(resolvedEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/xml'
      },
      data: xmlData
    });
  }

  /**
   * Realiza una petición PUT
   * @protected
   */
  protected async put<T>(endpoint: string, data: unknown, params: Record<string, string> = {}): Promise<T> {
    const resolvedEndpoint = this.config.resolveEndpoint(endpoint, params);
    return await this.request<T>(resolvedEndpoint, {
      method: 'PUT',
      data: data
    });
  }

  /**
   * Realiza una petición PATCH
   * @protected
   */
  protected async patch<T>(endpoint: string, data: unknown, params: Record<string, string> = {}): Promise<T> {
    const resolvedEndpoint = this.config.resolveEndpoint(endpoint, params);
    return await this.request<T>(resolvedEndpoint, {
      method: 'PATCH',
      data: data
    });
  }

  /**
   * Realiza una petición DELETE
   * @protected
   */
  protected async delete<T>(endpoint: string, params: Record<string, string> = {}): Promise<T> {
    const resolvedEndpoint = this.config.resolveEndpoint(endpoint, params);
    return await this.request<T>(resolvedEndpoint, {
      method: 'DELETE'
    });
  }

  // Métodos abstractos que deben ser implementados por las clases hijas
  abstract getDevices(): Promise<Device[]>;
  abstract getDevice(id: string): Promise<Device>;
  abstract getDevicePassport(id: string): Promise<Passport>;
  abstract getDeviceMUD(id: string): Promise<MUD>;
  abstract getDevicePolicies(id: string): Promise<Policy[]>;
  abstract applyIDSP2(deviceId: string, idsp2Id: string): Promise<ApplyResult>;
  abstract applyPolicy(deviceId: string, msplXml: string, name?: string): Promise<ApplyResult>;
  abstract getEnforcementStatus(deviceId: string): Promise<EnforcementStatus>;
  abstract enforcePolicy(deviceId: string, policyId: string): Promise<ApplyResult>;
}
