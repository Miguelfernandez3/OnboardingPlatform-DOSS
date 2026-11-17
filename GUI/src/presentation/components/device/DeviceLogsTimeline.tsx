import type React from 'react';
import { useTranslation } from 'react-i18next';
import { DeviceLogsResponse } from '../../../core/ports';

interface Props {
  timeline: DeviceLogsResponse | null;
  loading?: boolean;
  error?: string | null;
  showTitle?: boolean;
}

function formatElapsedMs(ms?: number): string {
  if (ms === undefined || ms === null || Number.isNaN(ms)) return '-';
  if (ms < 1) return '<1ms';
  if (ms < 10) return `${ms.toFixed(2)}ms`;
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const minutes = seconds / 60;
  return `${minutes.toFixed(2)}min`;
}

function resultBadgeStyle(result: string): React.CSSProperties {
  const base: React.CSSProperties = {
    padding: '0.18rem 0.55rem',
    borderRadius: '999px',
    fontWeight: 600,
    fontSize: '0.8rem',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  switch ((result || '').toLowerCase()) {
    case 'completed':
    case 'success':
      return { ...base, backgroundColor: '#d4edda', color: '#155724' };
    case 'failed':
    case 'error':
      return { ...base, backgroundColor: '#f8d7da', color: '#721c24' };
    case 'pending':
      return { ...base, backgroundColor: '#fff3cd', color: '#856404' };
    case 'skipped':
      return { ...base, backgroundColor: '#e9ecef', color: '#6c757d' };
    default:
      return { ...base, backgroundColor: '#e9ecef', color: '#6c757d' };
  }
}

export default function DeviceLogsTimeline({ timeline, loading, error, showTitle = true }: Props): JSX.Element {
  const { t } = useTranslation();
  const styles = `
    .device-logs-details > summary::-webkit-details-marker { display: none; }
    .device-logs-details > summary { list-style: none; cursor: pointer; position: relative; }
    .device-logs-summary-left { min-width: 0; }
    .device-logs-chevron {
      position: absolute;
      right: 0;
      top: 50%;
      transform: translateY(-50%);
      transition: transform 0.15s ease;
      transform-origin: center;
      color: #6c757d;
      font-weight: 900;
      font-size: 1.1rem;
      line-height: 1;
      width: 1.2rem;
      text-align: center;
      pointer-events: none;
    }
    .device-logs-details[open] > summary .device-logs-chevron { transform: translateY(-50%) rotate(90deg); }
  `;

  if (loading) {
    return (
      <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', backgroundColor: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: '8px' }}>
        {t('device.logs.loading')}
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', backgroundColor: '#f8d7da', border: '1px solid #f5c2c7', borderRadius: '8px', color: '#721c24' }}>
        <strong>{t('common.error')}:</strong> {error}
      </div>
    );
  }

  const groups = timeline?.onboardings ?? [];
  if (groups.length === 0) {
    return (
      <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', backgroundColor: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: '8px' }}>
        {t('device.logs.noLogs')}
      </div>
    );
  }

  return (
    <div style={{ marginTop: showTitle ? '1rem' : 0 }}>
      <style>{styles}</style>
      {showTitle && (
        <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1rem', fontWeight: 700 }}>
          {t('device.info.logs')}
        </h3>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {groups.map(group => {
          const correlationShort = group.correlationId.slice(0, 8);
          const total = group.totalElapsedMs;
          const isManualGroup = group.correlationId.startsWith('manual-');
          const groupTitle = isManualGroup
            ? t('device.logs.manualGroupTitle')
            : t('device.logs.groupTitle', { correlationId: correlationShort });

          return (
            <details
              key={group.correlationId}
              className="device-logs-details"
              style={{
                border: '1px solid #dee2e6',
                borderRadius: '8px',
                padding: '0.75rem 0.9rem',
                backgroundColor: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
              }}
            >
              <summary style={{ fontWeight: 700, color: '#343a40' }}>
                <div
                  className="device-logs-summary-left"
                  style={{ display: 'flex', gap: '0.75rem', alignItems: 'baseline', flexWrap: 'wrap' }}
                >
                  <span>{groupTitle}</span>
                  {total !== undefined && total !== null && (
                    <span style={{ fontSize: '0.9rem', color: '#6c757d', fontWeight: 600 }}>
                      {t('device.logs.totalElapsed', { total: formatElapsedMs(total) })}
                    </span>
                  )}
                </div>
                <span className="device-logs-chevron" aria-hidden>{'▸'}</span>
              </summary>

              <div style={{ marginTop: '0.75rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 140px 140px', gap: '0.5rem', padding: '0 0 0.5rem 0', paddingRight: '1.5rem', color: '#6c757d', fontSize: '0.85rem', fontWeight: 700 }}>
                  <div>{t('device.logs.columns.step')}</div>
                  <div>{t('device.logs.columns.elapsed')}</div>
                  <div>{t('device.logs.columns.result')}</div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {group.steps.map(step => {
                    const stepKey = step.id;
                    const stepName = step.stepName || step.policyName || t('device.logs.unknownStep');
                    const showBestCase = stepName === 'fetch_dsp' && group.bestCaseFetchDspMs !== undefined && group.bestCaseFetchDspMs !== null;
                    const hasStepDetails = Boolean(step.errorMessage || step.requestPreview || showBestCase);

                    const summaryInner = (
                      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 140px 140px', gap: '0.5rem', alignItems: 'center' }}>
                        <div style={{ fontWeight: 700, color: '#343a40', wordBreak: 'break-word' }}>
                          <span>{stepName}</span>
                          {hasStepDetails && (
                            <span style={{ marginLeft: '0.5rem', padding: '0.18rem 0.55rem', borderRadius: '999px', backgroundColor: '#e9ecef', color: '#495057', fontWeight: 700, fontSize: '0.75rem' }}>
                              {t('device.logs.showDetails')}
                            </span>
                          )}
                        </div>
                        <div style={{ fontFamily: 'monospace', color: '#343a40' }}>{formatElapsedMs(step.elapsedMs)}</div>
                        <div>
                          <span style={resultBadgeStyle(step.result)}>
                            {t(`device.logs.results.${String(step.result || '').toLowerCase()}`, { defaultValue: step.result })}
                          </span>
                        </div>
                      </div>
                    );

                    if (!hasStepDetails) {
                      return (
                        <div
                          key={stepKey}
                          style={{ border: '1px solid #e9ecef', borderRadius: '6px', padding: '0.35rem 0.5rem', backgroundColor: '#f8f9fa', position: 'relative', paddingRight: '1.5rem' }}
                        >
                          {summaryInner}
                        </div>
                      );
                    }

                    return (
                      <details
                        key={stepKey}
                        className="device-logs-details"
                        style={{ border: '1px solid #e9ecef', borderRadius: '6px', padding: '0.35rem 0.5rem', backgroundColor: '#f8f9fa', position: 'relative', paddingRight: '1.5rem' }}
                      >
                        <summary>
                          <div className="device-logs-summary-left">{summaryInner}</div>
                          <span className="device-logs-chevron" aria-hidden>{'▸'}</span>
                        </summary>

                        <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#495057' }}>
                          {showBestCase && (
                            <div style={{ marginBottom: '0.35rem' }}>
                              <strong>fetch_dsp best case:</strong>{' '}
                              <span style={{ color: '#0b5ed7', fontFamily: 'monospace' }}>
                                {formatElapsedMs(group.bestCaseFetchDspMs)}
                              </span>
                            </div>
                          )}
                          {step.errorMessage && (
                            <div style={{ marginBottom: '0.35rem' }}>
                              <strong>{t('device.logs.error')}:</strong>{' '}
                              <span style={{ color: '#721c24' }}>{step.errorMessage}</span>
                            </div>
                          )}
                          {step.requestPreview && (
                            <div style={{ wordBreak: 'break-word' }}>
                              <strong>{t('device.logs.requestPreview')}:</strong>{' '}
                              <pre style={{ margin: '0.25rem 0 0 0', padding: '0.5rem', backgroundColor: '#e9ecef', borderRadius: '6px', overflowX: 'auto' }}>
                                {step.requestPreview}
                              </pre>
                            </div>
                          )}
                        </div>
                      </details>
                    );
                  })}
                </div>
              </div>
            </details>
          );
        })}
      </div>
    </div>
  );
}

