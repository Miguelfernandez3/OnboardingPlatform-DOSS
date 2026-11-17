import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Device } from '../../../core/domain/entities/Device';
import { Passport } from '../../../core/domain/entities/Passport';
import { MUD } from '../../../core/domain/entities/MUD';
import { useIsMobile } from '../../hooks';
import JsonViewer from '../common/JsonViewer';
import MUDViewer from '../mud/MUDViewer';

interface DeviceInfoProps {
  device: Device;
  passport?: Passport | null;
  mud?: MUD | null;
  onEdit: () => void;
  onDelete: () => void;
}

/**
 * DeviceInfo - Componente para mostrar información completa del dispositivo
 */
export default function DeviceInfo({
  device,
  passport,
  mud,
  onEdit,
  onDelete
}: DeviceInfoProps): JSX.Element {
  const { t } = useTranslation();
  const [showEdk, setShowEdk] = useState<boolean>(false);
  const isMobile = useIsMobile();

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <div style={{ padding: isMobile ? '0.5rem' : '1rem' }}>
      <div style={{ 
        display: 'flex', 
        flexDirection: isMobile ? 'column' : 'row',
        justifyContent: 'space-between', 
        alignItems: isMobile ? 'stretch' : 'center',
        gap: isMobile ? '1rem' : '0',
        marginBottom: isMobile ? '1rem' : '2rem'
      }}>
        <h2 style={{ margin: 0, fontSize: isMobile ? '1.25rem' : '1.5rem' }}>{t('device.info.title')}</h2>
        <div style={{ display: 'flex', gap: isMobile ? '0.5rem' : '1rem' }}>
          <button
            onClick={onEdit}
            style={{
              flex: isMobile ? 1 : 'none',
              padding: isMobile ? '0.75rem 1rem' : '0.5rem 1rem',
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
              flex: isMobile ? 1 : 'none',
              padding: isMobile ? '0.75rem 1rem' : '0.5rem 1rem',
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
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: isMobile ? '1rem' : '1.25rem'
      }}>
        {/* Basic info */}
        <div
          style={{
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            padding: isMobile ? '0.75rem 0.9rem' : '0.85rem 1.1rem',
            backgroundColor: '#ffffff',
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(200px, 2fr) minmax(160px, 1.2fr)',
              columnGap: '1rem',
              rowGap: '0.35rem',
              alignItems: 'center'
            }}
          >
            <div style={{ minWidth: 0 }}>
              <h3
                style={{
                  margin: 0,
                  fontSize: '1rem',
                  fontWeight: 600
                }}
              >
                {t('device.info.basicInfo')}
              </h3>
              <div style={{ marginTop: '0.4rem', fontSize: '0.85rem', color: '#495057' }}>
                <div>
                  <strong>{t('device.info.id')}:</strong> {device.id}
                </div>
                {device.identifier && device.identifier !== device.id && (
                  <div>
                    <strong>{t('device.info.identifier')}:</strong> {device.identifier}
                  </div>
                )}
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.25rem',
                fontSize: '0.85rem',
                color: '#495057'
              }}
            >
              {device.name && (
                <span>
                  <strong>{t('common.name')}:</strong> {device.name}
                </span>
              )}
              {device.type && (
                <span>
                  <strong>{t('common.type')}:</strong> {device.type}
                </span>
              )}
              {device.manufacturer && (
                <span>
                  <strong>{t('common.manufacturer')}:</strong> {device.manufacturer}
                </span>
              )}
              {device.model && (
                <span>
                  <strong>{t('common.model')}:</strong> {device.model}
                </span>
              )}
              <span>
                <strong>{t('common.status')}:</strong>{' '}
                <span
                  style={{
                    padding: '0.18rem 0.55rem',
                    borderRadius: '999px',
                    backgroundColor: device.status === 'active' ? '#d4edda' : '#fff3cd',
                    color: device.status === 'active' ? '#155724' : '#856404',
                    fontWeight: 500,
                    fontSize: '0.8rem'
                  }}
                >
                  {device.status === 'active' ? t('devices.active') : t('devices.inactive')}
                </span>
              </span>
            </div>
          </div>
        </div>

        {/* Network info */}
        {(device.ip || device.mac || device.mudurl || device.inventory_id) && (
          <div
            style={{
              border: '1px solid #dee2e6',
              borderRadius: '8px',
              padding: isMobile ? '0.75rem 0.9rem' : '0.85rem 1.1rem',
              backgroundColor: '#ffffff',
              boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
            }}
          >
            <h3
              style={{
                margin: 0,
                marginBottom: '0.5rem',
                fontSize: '1rem',
                fontWeight: 600
              }}
            >
              {t('device.info.networkInfo')}
            </h3>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.3rem',
                fontSize: '0.85rem',
                color: '#495057'
              }}
            >
              {device.ip && (
                <span>
                  <strong>{t('device.info.ip')}:</strong> {device.ip}
                </span>
              )}
              {device.mac && (
                <span>
                  <strong>{t('device.info.mac')}:</strong> {device.mac}
                </span>
              )}
              {device.mudurl && (
                <span style={{ wordBreak: 'break-all' }}>
                  <strong>{t('device.info.mudUrl')}:</strong>{' '}
                  <a href={device.mudurl} target="_blank" rel="noopener noreferrer" style={{ color: '#007bff' }}>
                    {device.mudurl}
                  </a>
                </span>
              )}
              {device.inventory_id && (
                <span>
                  <strong>{t('device.info.idspId')}:</strong> {device.inventory_id}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Security info */}
        {device.edk && (
          <div
            style={{
              border: '1px solid #dee2e6',
              borderRadius: '8px',
              padding: isMobile ? '0.75rem 0.9rem' : '0.85rem 1.1rem',
              backgroundColor: '#ffffff',
              boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
            }}
          >
            <h3
              style={{
                margin: 0,
                marginBottom: '0.5rem',
                fontSize: '1rem',
                fontWeight: 600
              }}
            >
              {t('device.info.securityInfo')}
            </h3>
            <div style={{ fontSize: '0.85rem', color: '#495057' }}>
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
              {showEdk && (
                <div
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.5rem',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '4px',
                    fontFamily: 'monospace',
                    fontSize: '0.85rem',
                    wordBreak: 'break-all'
                  }}
                >
                  {device.edk}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Timestamps */}
        {(device.createdAt || device.updatedAt) && (
          <div
            style={{
              border: '1px solid #dee2e6',
              borderRadius: '8px',
              padding: isMobile ? '0.75rem 0.9rem' : '0.85rem 1.1rem',
              backgroundColor: '#ffffff',
              boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
            }}
          >
            <h3
              style={{
                margin: 0,
                marginBottom: '0.5rem',
                fontSize: '1rem',
                fontWeight: 600
              }}
            >
              {t('device.info.timestamps')}
            </h3>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.3rem',
                fontSize: '0.85rem',
                color: '#495057'
              }}
            >
              {device.createdAt && (
                <span>
                  <strong>{t('device.info.createdAt')}:</strong> {formatDate(device.createdAt)}
                </span>
              )}
              {device.updatedAt && (
                <span>
                  <strong>{t('device.info.updatedAt')}:</strong> {formatDate(device.updatedAt)}
                </span>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Digital Passport Section */}
      {passport && (
        <div style={{ marginTop: '1rem' }}>
          {/* <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', fontWeight: 'bold' }}>
            {t('device.info.passportSection')}
          </h3> */}
          <div style={{
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            border: '1px solid #dee2e6'
          }}>
            <JsonViewer data={passport.toJSON()} title={t('device.passport.title')} />
          </div>
        </div>
      )}

      {/* MUD File Section */}
      {mud && (
        <div style={{ marginTop: '1rem' }}>
          {/* <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', fontWeight: 'bold' }}>
            {t('device.info.mudSection')}
          </h3> */}
          <div style={{
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            border: '1px solid #dee2e6'
          }}>
            <MUDViewer mud={mud} />
          </div>
        </div>
      )}
    </div>
  );
}
