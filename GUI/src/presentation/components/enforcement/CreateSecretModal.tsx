import { useTranslation } from 'react-i18next';
import * as s from './styles';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  secretName: string;
  setSecretName: (v: string) => void;
  secretValue: string;
  setSecretValue: (v: string) => void;
  onCreate: () => Promise<void>;
  onValidationError: (msg: string) => void;
  onSuccess?: (msg: string) => void;
}

export default function CreateSecretModal({
  isOpen,
  onClose,
  secretName,
  setSecretName,
  secretValue,
  setSecretValue,
  onCreate,
  onValidationError,
  onSuccess
}: Props): JSX.Element | null {
  const { t } = useTranslation();

  const handleCreate = async () => {
    if (!secretName.trim() || !secretValue) {
      onValidationError(t('enforcementAdmin.secrets.nameRequired'));
      return;
    }
    try {
      await onCreate();
      onSuccess?.(t('enforcementAdmin.secrets.createSuccess'));
      onClose();
    } catch {
      // Error handled by parent
    }
  };

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
        padding: '1rem',
      }}
      onMouseDown={onClose}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '1.25rem',
          width: '50%',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: '#495057' }}>
          {t('enforcementAdmin.secrets.addSecret')}
        </h3>

        <div style={s.formSection}>
          <div style={s.formLabel}>{t('enforcementAdmin.secrets.name')}</div>
          <input
            style={s.input}
            placeholder={t('enforcementAdmin.secrets.namePlaceholder')}
            value={secretName}
            onChange={e => setSecretName(e.target.value)}
          />
        </div>
        <div style={s.formSection}>
          <div style={s.formLabel}>{t('enforcementAdmin.secrets.value')}</div>
          <input
            style={s.input}
            type="password"
            placeholder={t('enforcementAdmin.secrets.valuePlaceholder')}
            value={secretValue}
            onChange={e => setSecretValue(e.target.value)}
          />
        </div>

        <div style={s.buttonRow}>
          <button style={s.btnSuccess} onClick={handleCreate}>
            {t('enforcementAdmin.secrets.create')}
          </button>
          <button style={s.btnSecondary} type="button" onClick={onClose}>
            {t('common.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
