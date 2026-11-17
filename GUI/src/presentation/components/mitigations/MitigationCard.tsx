import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Mitigation } from '../../../core/domain/entities/Mitigation';
import JsonViewer from '../common/JsonViewer';
import { useToast } from '../../../infrastructure/notifications/useToast';
import { getEnforcementPrerequisitesMissing, isEnforcementPrerequisitesConflict } from '../../../infrastructure/api/errors/errorUtils';

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

  const isJSON = (value: unknown): boolean => {
    if (typeof value !== 'string') {
      return false;
    }
    try {
      JSON.parse(value);
      return true;
    } catch {
      return false;
    }
  };

  const isXML = (value: unknown): boolean => {
    return typeof value === 'string' && value.trim().startsWith('<');
  };

  const mitigationActions = Array.isArray(mitigation.mitigation_actions)
    ? mitigation.mitigation_actions.filter((item): item is string => typeof item === 'string' && item.length > 0)
    : mitigation.mitigation_actions
      ? [mitigation.mitigation_actions]
      : [];

  const renderMitigationAction = (action: string, index: number): JSX.Element => {
    const title =
      mitigationActions.length > 1
        ? `${t('device.mitigations.mitigationActions')} #${index + 1}`
        : t('device.mitigations.mitigationActions');

    if (isJSON(action)) {
      return (
        <JsonViewer
          data={JSON.parse(action)}
          title={title}
        />
      );
    }

    if (isXML(action)) {
      return (
        <div>
          <h4 style={{ marginBottom: '1rem' }}>{title}</h4>
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
            {action}
          </SyntaxHighlighter>
        </div>
      );
    }

    return (
      <div>
        <h4 style={{ marginBottom: '1rem' }}>{title}</h4>
        <pre style={{
          padding: '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          overflow: 'auto',
          fontSize: '0.875rem'
        }}>
          {action}
        </pre>
      </div>
    );
  };

  const handleAction = async (action: () => Promise<void>): Promise<void> => {
    try {
      setActionLoading(true);
      await action();
    } catch (err) {
      if (isEnforcementPrerequisitesConflict(err) && getEnforcementPrerequisitesMissing(err).length > 0) {
        return;
      }
      showApiError(err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{
      border: '1px solid #dee2e6',
      borderRadius: '8px',
      padding: '0.85rem 1.1rem',
      backgroundColor: '#fff'
    }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(220px, 2fr) minmax(200px, 1.5fr) auto',
          columnGap: '1rem',
          rowGap: '0.25rem',
          alignItems: 'center'
        }}
      >
        {/* Nombre y descripción */}
        <div style={{ minWidth: 0 }}>
          <h3
            style={{
              margin: 0,
              marginBottom: '0.25rem',
              fontSize: '1rem',
              fontWeight: 600,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}
            title={mitigation.name}
          >
            {mitigation.name}
          </h3>
          {mitigation.description && (
            <p style={{ margin: 0, color: '#6c757d', fontSize: '0.85rem' }}>
              {mitigation.description}
            </p>
          )}
        </div>

        {/* Estado + última aplicación */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.2rem',
            justifyContent: 'center',
            alignItems: 'flex-start',
            fontSize: '0.85rem'
          }}
        >
          <span
            style={{
              padding: '0.18rem 0.55rem',
              borderRadius: '999px',
              backgroundColor: mitigation.is_enforced ? '#d4edda' : '#e2e3e5',
              color: mitigation.is_enforced ? '#155724' : '#383d41',
              fontWeight: 500
            }}
          >
            {mitigation.is_enforced ? t('device.mitigations.enforced') : t('device.mitigations.notEnforced')}
          </span>
          {mitigation.last_enforced && (
            <span style={{ color: '#6c757d' }}>
              <strong>{t('device.mitigations.lastEnforced')}:</strong> {formatDate(mitigation.last_enforced)}
            </span>
          )}
        </div>

        {/* Botones */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          {mitigation.is_enforced ? (
            <button
              onClick={() => handleAction(onRevoke)}
              disabled={actionLoading}
              style={{
                padding: '0.45rem 1.1rem',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
                opacity: actionLoading ? 0.6 : 1,
                whiteSpace: 'nowrap'
              }}
            >
              {actionLoading ? t('common.loading') : t('device.mitigations.revoke')}
            </button>
          ) : (
            <button
              onClick={() => handleAction(onEnforce)}
              disabled={actionLoading}
              style={{
                padding: '0.45rem 1.1rem',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
                opacity: actionLoading ? 0.6 : 1,
                whiteSpace: 'nowrap'
              }}
            >
              {actionLoading ? t('common.loading') : t('device.mitigations.enforce')}
            </button>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              padding: '0.45rem 1rem',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              whiteSpace: 'nowrap'
            }}
          >
            {expanded ? t('device.mitigations.hideDetails') : t('device.mitigations.showDetails')}
          </button>
        </div>
      </div>

      {!mitigation.is_enforced &&
        mitigation.enforcementGaps &&
        !mitigation.enforcementGaps.ready &&
        mitigation.enforcementGaps.missing.length > 0 && (
        <div
          style={{
            marginTop: '0.6rem',
            padding: '0.5rem 0.75rem',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffe69c',
            borderRadius: '6px',
            fontSize: '0.82rem',
            color: '#664d03',
            lineHeight: 1.4
          }}
        >
          <strong>{t('device.mitigations.prerequisitesBanner')}:</strong>{' '}
          {mitigation.enforcementGaps.missing
            .map((item) => {
              const o = item as { label?: string; key?: string };
              return String(o.label || o.key || '').trim();
            })
            .filter(Boolean)
            .join(', ')}
        </div>
      )}

      {expanded && (
        <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid #dee2e6' }}>
          <h4 style={{ marginBottom: '1rem' }}>{t('device.mitigations.actions')}</h4>
          {mitigationActions.length > 0 && (
            <div>
              {mitigationActions.map((action, index) => (
                <div key={`${mitigation.id}-action-${index}`} style={{ marginBottom: index < mitigationActions.length - 1 ? '1.25rem' : 0 }}>
                  {renderMitigationAction(action, index)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
