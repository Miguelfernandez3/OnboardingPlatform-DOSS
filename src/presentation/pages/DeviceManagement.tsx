import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../config';
import { Passport } from '../../core/domain/entities/Passport';
import { MUD } from '../../core/domain/entities/MUD';
import { usePolicies, useDevice, useThreats, useMitigations } from '../hooks';
import { PolicyList, EnforcementStatus, LoadingSpinner, DeviceInfo, DeviceEditForm, ThreatList, MitigationList } from '../components';

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
  const [activeTab, setActiveTab] = useState<string>('info');
  const [passport, setPassport] = useState<Passport | null>(null);
  const [mud, setMud] = useState<MUD | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showEditForm, setShowEditForm] = useState<boolean>(false);
  
  const { 
    device,
    loading: deviceLoading,
    updateDevice,
    deleteDevice,
  } = useDevice(id);

  const { 
    policies, 
    loading: policiesLoading, 
    error: policiesError,
    enforcementStatus,
  } = usePolicies(id);

  const {
    threats,
    loading: threatsLoading,
    error: threatsError
  } = useThreats(id);

  const {
    mitigations,
    loading: mitigationsLoading,
    error: mitigationsError,
    enforceMitigation,
    revokeMitigation
  } = useMitigations(id);

  useEffect(() => {
    const fetchData = async (): Promise<void> => {
      if (!id) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        const [passportData, mudData] = await Promise.all([
          apiClient.getDevicePassport(id).catch(() => null),
          apiClient.getDeviceMUD(id).catch(() => null)
        ]);
        
        setPassport(passportData);
        setMud(mudData);
      } catch (err) {
        setError((err as Error).message || 'Error al cargar datos del dispositivo');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const tabs: Tab[] = [
    { id: 'info', label: t('device.tabs.info') },
    { id: 'threats', label: t('device.tabs.threats') },
    { id: 'mitigations', label: t('device.tabs.mitigations') },
    { id: 'policies', label: t('device.tabs.policies') }
  ];

  const handleEdit = (): void => {
    setShowEditForm(true);
  };

  const handleSave = async (data: Partial<import('../../core/domain/entities/Device').Device>): Promise<void> => {
    try {
      await updateDevice(data);
      setShowEditForm(false);
      alert(t('device.info.saveSuccess'));
    } catch (err) {
      alert(`${t('common.error')}: ${(err as Error).message}`);
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!window.confirm(t('device.info.deleteConfirm'))) {
      return;
    }

    try {
      await deleteDevice();
      alert(t('device.info.deleteSuccess'));
      navigate('/devices');
    } catch (err) {
      alert(`${t('common.error')}: ${(err as Error).message}`);
    }
  };

  const handleCreatePolicy = (): void => {
    navigate(`/devices/${id}/policies/create`);
  };

  if (loading || deviceLoading) {
    return <LoadingSpinner message={t('device.passport.loading')} />;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h1>{t('device.management')} {device?.name || id}</h1>

      {error && (
        <div style={{
          marginBottom: '1rem',
          padding: '1rem',
          backgroundColor: '#f8d7da',
          color: '#721c24',
          borderRadius: '4px',
          border: '1px solid #f5c6cb'
        }}>
          <strong>{t('common.error')}:</strong> {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{
        display: 'flex',
        borderBottom: '2px solid #dee2e6',
        marginBottom: '2rem',
        justifyContent: 'space-between', // distribuye los botones a lo largo del ancho
        width: '100%'
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1, // cada botón toma el mismo tamaño y se distribuyen
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
                  onDelete={handleDelete}
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
              onEnforce={enforceMitigation}
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
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

