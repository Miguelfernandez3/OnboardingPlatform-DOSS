import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Threat } from '../../../core/domain/entities/Threat';
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
    <div style={{ padding: '1rem' }}>
      <h2>{t('device.threats.title')}</h2>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        marginTop: '1rem'
      }}>
        <thead>
          <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
            <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.id')}</th>
            <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('device.threats.identifier')}</th>
            <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('device.threats.threatMudUrl')}</th>
            <th style={{ padding: '0.75rem', textAlign: 'left' }}>{t('common.actions')}</th>
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
