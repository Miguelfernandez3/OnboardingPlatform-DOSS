import { apiClient } from '../../config';
import type { ServiceLogsResponse } from '../../core/ports';

export const serviceLogsService = {
  get: (service: string, tail?: number): Promise<ServiceLogsResponse> =>
    apiClient.getServiceLogs(service, tail),
};

export type { ServiceLogsResponse };
