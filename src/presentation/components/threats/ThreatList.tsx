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
      <h2 style={{ fontSize: isMobile ? '1.25rem' : '1.5rem' }}>{t('device.threats.title')}</h2>
      
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
        // Tabla con scroll horizontal para desktop
        <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            marginTop: '1rem',
            minWidth: '500px'
          }}>
            <thead>
              <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.id')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('device.threats.identifier')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('device.threats.threatMudUrl')}</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {threats.map((threat) => (
                <tr 
                  key={threat.id}
                  style={{ borderBottom: '1px solid #dee2e6' }}
                >
                  <td style={{ padding: '0.75rem' }}>{threat.id}</td>
                  <td style={{ padding: '0.75rem' }}>{threat.identifier}</td>
                  <td style={{ padding: '0.75rem' }}>
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
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    {threat.threat_mud_file && (
                      <button
                        onClick={() => setSelectedThreat(threat)}
                        style={{
                          padding: '0.25rem 0.5rem',
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
