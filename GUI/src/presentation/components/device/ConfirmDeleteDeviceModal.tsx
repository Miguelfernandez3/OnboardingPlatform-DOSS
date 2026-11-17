import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks';

export interface ConfirmDeleteDeviceModalProps {
  isOpen: boolean;
  deviceLabel: string;
  onClose: () => void;
  onConfirm: () => void;
  isLoading?: boolean;
}

/**
 * Modal de confirmación para eliminar un dispositivo (sustituye window.confirm).
 */
export default function ConfirmDeleteDeviceModal({
  isOpen,
  deviceLabel,
  onClose,
  onConfirm,
  isLoading = false,
}: ConfirmDeleteDeviceModalProps): JSX.Element | null {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: isMobile ? '1rem' : '0',
      }}
      onClick={isLoading ? undefined : onClose}
      onKeyDown={(e) => {
        if (e.key === 'Escape' && !isLoading) onClose();
      }}
      role="presentation"
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: isMobile ? '1.5rem' : '2rem',
          width: '100%',
          maxWidth: '420px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-device-modal-title"
      >
        <h2
          id="delete-device-modal-title"
          style={{ marginTop: 0, marginBottom: '1rem', fontSize: isMobile ? '1.25rem' : '1.5rem' }}
        >
          {t('device.info.deleteModalTitle')}
        </h2>

        {deviceLabel.trim() ? (
          <p style={{ marginTop: 0, marginBottom: '0.5rem', color: '#333', fontWeight: 600 }}>{deviceLabel}</p>
        ) : null}

        <p style={{ marginBottom: '1.5rem', color: '#666' }}>{t('device.info.deleteConfirm')}</p>

        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: '4px',
              border: '1px solid #dee2e6',
              backgroundColor: 'white',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
            }}
          >
            {t('common.cancel')}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: '#dc3545',
              color: 'white',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              opacity: isLoading ? 0.7 : 1,
            }}
          >
            {isLoading ? '…' : t('device.info.delete')}
          </button>
        </div>
      </div>
    </div>
  );
}
