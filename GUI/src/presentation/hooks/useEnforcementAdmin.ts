import { useCallback, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { enforcementAdminService } from '../../infrastructure/services/enforcementAdminService';
import {
  EnforcementProfileData,
  EnforcementMappingData,
  EnforcementSecretMetadata,
  EnforcementExecutionLog,
  EnforcementTestRequest,
  EnforcementTestResponse
} from '../../core/ports';

type ProfileFormState = {
  name: string;
  mode: 'rest' | 'era';
  method: string;
  endpointTemplate: string;
  headersTemplate: string;
  payloadTemplate: string;
  timeoutSeconds: number;
  dryRun: boolean;
  isDefault: boolean;
  isActive: boolean;
  autoEnforceOnRegistration: boolean;
  authType: 'none' | 'bearer';
  authSecretId: string;
  allowMsplToken: boolean;
  contextSpec: string;
};

type MappingFormState = {
  matchKind: 'explicitProfile' | 'policyType' | 'capability';
  matchValue: string;
  profileId: string;
  priority: number;
  isActive: boolean;
};

const EMPTY_PROFILE_FORM: ProfileFormState = {
  name: '',
  mode: 'rest',
  method: 'POST',
  endpointTemplate: '',
  headersTemplate: '{}',
  payloadTemplate: '{}',
  timeoutSeconds: 10,
  dryRun: false,
  isDefault: false,
  isActive: true,
  autoEnforceOnRegistration: false,
  authType: 'none',
  authSecretId: '',
  allowMsplToken: false,
  contextSpec: ''
};

const EMPTY_MAPPING_FORM: MappingFormState = {
  matchKind: 'policyType',
  matchValue: '',
  profileId: '',
  priority: 100,
  isActive: true
};

interface LogFilters {
  from: string;
  to: string;
  result: string;
  deviceId: string;
  isTest: string;
  profileId: string;
  limit: string;
}

const DEFAULT_LOG_FILTERS: LogFilters = {
  from: '',
  to: '',
  result: '',
  deviceId: '',
  isTest: '',
  profileId: '',
  limit: '200'
};

export interface UseEnforcementAdminReturn {
  loading: boolean;
  profiles: EnforcementProfileData[];
  mappings: EnforcementMappingData[];
  secrets: EnforcementSecretMetadata[];
  executions: EnforcementExecutionLog[];
  executionsLoading: boolean;
  profileForm: ProfileFormState;
  setProfileForm: React.Dispatch<React.SetStateAction<ProfileFormState>>;
  editingProfileId: string | null;
  mappingForm: MappingFormState;
  setMappingForm: React.Dispatch<React.SetStateAction<MappingFormState>>;
  editingMappingId: string | null;
  secretName: string;
  setSecretName: (v: string) => void;
  secretValue: string;
  setSecretValue: (v: string) => void;
  testProfileId: string;
  setTestProfileId: (v: string) => void;
  testRunMode: 'preview' | 'execute';
  setTestRunMode: (v: 'preview' | 'execute') => void;
  testContextText: string;
  setTestContextText: (v: string) => void;
  testResult: EnforcementTestResponse | null;
  logFilters: LogFilters;
  setLogFilters: React.Dispatch<React.SetStateAction<LogFilters>>;
  profileOptions: { value: string; label: string }[];
  saveProfile: () => Promise<void>;
  editProfile: (profile: EnforcementProfileData) => void;
  cancelEditProfile: () => void;
  deleteProfile: (id: string) => Promise<void>;
  showProfileForm: boolean;
  openCreateProfile: () => void;
  closeProfileForm: () => void;
  toggleProfileActive: (id: string) => Promise<void>;
  saveMapping: () => Promise<void>;
  editMapping: (mapping: EnforcementMappingData) => void;
  cancelEditMapping: () => void;
  deleteMapping: (id: string) => Promise<void>;
  showMappingForm: boolean;
  openCreateMapping: () => void;
  closeMappingForm: () => void;
  toggleMappingActive: (id: string) => Promise<void>;
  createSecret: () => Promise<void>;
  showSecretForm: boolean;
  openCreateSecret: () => void;
  closeSecretForm: () => void;
  rotateSecret: (id: string, newValue: string) => Promise<void>;
  deleteSecret: (id: string) => Promise<void>;
  runTest: () => Promise<{ error?: string }>;
  refreshExecutions: () => void;
}

export function useEnforcementAdmin(): UseEnforcementAdminReturn {
  const queryClient = useQueryClient();

  const [profileForm, setProfileForm] = useState<ProfileFormState>(EMPTY_PROFILE_FORM);
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
  const [showProfileForm, setShowProfileForm] = useState(false);
  const [mappingForm, setMappingForm] = useState<MappingFormState>(EMPTY_MAPPING_FORM);
  const [editingMappingId, setEditingMappingId] = useState<string | null>(null);
  const [showMappingForm, setShowMappingForm] = useState(false);
  const [secretName, setSecretName] = useState('');
  const [secretValue, setSecretValue] = useState('');
  const [showSecretForm, setShowSecretForm] = useState(false);
  const [testProfileId, setTestProfileId] = useState('');
  const [testRunMode, setTestRunMode] = useState<'preview' | 'execute'>('preview');
  const [testContextText, setTestContextText] = useState('{}');
  const [testResult, setTestResult] = useState<EnforcementTestResponse | null>(null);
  const [logFilters, setLogFilters] = useState<LogFilters>(DEFAULT_LOG_FILTERS);

  const { data: profiles = [], isLoading: profilesLoading } = useQuery({
    queryKey: queryKeys.enforcement.profiles,
    queryFn: () => enforcementAdminService.getProfiles(true),
    staleTime: 1000 * 30,
  });

  const { data: mappings = [], isLoading: mappingsLoading } = useQuery({
    queryKey: queryKeys.enforcement.mappings,
    queryFn: () => enforcementAdminService.getMappings(true),
    staleTime: 1000 * 30,
  });

  const { data: secrets = [], isLoading: secretsLoading } = useQuery({
    queryKey: queryKeys.enforcement.secrets,
    queryFn: () => enforcementAdminService.getSecrets(),
    staleTime: 1000 * 30,
  });

  const executionQueryFilters = useMemo(() => ({
    from: logFilters.from || undefined,
    to: logFilters.to || undefined,
    result: logFilters.result || undefined,
    deviceId: logFilters.deviceId || undefined,
    isTest: logFilters.isTest === '' ? undefined : logFilters.isTest === 'true',
    profileId: logFilters.profileId ? Number(logFilters.profileId) : undefined,
    limit: Number(logFilters.limit) || 200,
  }), [logFilters]);

  const { data: executions = [], isLoading: executionsLoading } = useQuery({
    queryKey: queryKeys.enforcement.executions(executionQueryFilters),
    queryFn: () => enforcementAdminService.getExecutions(executionQueryFilters),
    staleTime: 1000 * 15,
    placeholderData: (previousData) => previousData,
  });

  // Nota: no incluimos executionsLoading aquí para evitar que el tab de logs
  // bloquee toda la página mientras el usuario escribe/aplica filtros.
  const loading = profilesLoading || mappingsLoading || secretsLoading;

  const invalidateAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: queryKeys.enforcement.all });
  }, [queryClient]);

  const profileOptions = useMemo(
    () => profiles.map(p => ({ value: String(p.id), label: `${p.id} - ${p.name}` })),
    [profiles]
  );

  const saveProfileMutation = useMutation({
    mutationFn: async () => {
      const payload: Partial<EnforcementProfileData> & { name: string; mode: 'rest' | 'era' } = {
        name: profileForm.name,
        mode: profileForm.mode,
        method: profileForm.method,
        endpointTemplate: profileForm.endpointTemplate || undefined,
        headersTemplate: profileForm.headersTemplate || undefined,
        payloadTemplate: profileForm.payloadTemplate || undefined,
        timeoutSeconds: Number(profileForm.timeoutSeconds),
        dryRun: profileForm.dryRun,
        isDefault: profileForm.isDefault,
        isActive: profileForm.isActive,
        autoEnforceOnRegistration: profileForm.autoEnforceOnRegistration,
        authType: profileForm.authType,
        authSecretId: profileForm.authSecretId ? Number(profileForm.authSecretId) : null,
        allowMsplToken: profileForm.allowMsplToken
      };
      if (profileForm.contextSpec.trim()) {
        try {
          (payload as Record<string, unknown>).contextSpec = JSON.parse(profileForm.contextSpec) as unknown;
        } catch {
          throw new Error('validationContextSpecJson');
        }
      }
      if (editingProfileId) {
        return enforcementAdminService.updateProfile(editingProfileId, payload);
      }
      return enforcementAdminService.createProfile(payload);
    },
    onSuccess: () => {
      setProfileForm(EMPTY_PROFILE_FORM);
      setEditingProfileId(null);
      setShowProfileForm(false);
      invalidateAll();
    },
  });

  const deleteProfileMutation = useMutation({
    mutationFn: (id: string) => enforcementAdminService.deleteProfile(id),
    onSuccess: () => invalidateAll(),
  });

  const updateProfileActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      enforcementAdminService.updateProfile(id, { isActive }),
    onSuccess: () => invalidateAll(),
  });

  const updateMappingActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      enforcementAdminService.updateMapping(id, { isActive }),
    onSuccess: () => invalidateAll(),
  });

  const saveMappingMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        matchKind: mappingForm.matchKind,
        matchValue: mappingForm.matchValue,
        profileId: Number(mappingForm.profileId),
        priority: Number(mappingForm.priority),
        isActive: mappingForm.isActive
      } as const;
      if (editingMappingId) {
        return enforcementAdminService.updateMapping(editingMappingId, payload);
      }
      return enforcementAdminService.createMapping(payload);
    },
    onSuccess: () => {
      setMappingForm(EMPTY_MAPPING_FORM);
      setEditingMappingId(null);
      setShowMappingForm(false);
      invalidateAll();
    },
  });

  const deleteMappingMutation = useMutation({
    mutationFn: (id: string) => enforcementAdminService.deleteMapping(id),
    onSuccess: () => invalidateAll(),
  });

  const createSecretMutation = useMutation({
    mutationFn: ({ name, value }: { name: string; value: string }) =>
      enforcementAdminService.createSecret(name, value),
    onSuccess: () => {
      setSecretName('');
      setSecretValue('');
      setShowSecretForm(false);
      invalidateAll();
    },
  });

  const rotateSecretMutation = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) =>
      enforcementAdminService.updateSecret(id, { value }),
    onSuccess: () => invalidateAll(),
  });

  const deleteSecretMutation = useMutation({
    mutationFn: (id: string) => enforcementAdminService.deleteSecret(id),
    onSuccess: () => invalidateAll(),
  });

  const editProfile = useCallback((profile: EnforcementProfileData) => {
    setEditingProfileId(String(profile.id));
    setProfileForm({
      name: profile.name,
      mode: profile.mode,
      method: profile.method || 'POST',
      endpointTemplate: profile.endpointTemplate || '',
      headersTemplate: profile.headersTemplate || '{}',
      payloadTemplate: profile.payloadTemplate || '{}',
      timeoutSeconds: profile.timeoutSeconds || 10,
      dryRun: profile.dryRun,
      isDefault: profile.isDefault,
      isActive: profile.isActive,
      autoEnforceOnRegistration: profile.autoEnforceOnRegistration,
      authType: profile.authType || 'none',
      authSecretId: profile.authSecretId ? String(profile.authSecretId) : '',
      allowMsplToken: profile.allowMsplToken,
      contextSpec:
        profile.contextSpec != null && profile.contextSpec !== ''
          ? JSON.stringify(profile.contextSpec, null, 2)
          : ''
    });
    setShowProfileForm(true);
  }, []);

  const openCreateProfile = useCallback(() => {
    setEditingProfileId(null);
    setProfileForm(EMPTY_PROFILE_FORM);
    setShowProfileForm(true);
  }, []);

  const closeProfileForm = useCallback(() => {
    setEditingProfileId(null);
    setProfileForm(EMPTY_PROFILE_FORM);
    setShowProfileForm(false);
  }, []);

  const toggleProfileActive = useCallback(async (id: string) => {
    const profile = profiles.find(p => String(p.id) === id);
    if (!profile) return;
    await updateProfileActiveMutation.mutateAsync({ id, isActive: !profile.isActive });
  }, [profiles]);

  const editMapping = useCallback((mapping: EnforcementMappingData) => {
    setEditingMappingId(String(mapping.id));
    setMappingForm({
      matchKind: mapping.matchKind,
      matchValue: mapping.matchValue,
      profileId: String(mapping.profileId),
      priority: mapping.priority,
      isActive: mapping.isActive
    });
    setShowMappingForm(true);
  }, []);

  const openCreateMapping = useCallback(() => {
    setEditingMappingId(null);
    setMappingForm(EMPTY_MAPPING_FORM);
    setShowMappingForm(true);
  }, []);

  const closeMappingForm = useCallback(() => {
    setEditingMappingId(null);
    setMappingForm(EMPTY_MAPPING_FORM);
    setShowMappingForm(false);
  }, []);

  const toggleMappingActive = useCallback(async (id: string) => {
    const mapping = mappings.find(m => String(m.id) === id);
    if (!mapping) return;
    await updateMappingActiveMutation.mutateAsync({ id, isActive: !mapping.isActive });
  }, [mappings]);

  const openCreateSecret = useCallback(() => {
    setSecretName('');
    setSecretValue('');
    setShowSecretForm(true);
  }, []);

  const closeSecretForm = useCallback(() => {
    setSecretName('');
    setSecretValue('');
    setShowSecretForm(false);
  }, []);

  const runTest = useCallback(async (): Promise<{ error?: string }> => {
    if (!testProfileId) return { error: 'profileRequired' };
    let parsedContext: Record<string, unknown> = {};
    try {
      parsedContext = JSON.parse(testContextText || '{}');
    } catch {
      return { error: 'invalidJson' };
    }
    const payload: EnforcementTestRequest = {
      profileId: Number(testProfileId),
      runMode: testRunMode,
      context: parsedContext
    };
    const result = await enforcementAdminService.testProfile(payload);
    setTestResult(result);
    queryClient.invalidateQueries({ queryKey: queryKeys.enforcement.executions() });
    return {};
  }, [testProfileId, testContextText, testRunMode, queryClient]);

  const refreshExecutions = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: queryKeys.enforcement.executions() });
  }, [queryClient]);

  return {
    loading,
    profiles,
    mappings,
    secrets,
    executions,
    executionsLoading,
    profileForm,
    setProfileForm,
    editingProfileId,
    mappingForm,
    setMappingForm,
    editingMappingId,
    secretName,
    setSecretName,
    secretValue,
    setSecretValue,
    testProfileId,
    setTestProfileId,
    testRunMode,
    setTestRunMode,
    testContextText,
    setTestContextText,
    testResult,
    logFilters,
    setLogFilters,
    profileOptions,
    saveProfile: async () => { await saveProfileMutation.mutateAsync(); },
    editProfile,
    cancelEditProfile: closeProfileForm,
    deleteProfile: async (id: string) => { await deleteProfileMutation.mutateAsync(id); },
    showProfileForm,
    openCreateProfile,
    closeProfileForm,
    toggleProfileActive,
    saveMapping: async () => { await saveMappingMutation.mutateAsync(); },
    editMapping,
    cancelEditMapping: closeMappingForm,
    deleteMapping: async (id: string) => { await deleteMappingMutation.mutateAsync(id); },
    showMappingForm,
    openCreateMapping,
    closeMappingForm,
    toggleMappingActive,
    createSecret: async () => { await createSecretMutation.mutateAsync({ name: secretName.trim(), value: secretValue }); },
    showSecretForm,
    openCreateSecret,
    closeSecretForm,
    rotateSecret: async (id: string, newValue: string) => { await rotateSecretMutation.mutateAsync({ id, value: newValue }); },
    deleteSecret: async (id: string) => { await deleteSecretMutation.mutateAsync(id); },
    runTest,
    refreshExecutions,
  };
}
