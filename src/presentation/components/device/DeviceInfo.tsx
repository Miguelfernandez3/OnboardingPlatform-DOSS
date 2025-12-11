import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Device } from '../../../core/domain/entities/Device';

interface DeviceInfoProps {
  device: Device;
  onEdit: () => void;
  onDelete: () => void;
}

/**
 * DeviceInfo - Componente para mostrar información completa del dispositivo
 */
export default function DeviceInfo({ device, onEdit, onDelete }: DeviceInfoProps): JSX.Element {
  const { t } = useTranslation();
  const [showEdk, setShowEdk] = useState<boolean>(false);

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <h2>{t('device.info.title')}</h2>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={onEdit}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            {t('device.info.edit')}
          </button>
          <button
            onClick={onDelete}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            {t('device.info.delete')}
          </button>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '1.5rem'
      }}>
        <div style={{
          padding: '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #dee2e6'
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem', fontWeight: 'bold' }}>
            {t('device.info.basicInfo')}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <strong>{t('device.info.id')}:</strong> {device.id}
            </div>
            {device.identifier && (
              <div>
                <strong>{t('device.info.identifier')}:</strong> {device.identifier}
              </div>
            )}
            {device.name && (
              <div>
                <strong>{t('common.name')}:</strong> {device.name}
              </div>
            )}
            {device.type && (
              <div>
                <strong>{t('common.type')}:</strong> {device.type}
              </div>
            )}
            {device.manufacturer && (
              <div>
                <strong>{t('common.manufacturer')}:</strong> {device.manufacturer}
              </div>
            )}
            <div>
              <strong>{t('common.model')}:</strong> {device.model}
            </div>
            <div>
              <strong>{t('common.status')}:</strong> 
              <span style={{
                marginLeft: '0.5rem',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: device.status === 'active' ? '#d4edda' : '#fff3cd',
                color: device.status === 'active' ? '#155724' : '#856404',
                fontSize: '0.875rem'
              }}>
                {device.status}
              </span>
            </div>
          </div>
        </div>

        <div style={{
          padding: '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #dee2e6'
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem', fontWeight: 'bold' }}>
            {t('device.info.networkInfo')}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {device.ip && (
              <div>
                <strong>{t('device.info.ip')}:</strong> {device.ip}
              </div>
            )}
            {device.mac && (
              <div>
                <strong>{t('device.info.mac')}:</strong> {device.mac}
              </div>
            )}
            {device.mudurl && (
              <div>
                <strong>{t('device.info.mudUrl')}:</strong>{' '}
                <a href={device.mudurl} target="_blank" rel="noopener noreferrer" style={{ color: '#007bff' }}>
                  {device.mudurl}
                </a>
              </div>
            )}
            {device.inventory_id && (
              <div>
                <strong>{t('device.info.inventoryId')}:</strong> {device.inventory_id}
              </div>
            )}
          </div>
        </div>

        {device.edk && (
          <div style={{
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            border: '1px solid #dee2e6'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem', fontWeight: 'bold' }}>
              {t('device.info.securityInfo')}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <strong>{t('device.info.edk')}:</strong>
                <button
                  onClick={() => setShowEdk(!showEdk)}
                  style={{
                    marginLeft: '0.5rem',
                    padding: '0.25rem 0.5rem',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.75rem'
                  }}
                >
                  {showEdk ? t('device.info.hide') : t('device.info.show')}
                </button>
              </div>
              {showEdk && (
                <div style={{
                  padding: '0.5rem',
                  backgroundColor: '#fff',
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  wordBreak: 'break-all'
                }}>
                  {device.edk}
                </div>
              )}
            </div>
          </div>
        )}

        <div style={{
          padding: '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #dee2e6'
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem', fontWeight: 'bold' }}>
            {t('device.info.timestamps')}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {device.createdAt && (
              <div>
                <strong>{t('device.info.createdAt')}:</strong> {formatDate(device.createdAt)}
              </div>
            )}
            {device.updatedAt && (
              <div>
                <strong>{t('device.info.updatedAt')}:</strong> {formatDate(device.updatedAt)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
