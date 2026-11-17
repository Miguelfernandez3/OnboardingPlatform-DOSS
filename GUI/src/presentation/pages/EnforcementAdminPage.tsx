import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AdminRoute } from '../components/auth';
import { useToast } from '../../infrastructure/notifications/useToast';
import { useEnforcementAdmin, useIsMobile } from '../hooks';
import LoadingSpinner from '../components/common/LoadingSpinner';
import {
  ProfilesSection,
  MappingsSection,
  SecretsSection,
  TestProfileSection,
  ExecutionLogsSection,
  ProfileFormModal,
  MappingFormModal,
  CreateSecretModal
} from '../components/enforcement';

interface Tab {
  id: string;
  label: string;
}

export default function EnforcementAdminPage(): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { showSuccess, showError, showApiError } = useToast();
  const [activeTab, setActiveTab] = useState('profiles');

  const hook = useEnforcementAdmin();

  const tabs: Tab[] = [
    { id: 'profiles', label: t('enforcementAdmin.tabs.profiles') },
    { id: 'mappings', label: t('enforcementAdmin.tabs.mappings') },
    { id: 'secrets', label: t('enforcementAdmin.tabs.secrets') },
    { id: 'test', label: t('enforcementAdmin.tabs.test') },
    { id: 'logs', label: t('enforcementAdmin.tabs.logs') },
  ];

  if (hook.loading) {
    return (
      <AdminRoute>
        <LoadingSpinner message={t('enforcementAdmin.loading')} />
      </AdminRoute>
    );
  }

  return (
    <AdminRoute>
      <div style={{ padding: isMobile ? '1rem' : '2rem' }}>
        <h1 style={{ fontSize: isMobile ? '1.5rem' : '2rem', margin: '0 0 1.5rem 0' }}>
          {t('enforcementAdmin.title')}
        </h1>

        {/* Tabs */}
        {isMobile ? (
          <div style={{ marginBottom: '1.5rem' }}>
            <select
              value={activeTab}
              onChange={e => setActiveTab(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                fontSize: '1rem',
                border: '2px solid #007bff',
                borderRadius: '8px',
                backgroundColor: 'white',
                color: '#333',
                cursor: 'pointer',
                fontWeight: 'bold',
                appearance: 'none',
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23007bff' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 1rem center',
                paddingRight: '2.5rem'
              }}
            >
              {tabs.map(tab => (
                <option key={tab.id} value={tab.id}>{tab.label}</option>
              ))}
            </select>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            borderBottom: '2px solid #dee2e6',
            marginBottom: '2rem',
            justifyContent: 'space-between',
            width: '100%'
          }}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  flex: 1,
                  padding: '1rem 2rem',
                  border: 'none',
                  backgroundColor: 'transparent',
                  borderBottom: activeTab === tab.id ? '3px solid #007bff' : '3px solid transparent',
                  color: activeTab === tab.id ? '#007bff' : '#6c757d',
                  fontWeight: activeTab === tab.id ? 'bold' : 'normal',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  textAlign: 'center'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'profiles' && (
          <ProfilesSection
            profiles={hook.profiles}
            isMobile={isMobile}
            onOpenCreateProfile={hook.openCreateProfile}
            onToggleProfileActive={hook.toggleProfileActive}
            onEdit={hook.editProfile}
            onDelete={hook.deleteProfile}
            onSuccess={showSuccess}
            onError={showApiError}
          />
        )}

        {activeTab === 'mappings' && (
          <MappingsSection
            mappings={hook.mappings}
            isMobile={isMobile}
            onOpenCreateMapping={hook.openCreateMapping}
            onToggleMappingActive={hook.toggleMappingActive}
            onEdit={hook.editMapping}
            onDelete={hook.deleteMapping}
            onSuccess={showSuccess}
            onError={showApiError}
          />
        )}

        {activeTab === 'secrets' && (
          <SecretsSection
            secrets={hook.secrets}
            isMobile={isMobile}
            onOpenCreateSecret={hook.openCreateSecret}
            onRotate={hook.rotateSecret}
            onDelete={hook.deleteSecret}
            onSuccess={showSuccess}
            onError={showApiError}
          />
        )}

        {activeTab === 'test' && (
          <TestProfileSection
            profileOptions={hook.profileOptions}
            testProfileId={hook.testProfileId}
            setTestProfileId={hook.setTestProfileId}
            testRunMode={hook.testRunMode}
            setTestRunMode={hook.setTestRunMode}
            testContextText={hook.testContextText}
            setTestContextText={hook.setTestContextText}
            testResult={hook.testResult}
            onRunTest={hook.runTest}
            onSuccess={showSuccess}
            onError={showApiError}
            onValidationError={showError}
          />
        )}

        {activeTab === 'logs' && (
          <ExecutionLogsSection
            executions={hook.executions}
            logFilters={hook.logFilters}
            setLogFilters={hook.setLogFilters}
            isMobile={isMobile}
            onRefresh={hook.refreshExecutions}
            loading={hook.executionsLoading}
          />
        )}

        <ProfileFormModal
          isOpen={hook.showProfileForm}
          onClose={hook.closeProfileForm}
          form={hook.profileForm}
          setForm={hook.setProfileForm}
          editingId={hook.editingProfileId}
          secrets={hook.secrets}
          onSave={hook.saveProfile}
          onValidationError={showError}
          isMobile={isMobile}
          onSuccess={showSuccess}
        />
        <MappingFormModal
          isOpen={hook.showMappingForm}
          onClose={hook.closeMappingForm}
          form={hook.mappingForm}
          setForm={hook.setMappingForm}
          editingId={hook.editingMappingId}
          profileOptions={hook.profileOptions}
          onSave={hook.saveMapping}
          onValidationError={showError}
          isMobile={isMobile}
          onSuccess={showSuccess}
        />
        <CreateSecretModal
          isOpen={hook.showSecretForm}
          onClose={hook.closeSecretForm}
          secretName={hook.secretName}
          setSecretName={hook.setSecretName}
          secretValue={hook.secretValue}
          setSecretValue={hook.setSecretValue}
          onCreate={hook.createSecret}
          onValidationError={showError}
          onSuccess={showSuccess}
        />
      </div>
    </AdminRoute>
  );
}
