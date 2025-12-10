import { useTranslation } from 'react-i18next';

interface EnforcementStatusProps {
  status?: string;
  message?: string;
  timestamp?: string;
}

interface StatusColors {
  bg: string;
  color: string;
  border: string;
}

/**
 * EnforcementStatus - Componente para mostrar el estado de enforcement
 */
export default function EnforcementStatus({ status, message, timestamp }: EnforcementStatusProps): JSX.Element {
  const { t } = useTranslation();

  const getStatusColor = (status?: string): StatusColors => {
    switch (status) {
      case 'completed':
        return { bg: '#d4edda', color: '#155724', border: '#c3e6cb' };
      case 'pending':
        return { bg: '#fff3cd', color: '#856404', border: '#ffeaa7' };
      case 'error':
        return { bg: '#f8d7da', color: '#721c24', border: '#f5c6cb' };
      default:
        return { bg: '#e2e3e5', color: '#383d41', border: '#d6d8db' };
    }
  };

  const statusColors = getStatusColor(status);
  const statusKey = status || 'unknown';
  const statusLabel = t(`enforcement.status.${statusKey}`) || statusKey;

  return (
    <div style={{
      padding: '1rem',
      backgroundColor: statusColors.bg,
      color: statusColors.color,
      borderRadius: '4px',
      border: `1px solid ${statusColors.border}`
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <strong>{t('enforcement.title')}:</strong>
        <span style={{
          padding: '0.25rem 0.75rem',
          borderRadius: '4px',
          backgroundColor: statusColors.color,
          color: statusColors.bg,
          fontWeight: 'bold',
          textTransform: 'uppercase',
          fontSize: '0.875rem'
        }}>
          {statusLabel}
        </span>
      </div>
      {message && (
        <p style={{ margin: '0.5rem 0' }}>{message}</p>
      )}
      {timestamp && (
        <p style={{ margin: '0.5rem 0', fontSize: '0.875rem', opacity: 0.8 }}>
          {new Date(timestamp).toLocaleString()}
        </p>
      )}
    </div>
  );
}

