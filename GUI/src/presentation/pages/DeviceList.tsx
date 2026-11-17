import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { useDevices, useIsMobile } from '../hooks';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { deviceService } from '../../infrastructure/services/deviceService';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { DeviceCreateForm } from '../components';
import { useToast } from '../../infrastructure/notifications/useToast';
import { CreateDeviceFromDSPInput } from '../../core/ports';

/**
 * DeviceList - Página que lista todos los dispositivos
 */
export default function DeviceList(): JSX.Element {
  const { t, i18n } = useTranslation();
  const { devices, loading, error, createDeviceFromDSP } = useDevices();

  // Orden por fecha de onboarding (createdAt), más reciente primero; sin fecha al final.
  const sortedDevices = useMemo(
    () => [...devices].sort((a, b) => {
      const ta = a.createdAt ? new Date(a.createdAt).getTime() : 0;
      const tb = b.createdAt ? new Date(b.createdAt).getTime() : 0;
      return tb - ta;
    }),
    [devices]
  );

  const formatOnboardingDate = (iso?: string): string =>
    iso ? new Date(iso).toLocaleDateString(i18n.language, { dateStyle: 'medium' }) : '-';
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isMobile = useIsMobile();
  const { showTranslated } = useToast();
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);

  // Prefetch device data on hover
  const handleDevicePrefetch = (deviceId: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.devices.detail(deviceId),
      queryFn: () => deviceService.getDevice(deviceId),
      staleTime: 1000 * 60 * 5, // 5 minutos
    });
  };

  const handleCreateDevice = async (data: CreateDeviceFromDSPInput): Promise<void> => {
    const createdDevice = await createDeviceFromDSP(data);
    setShowCreateForm(false);
    showTranslated('device.create.success', 'success');
    navigate(`/devices/${createdDevice.id}`);
  };

  if (loading) {
    return <LoadingSpinner message={t('devices.loadingDevices')} />;
  }

  if (error) {
    return (
      <div style={{ padding: '2rem' }}>
        <div style={{
          padding: '1rem',
          backgroundColor: '#f8d7da',
          color: '#721c24',
          borderRadius: '4px',
          border: '1px solid #f5c6cb'
        }}>
          <strong>{t('common.error')}:</strong> {error}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: isMobile ? '1rem' : '2rem' }}>
      <div style={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        justifyContent: 'space-between',
        alignItems: isMobile ? 'stretch' : 'center',
        gap: '1rem'
      }}>
        <h1 style={{ fontSize: isMobile ? '1.5rem' : '2rem', margin: 0 }}>{t('devices.title')}</h1>
        <button
          onClick={() => setShowCreateForm(true)}
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: '#198754',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.95rem',
            fontWeight: 600
          }}
        >
          {t('devices.addDevice')}
        </button>
      </div>
      {devices.length === 0 ? (
        <p>{t('devices.noDevices')}</p>
      ) : isMobile ? (
        // Vista de tarjetas para móvil
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {sortedDevices.map((device) => (
            <div
              key={device.id}
              style={{
                padding: '1rem',
                backgroundColor: '#fff',
                borderRadius: '8px',
                border: '1px solid #dee2e6',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{device.name}</h3>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  backgroundColor: device.status === 'active' ? '#d4edda' : '#fff3cd',
                  color: device.status === 'active' ? '#155724' : '#856404',
                  fontSize: '0.75rem'
                }}>
                  {device.status === 'active' ? t('devices.active') : t('devices.inactive')}
                </span>
              </div>
              <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>
                <div><strong>{t('common.type')}:</strong> {device.type || '-'}</div>
                <div><strong>{t('common.manufacturer')}:</strong> {device.manufacturer || '-'}</div>
                <div><strong>{t('common.model')}:</strong> {device.model || '-'}</div>
                <div><strong>{t('common.onboardingDate')}:</strong> {formatOnboardingDate(device.createdAt)}</div>
              </div>
              <button
                onMouseEnter={() => handleDevicePrefetch(device.id)}
                onClick={() => navigate(`/devices/${device.id}`)}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                {t('devices.viewDetails')}
              </button>
            </div>
          ))}
        </div>
      ) : (
        // Tabla con scroll horizontal para desktop/tablet
        <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            marginTop: '1rem',
            minWidth: '700px'
          }}>
            <thead>
              <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.id')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.name')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.type')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.manufacturer')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.model')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.status')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.onboardingDate')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {sortedDevices.map((device) => (
                <tr 
                  key={device.id}
                  style={{ borderBottom: '1px solid #dee2e6' }}
                >
                  <td style={{ padding: '0.75rem' }}>{device.id}</td>
                  <td style={{ padding: '0.75rem' }}>{device.name || '-'}</td>
                  <td style={{ padding: '0.75rem' }}>{device.type || '-'}</td>
                  <td style={{ padding: '0.75rem' }}>{device.manufacturer || '-'}</td>
                  <td style={{ padding: '0.75rem' }}>{device.model || '-'}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      backgroundColor: device.status === 'active' ? '#d4edda' : '#fff3cd',
                      color: device.status === 'active' ? '#155724' : '#856404',
                      fontSize: '0.875rem'
                    }}>
                      {device.status === 'active' ? t('devices.active') : t('devices.inactive')}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', whiteSpace: 'nowrap' }}>{formatOnboardingDate(device.createdAt)}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <button
                      onMouseEnter={() => handleDevicePrefetch(device.id)}
                      onClick={() => navigate(`/devices/${device.id}`)}
                      style={{
                        padding: '0.5rem 1rem',
                        backgroundColor: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {t('devices.viewDetails')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreateForm && (
        <DeviceCreateForm
          onCreate={handleCreateDevice}
          onCancel={() => setShowCreateForm(false)}
        />
      )}
    </div>
  );
}
