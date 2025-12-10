import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../config';
import { Passport } from '../../core/domain/entities/Passport';
import { MUD } from '../../core/domain/entities/MUD';
import { usePolicies } from '../hooks/usePolicies';
import JsonViewer from '../components/common/JsonViewer';
import MUDViewer from '../components/mud/MUDViewer';
import PolicyList from '../components/policies/PolicyList';
import IDSP2Uploader from '../components/policies/IDSP2Uploader';
import MSPLEditor from '../components/mspl/MSPLEditor';
import EnforcementStatus from '../components/policies/EnforcementStatus';
import LoadingSpinner from '../components/common/LoadingSpinner';

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
  const [activeTab, setActiveTab] = useState<string>('passport');
  const [passport, setPassport] = useState<Passport | null>(null);
  const [mud, setMud] = useState<MUD | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  const { 
    policies, 
    loading: policiesLoading, 
    error: policiesError,
    enforcementStatus,
    applyPolicy,
    applyIDSP2
  } = usePolicies(id);

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
    { id: 'passport', label: t('device.tabs.passport') },
    { id: 'mud', label: t('device.tabs.mud') },
    { id: 'policies', label: t('device.tabs.policies') },
    { id: 'apply', label: t('device.tabs.apply') }
  ];

  if (loading) {
    return <LoadingSpinner message={t('device.passport.loading')} />;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h1>{t('device.management')} {id}</h1>

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
        marginBottom: '2rem'
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '1rem 2rem',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: activeTab === tab.id ? '3px solid #007bff' : '3px solid transparent',
              color: activeTab === tab.id ? '#007bff' : '#6c757d',
              fontWeight: activeTab === tab.id ? 'bold' : 'normal',
              cursor: 'pointer',
              fontSize: '1rem'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'passport' && (
          <div>
            {passport ? (
              <JsonViewer data={passport.toJSON()} title={t('device.passport.title')} />
            ) : (
              <p>{t('device.passport.noData')}</p>
            )}
          </div>
        )}

        {activeTab === 'mud' && (
          <div>
            {mud ? (
              <MUDViewer mud={mud} />
            ) : (
              <p>{t('device.mud.noData')}</p>
            )}
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
              <PolicyList policies={policies} />
            )}
          </div>
        )}

        {activeTab === 'apply' && (
          <div>
            <div style={{ marginBottom: '2rem' }}>
              <IDSP2Uploader deviceId={id || ''} onApply={applyIDSP2} />
            </div>
            
            <div style={{ marginTop: '3rem', borderTop: '2px solid #dee2e6', paddingTop: '2rem' }}>
              <h2>{t('policies.createEdit.title')}</h2>
              <MSPLEditor
                onApply={async (msplXml: string) => {
                  try {
                    await applyPolicy(msplXml);
                    alert(t('policies.createEdit.success'));
                  } catch (err) {
                    alert(`${t('policies.createEdit.error')}: ${(err as Error).message}`);
                  }
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

