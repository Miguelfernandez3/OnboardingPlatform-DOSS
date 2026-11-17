import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Policy } from '../../../core/domain/entities/Policy';
import { useIsMobile } from '../../hooks';
import MSPLViewer from '../mspl/MSPLViewer';

interface PolicyListProps {
  policies: Policy[];
  onCreateNew?: () => void;
  onEnforcePolicy?: (policyId: string) => Promise<void>;
}

/**
 * PolicyList - Componente para listar políticas aplicadas
 */
export default function PolicyList({ policies, onCreateNew, onEnforcePolicy }: PolicyListProps): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [runningPolicyId, setRunningPolicyId] = useState<string | null>(null);
  const [confirmPolicyId, setConfirmPolicyId] = useState<string | null>(null);

  const translateStatus = (status?: string | null): string => {
    if (!status) return '-';
    return t(`policies.statusLabels.${status}`, status);
  };

  const translateEnforcementStatus = (status?: string | null): string => {
    if (!status) return '-';
    return t(`policies.enforcementStatusLabels.${status}`, status);
  };

  const runEnforce = async (policyId: string): Promise<void> => {
    if (!onEnforcePolicy) return;
    setRunningPolicyId(policyId);
    try {
      await onEnforcePolicy(policyId);
    } catch (_err) {
      // Parent component handles user feedback.
    } finally {
      setRunningPolicyId(null);
    }
  };

  const handleEnforce = (policyId: string, isReEnforce: boolean): void => {
    if (isReEnforce) {
      setConfirmPolicyId(policyId);
    } else {
      void runEnforce(policyId);
    }
  };

  return (
    <div>
      <div style={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        justifyContent: 'space-between',
        alignItems: isMobile ? 'stretch' : 'center',
        gap: isMobile ? '1rem' : '0',
        marginBottom: isMobile ? '1rem' : '1.5rem'
      }}>
        <h2 style={{ margin: 0, fontSize: isMobile ? '1.25rem' : '1.5rem' }}>{t('policies.title')}</h2>
        {onCreateNew && (
          <button
            onClick={onCreateNew}
            style={{
              padding: isMobile ? '0.75rem 1rem' : '0.75rem 1.5rem',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
          >
            <span>+</span>
            {t('policies.createNew')}
          </button>
        )}
      </div>

      {!policies || policies.length === 0 ? (
        <div style={{
          padding: isMobile ? '2rem 1rem' : '3rem',
          textAlign: 'center',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}>
          <p style={{ marginBottom: '1rem', fontSize: isMobile ? '1rem' : '1.1rem' }}>{t('policies.noPolicies')}</p>
          {onCreateNew && (
            <button
              onClick={onCreateNew}
              style={{
                width: isMobile ? '100%' : 'auto',
                padding: '0.75rem 1.5rem',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: 'bold'
              }}
            >
              {t('policies.createNew')}
            </button>
          )}
        </div>
      ) : (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: isMobile ? '1rem' : '1.25rem'
        }}>
          {policies.map((policy) => {
            const isSuperseded = policy.status === 'superseded' || policy.enforcementStatus === 'superseded';
            const statusColor =
              isSuperseded
                ? { bg: '#e9ecef', fg: '#495057' }
                : policy.status === 'active'
                ? { bg: '#d4edda', fg: '#155724' }
                : policy.status === 'failed'
                  ? { bg: '#f8d7da', fg: '#721c24' }
                  : { bg: '#fff3cd', fg: '#856404' };

            const enforcementColor =
              isSuperseded
                ? { bg: '#e9ecef', fg: '#495057' }
                : policy.enforcementStatus === 'completed'
                ? { bg: '#d4edda', fg: '#155724' }
                : policy.enforcementStatus === 'error' || policy.enforcementStatus === 'failed'
                  ? { bg: '#f8d7da', fg: '#721c24' }
                  : policy.enforcementStatus === 'deferred'
                    ? { bg: '#cce5ff', fg: '#004085' }
                    : { bg: '#fff3cd', fg: '#856404' };

            const firstMissing = policy.enforcementBlockers?.missing?.[0] as
              | { label?: string; key?: string }
              | undefined;
            const missingHint = firstMissing
              ? String(firstMissing.label || firstMissing.key || '')
              : '';

            return (
              <div
                key={policy.id}
                style={{
                  border: '1px solid #dee2e6',
                  borderRadius: '8px',
                  padding: isMobile ? '0.75rem 0.75rem 0.5rem' : '0.85rem 1.25rem 0.75rem',
                  backgroundColor: '#ffffff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
                }}
              >
                {isMobile ? (
                  <>
                    {/* Versión móvil (similar a antes, más compacta) */}
                    <div style={{ marginBottom: '0.5rem' }}>
                      <h3
                        style={{
                          margin: 0,
                          fontSize: '1rem',
                          fontWeight: 600
                        }}
                      >
                        {policy.name || `${t('policies.id')} ${policy.id}`}
                      </h3>
                      <div style={{ fontSize: '0.8rem', color: '#6c757d', marginTop: '0.25rem' }}>
                        <strong>{t('policies.id')}:</strong> {policy.id}
                      </div>
                    </div>
                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '0.35rem',
                        marginBottom: '0.5rem'
                      }}
                    >
                      <span
                        style={{
                          padding: '0.15rem 0.45rem',
                          borderRadius: '999px',
                          fontSize: '0.75rem',
                          backgroundColor: statusColor.bg,
                          color: statusColor.fg,
                          fontWeight: 500
                        }}
                      >
                        {t('policies.status')}: {translateStatus(policy.status)}
                      </span>
                      <span
                        style={{
                          padding: '0.15rem 0.45rem',
                          borderRadius: '999px',
                          fontSize: '0.75rem',
                          backgroundColor: enforcementColor.bg,
                          color: enforcementColor.fg,
                          fontWeight: 500
                        }}
                      >
                        {t('policies.enforcement')}: {translateEnforcementStatus(policy.enforcementStatus)}
                      </span>
                      {policy.policyType && (
                        <span
                          style={{
                            padding: '0.15rem 0.45rem',
                            borderRadius: '999px',
                            fontSize: '0.75rem',
                            backgroundColor: '#e2e3e5',
                            color: '#495057'
                          }}
                        >
                          {t('policies.policyType')}: {policy.policyType}
                        </span>
                      )}
                      {policy.source && (
                        <span
                          style={{
                            padding: '0.15rem 0.45rem',
                            borderRadius: '999px',
                            fontSize: '0.75rem',
                            backgroundColor: '#e7f1ff',
                            color: '#0b5ed7'
                          }}
                        >
                          {t('policies.source')}: {policy.source}
                        </span>
                      )}
                    </div>

                    {policy.enforcementStatus === 'deferred' && missingHint && (
                      <div style={{ fontSize: '0.75rem', color: '#004085', marginBottom: '0.35rem' }}>
                        {t('policies.missingContext')}: {missingHint}
                      </div>
                    )}

                    {onEnforcePolicy && policy.canEnforce !== false && !isSuperseded && (
                      <div style={{ marginBottom: policy.msplXml ? '0.5rem' : 0 }}>
                        <button
                          onClick={() => handleEnforce(policy.id, policy.enforcementStatus === 'completed')}
                          disabled={runningPolicyId === policy.id}
                          style={{
                            padding: '0.45rem 0.9rem',
                            backgroundColor: policy.enforcementStatus === 'completed' ? '#20c997' : '#28a745',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: runningPolicyId === policy.id ? 'not-allowed' : 'pointer',
                            opacity: runningPolicyId === policy.id ? 0.7 : 1,
                            fontWeight: 600,
                            fontSize: '0.9rem',
                            width: '100%'
                          }}
                        >
                            {runningPolicyId === policy.id
                              ? t('policies.enforcing')
                              : policy.enforcementStatus === 'completed'
                                ? t('policies.enforceAgain')
                                : t('policies.enforce')}
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    {/* Versión desktop: grid horizontal que aprovecha el espacio */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'minmax(220px, 2fr) minmax(140px, 1fr) minmax(170px, 1.2fr) minmax(160px, 1.2fr) auto',
                        columnGap: '1rem',
                        rowGap: '0.25rem',
                        alignItems: 'center'
                      }}
                    >
                      {/* Columna 1: título + ID */}
                      <div style={{ minWidth: 0 }}>
                        <h3
                          style={{
                            margin: 0,
                            fontSize: '1.05rem',
                            fontWeight: 600,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}
                          title={policy.name || `${t('policies.id')} ${policy.id}`}
                        >
                          {policy.name || `${t('policies.id')} ${policy.id}`}
                        </h3>
                        <div
                          style={{
                            fontSize: '0.8rem',
                            color: '#6c757d',
                            marginTop: '0.15rem'
                          }}
                        >
                          <strong>{t('policies.id')}:</strong> {policy.id}
                        </div>
                      </div>

                      {/* Columna 2: status */}
                      <div
                        style={{
                          fontSize: '0.85rem',
                          display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center'
                        }}
                      >
                        <span
                          style={{
                            padding: '0.18rem 0.55rem',
                            borderRadius: '999px',
                            backgroundColor: statusColor.bg,
                            color: statusColor.fg,
                            fontWeight: 500
                          }}
                        >
                          {t('policies.status')}: {translateStatus(policy.status)}
                        </span>
                      </div>

                      {/* Columna 3: enforcement */}
                      <div
                        style={{
                          fontSize: '0.85rem',
                          display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center'
                        }}
                      >
                        <span
                          style={{
                            padding: '0.18rem 0.55rem',
                            borderRadius: '999px',
                            backgroundColor: enforcementColor.bg,
                            color: enforcementColor.fg,
                            fontWeight: 500
                          }}
                        >
                          {t('policies.enforcement')}: {translateEnforcementStatus(policy.enforcementStatus)}
                        </span>
                      </div>

                      {/* Columna 4: tipo/origen/fecha comprimidos */}
                      <div
                        style={{
                          fontSize: '0.8rem',
                          color: '#495057',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.15rem',
                          justifyContent: 'center'
                        }}
                      >
                        {policy.policyType && (
                          <span>
                            <strong>{t('policies.policyType')}:</strong> {policy.policyType}
                          </span>
                        )}
                        {policy.source && (
                          <span>
                            <strong>{t('policies.source')}:</strong> {policy.source}
                          </span>
                        )}
                        {policy.enforcementStatus === 'deferred' && missingHint && (
                          <span style={{ color: '#004085' }}>
                            <strong>{t('policies.missingContext')}:</strong> {missingHint}
                          </span>
                        )}
                        {policy.appliedAt && (
                          <span>
                            <strong>{t('policies.appliedAt')}:</strong>{' '}
                            {new Date(policy.appliedAt).toLocaleString()}
                          </span>
                        )}
                      </div>

                      {/* Columna 5: botón alineado a la derecha */}
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'center',
                          alignItems: 'center'
                        }}
                      >
                        {onEnforcePolicy && policy.canEnforce !== false && !isSuperseded && (
                          <button
                            onClick={() => handleEnforce(policy.id, policy.enforcementStatus === 'completed')}
                            disabled={runningPolicyId === policy.id}
                            style={{
                              padding: '0.45rem 1.2rem',
                              backgroundColor: policy.enforcementStatus === 'completed' ? '#20c997' : '#28a745',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: runningPolicyId === policy.id ? 'not-allowed' : 'pointer',
                              opacity: runningPolicyId === policy.id ? 0.7 : 1,
                              fontWeight: 600,
                              fontSize: '0.9rem',
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {runningPolicyId === policy.id
                              ? t('policies.enforcing')
                              : policy.enforcementStatus === 'completed'
                                ? t('policies.enforceAgain')
                                : t('policies.enforce')}
                          </button>
                        )}
                      </div>
                    </div>
                  </>
                )}

                {/* XML colapsable, debajo ocupando todo el ancho */}
                {policy.msplXml && (
                  <details style={{ marginTop: '0.4rem' }}>
                    <summary
                      style={{
                        cursor: 'pointer',
                        fontWeight: 500,
                        fontSize: '0.9rem',
                        color: '#0d6efd',
                        paddingTop: '0.1rem',
                        paddingBottom: '0.1rem'
                      }}
                    >
                      {t('policies.viewXml')}
                    </summary>
                    <div style={{ marginTop: '0.35rem' }}>
                      <MSPLViewer msplXml={policy.msplXml} />
                    </div>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modal de confirmación para re-enforce */}
      {confirmPolicyId && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              padding: '1.5rem',
              maxWidth: '420px',
              width: '90%',
              boxShadow: '0 10px 25px rgba(0,0,0,0.2)'
            }}
          >
            <h3 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '1.1rem' }}>
              {t('policies.confirmReEnforceTitle')}
            </h3>
            <p style={{ marginTop: 0, marginBottom: '1.25rem', fontSize: '0.95rem', color: '#495057' }}>
              {t('policies.confirmReEnforceMessage')}
            </p>
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '0.5rem'
              }}
            >
              <button
                onClick={() => setConfirmPolicyId(null)}
                style={{
                  padding: '0.4rem 0.9rem',
                  borderRadius: '4px',
                  border: '1px solid #ced4da',
                  backgroundColor: '#ffffff',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={() => {
                  const id = confirmPolicyId;
                  setConfirmPolicyId(null);
                  if (id) void runEnforce(id);
                }}
                style={{
                  padding: '0.4rem 0.95rem',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: '#20c997',
                  color: '#ffffff',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: 600
                }}
              >
                {t('policies.confirmReEnforceConfirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
