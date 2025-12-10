import { useTranslation } from 'react-i18next';
import { Policy } from '../../../core/domain/entities/Policy';
import MSPLViewer from '../mspl/MSPLViewer';

interface PolicyListProps {
  policies: Policy[];
}

/**
 * PolicyList - Componente para listar políticas aplicadas
 */
export default function PolicyList({ policies }: PolicyListProps): JSX.Element {
  const { t } = useTranslation();

  if (!policies || policies.length === 0) {
    return <p>{t('policies.noPolicies')}</p>;
  }

  return (
    <div>
      <h2>{t('policies.title')}</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {policies.map((policy) => (
          <div 
            key={policy.id} 
            style={{
              border: '1px solid #ddd',
              borderRadius: '8px',
              padding: '1rem',
              backgroundColor: '#f9f9f9'
            }}
          >
            <div style={{ marginBottom: '1rem' }}>
              <h3>{policy.name || `${t('policies.id')} ${policy.id}`}</h3>
              <p><strong>{t('policies.id')}:</strong> {policy.id}</p>
              <p><strong>{t('policies.status')}:</strong> 
                <span style={{
                  marginLeft: '0.5rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  backgroundColor: policy.status === 'active' ? '#d4edda' : '#fff3cd',
                  color: policy.status === 'active' ? '#155724' : '#856404'
                }}>
                  {policy.status}
                </span>
              </p>
              <p><strong>{t('policies.enforcement')}:</strong> 
                <span style={{
                  marginLeft: '0.5rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  backgroundColor: policy.enforcementStatus === 'completed' ? '#d4edda' : 
                                   policy.enforcementStatus === 'error' ? '#f8d7da' : '#fff3cd',
                  color: policy.enforcementStatus === 'completed' ? '#155724' : 
                         policy.enforcementStatus === 'error' ? '#721c24' : '#856404'
                }}>
                  {policy.enforcementStatus}
                </span>
              </p>
              {policy.appliedAt && (
                <p><strong>{t('policies.appliedAt')}:</strong> {new Date(policy.appliedAt).toLocaleString()}</p>
              )}
            </div>
            {policy.msplXml && (
              <details>
                <summary style={{ cursor: 'pointer', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                  {t('policies.viewXml')}
                </summary>
                <MSPLViewer msplXml={policy.msplXml} />
              </details>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

