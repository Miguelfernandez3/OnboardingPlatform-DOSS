import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Threat } from '../../../core/domain/entities/Threat';
import { useIsMobile } from '../../hooks';
import LoadingSpinner from '../common/LoadingSpinner';
import ThreatMudModal from './ThreatMudModal';

interface ThreatListProps {
  threats: Threat[];
  loading: boolean;
  error: string | null;
}

/**
 * ThreatList - Componente para mostrar lista de threats
 */
export default function ThreatList({ threats, loading, error }: ThreatListProps): JSX.Element {
  const { t } = useTranslation();
  const [selectedThreat, setSelectedThreat] = useState<Threat | null>(null);
  const isMobile = useIsMobile();

  if (loading) {
    return <LoadingSpinner message={t('device.threats.loading')} />;
  }

  if (error) {
    return (
      <div style={{
        padding: '1rem',
        backgroundColor: '#f8d7da',
        color: '#721c24',
        borderRadius: '4px',
        border: '1px solid #f5c6cb'
      }}>
        <strong>{t('common.error')}:</strong> {error}
      </div>
    );
  }

  if (threats.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>{t('device.threats.noThreats')}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: isMobile ? '0.5rem' : '1rem' }}>
      <h2 style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', marginBottom: isMobile ? '0.75rem' : '1rem' }}>
        {t('device.threats.title')}
      </h2>
      
      {isMobile ? (
        // Vista de tarjetas para móvil
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {threats.map((threat) => (
            <div
              key={threat.id}
              style={{
                padding: '1rem',
                backgroundColor: '#fff',
                borderRadius: '8px',
                border: '1px solid #dee2e6',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              <div style={{ marginBottom: '0.5rem' }}>
                <strong>{t('device.threats.identifier')}:</strong> {threat.identifier}
              </div>
              <div style={{ marginBottom: '0.75rem', fontSize: '0.875rem', color: '#666' }}>
                <strong>{t('common.id')}:</strong> {threat.id}
              </div>
              {threat.threat_mud_url && (
                <div style={{ marginBottom: '0.75rem', wordBreak: 'break-all' }}>
                  <strong>{t('device.threats.threatMudUrl')}:</strong>{' '}
                  <a 
                    href={threat.threat_mud_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#007bff', fontSize: '0.875rem' }}
                  >
                    {threat.threat_mud_url}
                  </a>
                </div>
              )}
              {threat.threat_mud_file && (
                <button
                  onClick={() => setSelectedThreat(threat)}
                  style={{
                    width: '100%',
                    padding: '0.5rem 1rem',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  {t('device.threats.viewMud')}
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        // Vista tipo tarjeta alineada horizontalmente para desktop
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
          {threats.map((threat) => (
            <div
              key={threat.id}
              style={{
                border: '1px solid #dee2e6',
                borderRadius: '8px',
                padding: '0.75rem 1rem',
                backgroundColor: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(220px, 1.7fr) minmax(260px, 2fr) auto',
                  columnGap: '1rem',
                  rowGap: '0.25rem',
                  alignItems: 'center'
                }}
              >
                {/* Identificador + ID */}
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}
                    title={threat.identifier}
                  >
                    {t('device.threats.identifier')}: {threat.identifier}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#6c757d', marginTop: '0.15rem' }}>
                    <strong>{t('common.id')}:</strong> {threat.id}
                  </div>
                </div>

                {/* Threat MUD URL */}
                <div
                  style={{
                    fontSize: '0.85rem',
                    color: '#495057',
                    wordBreak: 'break-all'
                  }}
                >
                  <strong>{t('device.threats.threatMudUrl')}:</strong>{' '}
                  {threat.threat_mud_url ? (
                    <a
                      href={threat.threat_mud_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#007bff' }}
                    >
                      {threat.threat_mud_url}
                    </a>
                  ) : (
                    '-'
                  )}
                </div>

                {/* Botón ver MUD */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center'
                  }}
                >
                  {threat.threat_mud_file && (
                    <button
                      onClick={() => setSelectedThreat(threat)}
                      style={{
                        padding: '0.45rem 1rem',
                        backgroundColor: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {t('device.threats.viewMud')}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedThreat && selectedThreat.threat_mud_file && (
        <ThreatMudModal
          threatMudFile={selectedThreat.threat_mud_file}
          threatIdentifier={selectedThreat.identifier}
          onClose={() => setSelectedThreat(null)}
        />
      )}
    </div>
  );
}
