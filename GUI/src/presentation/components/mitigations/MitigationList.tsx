import { useTranslation } from 'react-i18next';
import { Mitigation } from '../../../core/domain/entities/Mitigation';
import LoadingSpinner from '../common/LoadingSpinner';
import MitigationCard from './MitigationCard';

interface MitigationListProps {
  mitigations: Mitigation[];
  loading: boolean;
  error: string | null;
  onEnforce: (mitigationId: string) => Promise<void>;
  onRevoke: (mitigationId: string) => Promise<void>;
}

/**
 * MitigationList - Componente para mostrar lista de mitigations con botones enforce/revoke
 */
export default function MitigationList({ 
  mitigations, 
  loading, 
  error, 
  onEnforce, 
  onRevoke 
}: MitigationListProps): JSX.Element {
  const { t } = useTranslation();

  if (loading) {
    return <LoadingSpinner message={t('device.mitigations.loading')} />;
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

  if (mitigations.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>{t('device.mitigations.noMitigations')}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '1rem' }}>
      <h2>{t('device.mitigations.title')}</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
        {mitigations.map((mitigation) => (
          <MitigationCard
            key={mitigation.id}
            mitigation={mitigation}
            onEnforce={() => onEnforce(mitigation.id)}
            onRevoke={() => onRevoke(mitigation.id)}
          />
        ))}
      </div>
    </div>
  );
}
