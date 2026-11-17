import { Fragment, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EnforcementExecutionLog } from '../../../core/ports';
import * as s from './styles';

interface LogFilters {
  from: string;
  to: string;
  result: string;
  deviceId: string;
  isTest: string;
  profileId: string;
  limit: string;
}

interface Props {
  executions: EnforcementExecutionLog[];
  logFilters: LogFilters;
  setLogFilters: React.Dispatch<React.SetStateAction<LogFilters>>;
  isMobile: boolean;
  onRefresh: () => void;
  loading?: boolean;
}

const RESULT_BADGE_MAP: Record<string, React.CSSProperties> = {
  completed: { padding: '0.25rem 0.5rem', borderRadius: '4px', backgroundColor: '#d4edda', color: '#155724', fontSize: '0.75rem', fontWeight: 500 },
  error: { padding: '0.25rem 0.5rem', borderRadius: '4px', backgroundColor: '#f8d7da', color: '#721c24', fontSize: '0.75rem', fontWeight: 500 },
  failed: { padding: '0.25rem 0.5rem', borderRadius: '4px', backgroundColor: '#f8d7da', color: '#721c24', fontSize: '0.75rem', fontWeight: 500 },
  pending: { padding: '0.25rem 0.5rem', borderRadius: '4px', backgroundColor: '#fff3cd', color: '#856404', fontSize: '0.75rem', fontWeight: 500 },
  skipped: { padding: '0.25rem 0.5rem', borderRadius: '4px', backgroundColor: '#e9ecef', color: '#6c757d', fontSize: '0.75rem', fontWeight: 500 },
};

const defaultBadge: React.CSSProperties = { padding: '0.25rem 0.5rem', borderRadius: '4px', backgroundColor: '#e9ecef', color: '#6c757d', fontSize: '0.75rem', fontWeight: 500 };

export default function ExecutionLogsSection({
  executions, logFilters, setLogFilters, isMobile, onRefresh, loading = false
}: Props): JSX.Element {
  const { t } = useTranslation();

  const DEFAULT_LOG_FILTERS: LogFilters = useMemo(() => ({
    from: '',
    to: '',
    result: '',
    deviceId: '',
    isTest: '',
    profileId: '',
    limit: '200'
  }), []);

  const [draftFilters, setDraftFilters] = useState<LogFilters>(logFilters);

  // Mantener el draft en sync si los filtros aplicados cambian desde fuera
  useEffect(() => {
    setDraftFilters(logFilters);
  }, [logFilters]);

  const applyFilters = () => {
    setLogFilters(draftFilters);
  };

  const resetFilters = () => {
    setDraftFilters(DEFAULT_LOG_FILTERS);
    setLogFilters(DEFAULT_LOG_FILTERS);
  };

  const formatPhase = (log: EnforcementExecutionLog): string => {
    const stepName = (log.stepName ?? '').toString().trim();
    if (stepName) return stepName;
    const policyName = (log.policyName ?? '').toString().trim();
    if (policyName) return policyName;
    const eventType = (log.eventType ?? '').toString().trim();
    if (eventType) return eventType;
    return log.runMode || '-';
  };

  const resultBadge = (result: string) => (
    <span style={RESULT_BADGE_MAP[result] ?? defaultBadge}>{result}</span>
  );

  const parseRequestPreview = (requestPreview?: string): Record<string, unknown> | null => {
    if (!requestPreview) {
      return null;
    }
    try {
      const parsed = JSON.parse(requestPreview);
      return parsed && typeof parsed === 'object' ? parsed as Record<string, unknown> : null;
    } catch {
      return null;
    }
  };

  const getGeneratedRules = (log: EnforcementExecutionLog): string[] => {
    const parsed = parseRequestPreview(log.requestPreview);
    const generatedRules = parsed?.generatedRules;
    return Array.isArray(generatedRules)
      ? generatedRules.filter((rule): rule is string => typeof rule === 'string')
      : [];
  };

  const getPreviewText = (log: EnforcementExecutionLog): string | null => {
    const parsed = parseRequestPreview(log.requestPreview);
    if (parsed) {
      return JSON.stringify(parsed, null, 2);
    }
    return log.requestPreview ?? null;
  };

  const renderLogDetails = (log: EnforcementExecutionLog) => {
    const generatedRules = getGeneratedRules(log);
    const previewText = getPreviewText(log);
    const responseExcerpt = log.responseExcerpt?.trim();
    const hasDetails = generatedRules.length > 0 || previewText || responseExcerpt;

    if (!hasDetails) {
      return null;
    }

    return (
      <details style={s.logDetails}>
        <summary style={s.logDetailsSummary}>{t('enforcementAdmin.logs.details')}</summary>
        {generatedRules.length > 0 && (
          <div style={s.logDetailsSection}>
            <div style={s.logDetailsLabel}>{t('enforcementAdmin.logs.generatedRules')}</div>
            <pre style={s.logCodeBlock}>{generatedRules.join('\n')}</pre>
          </div>
        )}
        {previewText && (
          <div style={s.logDetailsSection}>
            <div style={s.logDetailsLabel}>{t('enforcementAdmin.logs.requestPreview')}</div>
            <pre style={s.logCodeBlock}>{previewText}</pre>
          </div>
        )}
        {responseExcerpt && (
          <div style={s.logDetailsSection}>
            <div style={s.logDetailsLabel}>{t('enforcementAdmin.logs.responseExcerpt')}</div>
            <pre style={s.logCodeBlock}>{responseExcerpt}</pre>
          </div>
        )}
      </details>
    );
  };

  return (
    <div style={s.card}>
      <h2 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.25rem' }}>
        {t('enforcementAdmin.logs.title')}
      </h2>

      <div style={{ ...s.formGrid, gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.logs.from')}</div>
          <input style={s.input} placeholder={t('enforcementAdmin.logs.from')} value={draftFilters.from} onChange={e => setDraftFilters(prev => ({ ...prev, from: e.target.value }))} />
        </div>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.logs.to')}</div>
          <input style={s.input} placeholder={t('enforcementAdmin.logs.to')} value={draftFilters.to} onChange={e => setDraftFilters(prev => ({ ...prev, to: e.target.value }))} />
        </div>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.logs.result')}</div>
          <input style={s.input} placeholder={t('enforcementAdmin.logs.result')} value={draftFilters.result} onChange={e => setDraftFilters(prev => ({ ...prev, result: e.target.value }))} />
        </div>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.logs.deviceId')}</div>
          <input style={s.input} placeholder={t('enforcementAdmin.logs.deviceId')} value={draftFilters.deviceId} onChange={e => setDraftFilters(prev => ({ ...prev, deviceId: e.target.value }))} />
        </div>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.logs.isTest')}</div>
          <select style={s.select} value={draftFilters.isTest} onChange={e => setDraftFilters(prev => ({ ...prev, isTest: e.target.value }))}>
            <option value="">{t('enforcementAdmin.logs.isTestAny')}</option>
            <option value="true">true</option>
            <option value="false">false</option>
          </select>
        </div>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.logs.profileId')}</div>
          <input style={s.input} placeholder={t('enforcementAdmin.logs.profileId')} value={draftFilters.profileId} onChange={e => setDraftFilters(prev => ({ ...prev, profileId: e.target.value }))} />
        </div>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.logs.limit')}</div>
          <input style={s.input} placeholder={t('enforcementAdmin.logs.limit')} value={draftFilters.limit} onChange={e => setDraftFilters(prev => ({ ...prev, limit: e.target.value }))} />
        </div>
      </div>

      <div style={s.buttonRow}>
        <button style={s.btnPrimary} onClick={applyFilters} disabled={loading}>
          {t('common.apply', { defaultValue: 'Apply' })}
        </button>
        <button style={s.btnSecondary} onClick={resetFilters} disabled={loading}>
          {t('common.reset', { defaultValue: 'Reset' })}
        </button>
        <button style={s.btnPrimary} onClick={onRefresh} disabled={loading}>
          {t('enforcementAdmin.logs.refresh')}
        </button>
        {loading && (
          <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>
            {t('common.loading', { defaultValue: 'Loading…' })}
          </span>
        )}
      </div>

      {executions.length === 0 ? (
        <p style={{ color: '#6c757d', marginTop: '1rem' }}>{t('enforcementAdmin.logs.noLogs')}</p>
      ) : isMobile ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
          {executions.map(log => (
            <div key={log.id} style={s.mobileCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.8rem', color: '#6c757d' }}>#{log.id}</span>
                {resultBadge(log.result)}
              </div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.logs.phase')}:</strong> {formatPhase(log)}</div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.logs.runMode')}:</strong> {log.runMode}</div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.logs.profile')}:</strong> {log.profileId ?? '-'}</div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.logs.device')}:</strong> {log.deviceId ?? '-'}</div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.logs.httpStatus')}:</strong> {log.responseStatus ?? '-'}</div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.logs.when')}:</strong> {log.executedAt ?? '-'}</div>
              {log.errorMessage && (
                <div style={{ ...s.mobileCardField, color: '#dc3545' }}>
                  <strong>{t('enforcementAdmin.logs.error')}:</strong> {log.errorMessage}
                </div>
              )}
              {renderLogDetails(log)}
            </div>
          ))}
        </div>
      ) : (
        <div style={{ ...s.tableWrapper, marginTop: '1rem' }}>
          <table style={{ ...s.table, minWidth: '900px' }}>
            <thead>
              <tr style={s.thead}>
                <th style={s.th}>{t('enforcementAdmin.logs.id')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.phase')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.result')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.runMode')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.profile')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.device')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.httpStatus')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.when')}</th>
                <th style={s.th}>{t('enforcementAdmin.logs.error')}</th>
              </tr>
            </thead>
            <tbody>
              {executions.map(log => {
                const details = renderLogDetails(log);
                return (
                <Fragment key={log.id}>
                  <tr key={log.id} style={s.tr}>
                    <td style={s.td}>{log.id}</td>
                    <td style={s.td}>{formatPhase(log)}</td>
                    <td style={s.td}>{resultBadge(log.result)}</td>
                    <td style={s.td}>{log.runMode}</td>
                    <td style={s.td}>{log.profileId ?? '-'}</td>
                    <td style={s.td}>{log.deviceId ?? '-'}</td>
                    <td style={s.td}>{log.responseStatus ?? '-'}</td>
                    <td style={s.td}>{log.executedAt ?? '-'}</td>
                    <td style={{ ...s.td, color: log.errorMessage ? '#dc3545' : undefined, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {log.errorMessage ?? '-'}
                    </td>
                  </tr>
                  {details && (
                    <tr style={s.tr}>
                      <td style={{ ...s.td, paddingTop: 0 }} colSpan={9}>
                        {details}
                      </td>
                    </tr>
                  )}
                </Fragment>
              )})}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
