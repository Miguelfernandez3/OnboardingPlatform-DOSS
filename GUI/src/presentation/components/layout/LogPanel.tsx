import { useEffect, useRef, useState } from 'react';
import type React from 'react';
import { useTranslation } from 'react-i18next';
import { useServiceLogs } from '../../hooks/useServiceLogs';
import { useIsMobile } from '../../hooks';

// Selector estático: los servicios que expone el backend (mapa en api/service_logs.py).
const SERVICES = ['domain-manager', 'fdo', 'mud-manager', 'threat-mud-manager'] as const;

interface Props {
  open: boolean;
  onClose: () => void;
}

function levelColor(level: string | null): React.CSSProperties {
  switch ((level || '').toUpperCase()) {
    case 'ERROR':
    case 'CRITICAL':
      return { color: '#ff6b6b' };
    case 'WARNING':
      return { color: '#ffd166' };
    case 'INFO':
      return { color: '#8bd3ff' };
    default:
      return { color: '#adb5bd' };
  }
}

export default function LogPanel({ open, onClose }: Props): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [service, setService] = useState<string>(SERVICES[0]);
  const { logs, loading, error } = useServiceLogs(service, open);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll al final en cada refresh.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  const width = isMobile ? '100vw' : '480px';

  const styles = `
    .log-panel-tab:hover { background-color: #23272b; }
    .log-panel-service.active { background-color: #ffc107; color: #212529; }
    .log-panel-service:not(.active):hover { background-color: #495057; }
  `;

  return (
    <>
      <style>{styles}</style>
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          height: '100vh',
          width,
          maxWidth: '100vw',
          backgroundColor: '#1e2227',
          color: '#e9ecef',
          boxShadow: open ? '2px 0 12px rgba(0,0,0,0.4)' : 'none',
          transform: open ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.2s ease',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
        }}
      >
        {/* Cabecera */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0.75rem 1rem', backgroundColor: '#343a40', borderBottom: '1px solid #495057',
        }}>
          <strong style={{ fontSize: '0.95rem' }}>{t('serviceLogs.title')}</strong>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {logs?.available && (
              <span style={{ fontSize: '0.7rem', color: '#40c057', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#40c057', display: 'inline-block' }} />
                {t('serviceLogs.live')}
              </span>
            )}
            <button
              onClick={onClose}
              aria-label={t('serviceLogs.close')}
              style={{ background: 'transparent', border: 'none', color: '#adb5bd', fontSize: '1.3rem', cursor: 'pointer', lineHeight: 1 }}
            >
              ×
            </button>
          </span>
        </div>

        {/* Selector de servicios */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', padding: '0.6rem 0.75rem', backgroundColor: '#23272b', borderBottom: '1px solid #343a40' }}>
          {SERVICES.map(s => (
            <button
              key={s}
              className={`log-panel-service${s === service ? ' active' : ''}`}
              onClick={() => setService(s)}
              style={{
                border: 'none', borderRadius: '999px', padding: '0.25rem 0.7rem',
                fontSize: '0.75rem', cursor: 'pointer', backgroundColor: '#343a40', color: '#e9ecef',
              }}
            >
              {t(`serviceLogs.services.${s}`, s)}
            </button>
          ))}
        </div>

        {/* Cuerpo */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '0.5rem 0.75rem', fontSize: '0.78rem', lineHeight: 1.5 }}>
          {error && <div style={{ color: '#ff6b6b' }}>{error}</div>}
          {!error && loading && !logs && <div style={{ color: '#adb5bd' }}>{t('serviceLogs.loading')}</div>}
          {!error && logs && !logs.available && <div style={{ color: '#ffd166' }}>{t('serviceLogs.unavailable')}</div>}
          {!error && logs?.available && logs.lines.length === 0 && (
            <div style={{ color: '#adb5bd' }}>{t('serviceLogs.empty')}</div>
          )}
          {logs?.available && logs.lines.map((line, i) => (
            <div key={i} style={{ display: 'flex', gap: '0.5rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {line.ts && <span style={{ color: '#6c757d', flexShrink: 0 }}>{line.ts.slice(11, 19)}</span>}
              {line.level && <span style={{ ...levelColor(line.level), flexShrink: 0, fontWeight: 600 }}>{line.level}</span>}
              <span style={levelColor(line.level)}>{line.message}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
