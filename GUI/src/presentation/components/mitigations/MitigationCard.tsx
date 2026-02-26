import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Mitigation } from '../../../core/domain/entities/Mitigation';
import JsonViewer from '../common/JsonViewer';
import { useToast } from '../../../infrastructure/notifications/useToast';

interface MitigationCardProps {
  mitigation: Mitigation;
  onEnforce: () => Promise<void>;
  onRevoke: () => Promise<void>;
}

/**
 * MitigationCard - Tarjeta expandible con detalles de mitigation
 */
export default function MitigationCard({ mitigation, onEnforce, onRevoke }: MitigationCardProps): JSX.Element {
  const { t } = useTranslation();
  const { showApiError } = useToast();
  const [expanded, setExpanded] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const isJSON = (str: string): boolean => {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  };

  const isXML = (str: string): boolean => {
    return str.trim().startsWith('<');
  };

  const handleAction = async (action: () => Promise<void>): Promise<void> => {
    try {
      setActionLoading(true);
      await action();
    } catch (err) {
      showApiError(err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{
      border: '1px solid #dee2e6',
      borderRadius: '8px',
      padding: '1rem',
      backgroundColor: '#fff'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>{mitigation.name}</h3>
          {mitigation.description && (
            <p style={{ margin: 0, color: '#6c757d', fontSize: '0.875rem' }}>
              {mitigation.description}
            </p>
          )}
          <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              backgroundColor: mitigation.is_enforced ? '#d4edda' : '#e2e3e5',
              color: mitigation.is_enforced ? '#155724' : '#383d41',
              fontSize: '0.875rem',
              fontWeight: 'bold'
            }}>
              {mitigation.is_enforced ? t('device.mitigations.enforced') : t('device.mitigations.notEnforced')}
            </span>
            {mitigation.last_enforced && (
              <span style={{ fontSize: '0.875rem', color: '#6c757d' }}>
                {t('device.mitigations.lastEnforced')}: {formatDate(mitigation.last_enforced)}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {mitigation.is_enforced ? (
            <button
              onClick={() => handleAction(onRevoke)}
              disabled={actionLoading}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.875rem',
                opacity: actionLoading ? 0.6 : 1
              }}
            >
              {actionLoading ? t('common.loading') : t('device.mitigations.revoke')}
            </button>
          ) : (
            <button
              onClick={() => handleAction(onEnforce)}
              disabled={actionLoading}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.875rem',
                opacity: actionLoading ? 0.6 : 1
              }}
            >
              {actionLoading ? t('common.loading') : t('device.mitigations.enforce')}
            </button>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            {expanded ? t('device.mitigations.hideDetails') : t('device.mitigations.showDetails')}
          </button>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid #dee2e6' }}>
          <h4 style={{ marginBottom: '1rem' }}>{t('device.mitigations.actions')}</h4>
          {mitigation.mitigation_actions && (
            <div>
              {isJSON(mitigation.mitigation_actions) ? (
                <JsonViewer 
                  data={JSON.parse(mitigation.mitigation_actions)} 
                  title={t('device.mitigations.mitigationActions')}
                />
              ) : isXML(mitigation.mitigation_actions) ? (
                <div>
                  <h4 style={{ marginBottom: '1rem' }}>{t('device.mitigations.mitigationActions')}</h4>
                  <SyntaxHighlighter 
                    language="xml" 
                    style={oneDark} 
                    wrapLines={true}
                    customStyle={{
                      borderRadius: '6px',
                      padding: '1rem',
                      fontSize: '14px'
                    }}
                  >
                    {mitigation.mitigation_actions}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <div>
                  <h4 style={{ marginBottom: '1rem' }}>{t('device.mitigations.mitigationActions')}</h4>
                  <pre style={{
                    padding: '1rem',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '4px',
                    overflow: 'auto',
                    fontSize: '0.875rem'
                  }}>
                    {mitigation.mitigation_actions}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
