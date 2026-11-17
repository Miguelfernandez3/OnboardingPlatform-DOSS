import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../config';
import { Passport } from '../../core/domain/entities/Passport';
import { MUD } from '../../core/domain/entities/MUD';
import { usePolicies, useDevice, useThreats, useMitigations, useIsMobile, useDeviceLogs } from '../hooks';
import { PolicyList, EnforcementStatus, LoadingSpinner, DeviceInfo, DeviceEditForm, ThreatList, MitigationList, ConfirmDeleteDeviceModal } from '../components';
import DeviceLogsTimeline from '../components/device/DeviceLogsTimeline';
import { useToast } from '../../infrastructure/notifications/useToast';
import { policyServiceActions } from '../../infrastructure/services/policyService';
import {
  getEnforcementPrerequisitesMissing,
  isEnforcementPrerequisitesConflict
} from '../../infrastructure/api/errors/errorUtils';
import EnforceContextModal from '../components/enforcement/EnforceContextModal';
import { splitUpdateFromForm, type MissingItem } from '../utils/enforcementContextForm';
import { queryKeys } from '../../infrastructure/query/queryKeys';

interface Tab {
  id: string;
  label: string;
}

/**
 * DeviceManagement - Página principal de gestión del dispositivo
 * Incluye tabs para: Pasaporte, MUD, Políticas, Aplicar Política
 */
export default function DeviceManagement(): JSX.Element {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const queryClient = useQueryClient();
  const { showTranslated, showApiError } = useToast();
  
  // Inicializar el tab activo desde el hash de la URL o por defecto 'info'
  const getInitialTab = (): string => {
    const hash = window.location.hash.replace('#', '');
    const validTabs = ['info', 'threats', 'mitigations', 'policies', 'logs'];
    return validTabs.includes(hash) ? hash : 'info';
  };
  
  const [activeTab, setActiveTab] = useState<string>(getInitialTab());
  const [passport, setPassport] = useState<Passport | null>(null);
  const [mud, setMud] = useState<MUD | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [showEditForm, setShowEditForm] = useState<boolean>(false);
  const [ctxModal, setCtxModal] = useState<{
    target: { kind: 'policy'; policyId: string } | { kind: 'mitigation'; mitigationId: string };
    missing: MissingItem[];
  } | null>(null);
  
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);
  const [deleteBusy, setDeleteBusy] = useState<boolean>(false);

  const { 
    device,
    loading: deviceLoading,
    updateDevice,
    deleteDevice,
    isDeviceDeleted,
  } = useDevice(id);

  const activeScopeId = id && !isDeviceDeleted ? id : undefined;

  const { 
    policies, 
    loading: policiesLoading, 
    error: policiesError,
    enforcementStatus,
    enforcePolicy,
  } = usePolicies(activeScopeId);

  const {
    threats,
    loading: threatsLoading,
    error: threatsError
  } = useThreats(activeScopeId);

  const {
    mitigations,
    loading: mitigationsLoading,
    error: mitigationsError,
    enforceMitigation,
    revokeMitigation
  } = useMitigations(activeScopeId);

  const {
    logs: deviceLogs,
    loading: deviceLogsLoading,
    error: deviceLogsError,
  } = useDeviceLogs(activeScopeId);

  useEffect(() => {
    if (!id || isDeviceDeleted) {
      setPassport(null);
      setMud(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const fetchData = async (showLoading = false): Promise<void> => {
      try {
        if (showLoading) {
          setLoading(true);
        }
        
        const [passportData, mudData] = await Promise.all([
          apiClient.getDevicePassport(id).catch(() => null),
          apiClient.getDeviceMUD(id).catch(() => null)
        ]);

        if (!cancelled) {
          setPassport(passportData);
          setMud(mudData);
        }
      } catch (err) {
        // Los errores se mostrarán automáticamente como toast
        // No necesitamos setError aquí ya que los errores de API se manejan globalmente
      } finally {
        if (!cancelled && showLoading) {
          setLoading(false);
        }
      }
    };

    void fetchData(true);
    const intervalId = window.setInterval(() => {
      void fetchData(false);
    }, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [id, isDeviceDeleted]);

  // Sincronizar el hash de la URL con el tab activo cuando cambia la URL
  useEffect(() => {
    const handleHashChange = (): void => {
      const hash = window.location.hash.replace('#', '');
      const validTabs = ['info', 'threats', 'mitigations', 'policies', 'logs'];
      if (hash && validTabs.includes(hash)) {
        setActiveTab(hash);
      } else if (!hash) {
        // Si no hay hash, establecer 'info' por defecto
        setActiveTab('info');
      }
    };

    // Verificar el hash inicial
    handleHashChange();

    // Escuchar cambios en el hash
    window.addEventListener('hashchange', handleHashChange);
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, [id]); // Ejecutar cuando cambie el id del dispositivo o al montar

  // Actualizar el hash cuando cambia el tab activo
  const handleTabChange = (tabId: string): void => {
    setActiveTab(tabId);
    window.location.hash = tabId;
  };

  const tabs: Tab[] = [
    { id: 'info', label: t('device.tabs.info') },
    { id: 'threats', label: t('device.tabs.threats') },
    { id: 'mitigations', label: t('device.tabs.mitigations') },
    { id: 'policies', label: t('device.tabs.policies') },
    { id: 'logs', label: t('device.tabs.logs') },
  ];

  const handleEdit = (): void => {
    setShowEditForm(true);
  };

  const handleSave = async (data: Partial<import('../../core/domain/entities/Device').Device>): Promise<void> => {
    try {
      await updateDevice(data);
      setShowEditForm(false);
      showTranslated('device.info.saveSuccess', 'success');
    } catch (err) {
      showApiError(err);
    }
  };

  const handleRequestDelete = (): void => {
    setShowDeleteModal(true);
  };

  const handleConfirmDeleteDevice = async (): Promise<void> => {
    try {
      setDeleteBusy(true);
      await deleteDevice();
      showTranslated('device.info.deleteSuccess', 'success');
      setShowDeleteModal(false);
      navigate('/devices', { replace: true });
    } catch (err) {
      showApiError(err);
    } finally {
      setDeleteBusy(false);
    }
  };

  const handleCreatePolicy = (): void => {
    navigate(`/devices/${id}/policies/create`);
  };

  const handleEnforcePolicy = async (policyId: string): Promise<void> => {
    if (!id || !device) return;
    let missing: MissingItem[] = [];
    try {
      const g = await policyServiceActions.getPolicyEnforcementGaps(id, policyId);
      missing = (g.missing || []) as MissingItem[];
    } catch {
      /* gaps no disponibles: seguimos e intentamos enforce */
    }
    if (missing.length > 0) {
      setCtxModal({ target: { kind: 'policy', policyId }, missing });
      return;
    }
    try {
      await enforcePolicy(policyId);
      showTranslated('policies.enforceSuccess', 'success');
    } catch (err) {
      if (isEnforcementPrerequisitesConflict(err)) {
        const fallbackMissing = getEnforcementPrerequisitesMissing(err) as MissingItem[];
        if (fallbackMissing.length > 0) {
          setCtxModal({
            target: { kind: 'policy', policyId },
            missing: fallbackMissing
          });
          return;
        }
      }
      showApiError(err);
    }
  };

  const handleEnforceMitigation = async (mitigationId: string): Promise<void> => {
    if (!id || !device) return;
    const mitigation = mitigations.find((m) => m.id === mitigationId);
    if (!mitigation) {
      showApiError(new Error('Mitigation not found'));
      return;
    }
    const fromList = (mitigation.enforcementGaps?.missing || []) as MissingItem[];
    if (fromList.length > 0) {
      setCtxModal({ target: { kind: 'mitigation', mitigationId }, missing: fromList });
      return;
    }
    try {
      await enforceMitigation(mitigationId);
      showTranslated('device.mitigations.enforceSuccess', 'success');
    } catch (err) {
      if (isEnforcementPrerequisitesConflict(err)) {
        const fallbackMissing = getEnforcementPrerequisitesMissing(err) as MissingItem[];
        if (fallbackMissing.length > 0) {
          setCtxModal({
            target: { kind: 'mitigation', mitigationId },
            missing: fallbackMissing
          });
          return;
        }
      }
      showApiError(err);
    }
  };

  const handleEnforceContextSubmit = async (form: Record<string, string>): Promise<void> => {
    if (!id || !ctxModal) return;
    if (!device) {
      showApiError(new Error(t('common.error')));
      return;
    }
    const { update, extraContext } = splitUpdateFromForm(ctxModal.missing, form, device);
    if (Object.keys(update).length > 0) {
      await updateDevice(update);
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.mitigations(id!) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.detail(id!) });
    }
    const extra =
      Object.keys(extraContext).length > 0 ? { extraContext } : undefined;
    if (ctxModal.target.kind === 'policy') {
      await enforcePolicy(ctxModal.target.policyId, extra);
    } else {
      await enforceMitigation(ctxModal.target.mitigationId, extra);
    }
    setCtxModal(null);
    showTranslated(
      ctxModal.target.kind === 'policy' ? 'policies.enforceSuccess' : 'device.mitigations.enforceSuccess',
      'success'
    );
  };

  if (loading || deviceLoading) {
    return <LoadingSpinner message={t('device.passport.loading')} />;
  }

  return (
    <div style={{ padding: isMobile ? '1rem' : '2rem'}}>
      <h1 style={{ fontSize: isMobile ? '1.5rem' : '2rem', marginBottom: '1.5rem'  }}>
        {t('device.management', { deviceName: device?.name || id })}
      </h1>

      {/* Tabs - Dropdown en móvil, tabs en desktop */}
      {isMobile ? (
        <div style={{ marginBottom: '1.5rem'}}>
          <select
            value={activeTab}
            onChange={(e) => handleTabChange(e.target.value)}
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
            {tabs.map((tab) => (
              <option key={tab.id} value={tab.id}>
                {tab.label}
              </option>
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
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
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
      <div>
        {activeTab === 'info' && (
          <div>
            {device ? (
              <>
                <DeviceInfo 
                  device={device}
                  passport={passport}
                  mud={mud}
                  onEdit={handleEdit}
                  onDelete={handleRequestDelete}
                />
                {showEditForm && (
                  <DeviceEditForm
                    device={device}
                    onSave={handleSave}
                    onCancel={() => setShowEditForm(false)}
                  />
                )}
              </>
            ) : (
              <p>{t('device.info.noData')}</p>
            )}
          </div>
        )}

        {activeTab === 'logs' && (
          <div>
            <h2 style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', marginBottom: '1rem' }}>
              {t('device.tabs.logs')}
            </h2>
            <DeviceLogsTimeline
              timeline={deviceLogs}
              loading={deviceLogsLoading}
              error={deviceLogsError}
              showTitle={false}
            />
          </div>
        )}

        {activeTab === 'threats' && (
          <div>
            <ThreatList 
              threats={threats}
              loading={threatsLoading}
              error={threatsError}
            />
          </div>
        )}

        {activeTab === 'mitigations' && (
          <div>
            <MitigationList
              mitigations={mitigations}
              loading={mitigationsLoading}
              error={mitigationsError}
              onEnforce={handleEnforceMitigation}
              onRevoke={revokeMitigation}
            />
          </div>
        )}

        {activeTab === 'policies' && (
          <div>
            {enforcementStatus && (
              <div style={{ marginBottom: '2rem' }}>
                <EnforcementStatus
                  status={enforcementStatus.status}
                  message={enforcementStatus.message}
                  timestamp={enforcementStatus.timestamp}
                />
              </div>
            )}
            {policiesLoading ? (
              <LoadingSpinner message={t('policies.loading')} />
            ) : policiesError ? (
              <div style={{
                padding: '1rem',
                backgroundColor: '#f8d7da',
                color: '#721c24',
                borderRadius: '4px'
              }}>
                <strong>{t('common.error')}:</strong> {policiesError}
              </div>
            ) : (
              <PolicyList 
                policies={policies}
                onCreateNew={handleCreatePolicy}
                onEnforcePolicy={handleEnforcePolicy}
              />
            )}
          </div>
        )}
      </div>
      {ctxModal && (
        <EnforceContextModal
          open
          title={
            ctxModal.target.kind === 'policy'
              ? t('enforceContext.titlePolicy')
              : t('enforceContext.titleMitigation')
          }
          missing={ctxModal.missing}
          onCancel={() => setCtxModal(null)}
          onSubmit={handleEnforceContextSubmit}
        />
      )}
      <ConfirmDeleteDeviceModal
        isOpen={showDeleteModal}
        deviceLabel={(device?.name || device?.identifier || id || '').trim()}
        onClose={() => {
          if (!deleteBusy) setShowDeleteModal(false);
        }}
        onConfirm={handleConfirmDeleteDevice}
        isLoading={deleteBusy}
      />
    </div>
  );
}
