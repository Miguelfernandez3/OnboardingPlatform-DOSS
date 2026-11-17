import { apiClient } from '../../config';
import {
  EnforcementProfileData,
  EnforcementMappingData,
  EnforcementSecretMetadata,
  EnforcementExecutionLog,
  EnforcementTestRequest,
  EnforcementTestResponse
} from '../../core/ports';

export const enforcementAdminService = {
  getProfiles(includeInactive: boolean = true): Promise<EnforcementProfileData[]> {
    return apiClient.getEnforcementProfiles(includeInactive);
  },
  createProfile(
    payload: Partial<EnforcementProfileData> & { name: string; mode: 'rest' | 'era' }
  ): Promise<EnforcementProfileData> {
    return apiClient.createEnforcementProfile(payload);
  },
  updateProfile(id: string, payload: Partial<EnforcementProfileData>): Promise<EnforcementProfileData> {
    return apiClient.updateEnforcementProfile(id, payload);
  },
  deleteProfile(id: string): Promise<void> {
    return apiClient.deleteEnforcementProfile(id);
  },

  getMappings(includeInactive: boolean = true): Promise<EnforcementMappingData[]> {
    return apiClient.getEnforcementMappings(includeInactive);
  },
  createMapping(
    payload: Partial<EnforcementMappingData> & {
      matchKind: 'explicitProfile' | 'policyType' | 'capability';
      matchValue: string;
      profileId: number;
    }
  ): Promise<EnforcementMappingData> {
    return apiClient.createEnforcementMapping(payload);
  },
  updateMapping(id: string, payload: Partial<EnforcementMappingData>): Promise<EnforcementMappingData> {
    return apiClient.updateEnforcementMapping(id, payload);
  },
  deleteMapping(id: string): Promise<void> {
    return apiClient.deleteEnforcementMapping(id);
  },

  getSecrets(): Promise<EnforcementSecretMetadata[]> {
    return apiClient.getEnforcementSecrets();
  },
  createSecret(name: string, value: string): Promise<EnforcementSecretMetadata> {
    return apiClient.createEnforcementSecret(name, value);
  },
  updateSecret(id: string, payload: { name?: string; value?: string }): Promise<EnforcementSecretMetadata> {
    return apiClient.updateEnforcementSecret(id, payload);
  },
  deleteSecret(id: string): Promise<void> {
    return apiClient.deleteEnforcementSecret(id);
  },

  testProfile(payload: EnforcementTestRequest): Promise<EnforcementTestResponse> {
    return apiClient.testEnforcementProfile(payload);
  },
  getExecutions(filters?: {
    from?: string;
    to?: string;
    result?: string;
    deviceId?: string;
    isTest?: boolean;
    profileId?: number;
    limit?: number;
  }): Promise<EnforcementExecutionLog[]> {
    return apiClient.getEnforcementExecutions(filters);
  }
};
