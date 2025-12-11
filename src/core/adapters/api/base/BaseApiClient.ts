import axios, { AxiosRequestConfig, AxiosError } from 'axios';
import { IConfigProvider, IApiClient, ApplyResult, EnforcementStatus } from '../../../ports';
import { Device, Policy, MUD, Passport } from '../../../domain';

/**
 * BaseApiClient - Clase base abstracta para adapters de API
 * Proporciona funcionalidad común y métodos helper
 */
export abstract class BaseApiClient extends IApiClient {
  protected config: IConfigProvider;

  constructor(configProvider: IConfigProvider) {
    super();
    this.config = configProvider;
  }

  /**
   * Realiza una petición HTTP usando axios
   * @protected
   */
  protected async request<T>(endpoint: string, options: AxiosRequestConfig = {}): Promise<T> {
    const url = `${this.config.getApiBaseUrl()}${endpoint}`;
    
    const defaultOptions: AxiosRequestConfig = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await axios<T>(url, defaultOptions);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        const errorMessage = axiosError.response?.data 
          ? (typeof axiosError.response.data === 'string' 
              ? axiosError.response.data 
              : JSON.stringify(axiosError.response.data))
          : axiosError.message || 'Unknown error';
        throw new Error(`API Error: ${axiosError.response?.status || 'Network'} - ${errorMessage}`);
      }
      throw error;
    }
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
  abstract applyPolicy(deviceId: string, msplXml: string): Promise<ApplyResult>;
  abstract getEnforcementStatus(deviceId: string): Promise<EnforcementStatus>;
}

