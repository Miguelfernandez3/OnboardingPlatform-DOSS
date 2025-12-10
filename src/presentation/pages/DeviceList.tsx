import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useDevices } from '../hooks/useDevices';
import LoadingSpinner from '../components/common/LoadingSpinner';

/**
 * DeviceList - Página que lista todos los dispositivos
 */
export default function DeviceList(): JSX.Element {
  const { t } = useTranslation();
  const { devices, loading, error } = useDevices();
  const navigate = useNavigate();

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
    <div style={{ padding: '2rem' }}>
      <h1>{t('devices.title')}</h1>
      {devices.length === 0 ? (
        <p>{t('devices.noDevices')}</p>
      ) : (
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          marginTop: '1rem'
        }}>
          <thead>
            <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.id')}</th>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.name')}</th>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.type')}</th>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.manufacturer')}</th>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.model')}</th>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.status')}</th>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr 
                key={device.id}
                style={{ borderBottom: '1px solid #dee2e6' }}
              >
                <td style={{ padding: '0.75rem' }}>{device.id}</td>
                <td style={{ padding: '0.75rem' }}>{device.name}</td>
                <td style={{ padding: '0.75rem' }}>{device.type}</td>
                <td style={{ padding: '0.75rem' }}>{device.manufacturer}</td>
                <td style={{ padding: '0.75rem' }}>{device.model}</td>
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
                <td style={{ padding: '0.75rem' }}>
                  <button
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
      )}
    </div>
  );
}

