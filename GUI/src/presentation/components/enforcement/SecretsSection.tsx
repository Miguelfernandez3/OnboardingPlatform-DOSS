import { useTranslation } from 'react-i18next';
import { EnforcementSecretMetadata } from '../../../core/ports';
import * as s from './styles';

interface Props {
  secrets: EnforcementSecretMetadata[];
  isMobile: boolean;
  onOpenCreateSecret: () => void;
  onRotate: (id: string, newValue: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onSuccess: (msg: string) => void;
  onError: (err: unknown) => void;
}

export default function SecretsSection({
  secrets, isMobile, onOpenCreateSecret,
  onRotate, onDelete, onSuccess, onError
}: Props): JSX.Element {
  const { t } = useTranslation();

  const handleRotate = async (id: string) => {
    const newValue = window.prompt(t('enforcementAdmin.secrets.rotatePrompt'));
    if (!newValue) return;
    try {
      await onRotate(id, newValue);
      onSuccess(t('enforcementAdmin.secrets.rotateSuccess'));
    } catch (err) {
      onError(err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('enforcementAdmin.secrets.confirmDelete', { id }))) return;
    try {
      await onDelete(id);
      onSuccess(t('enforcementAdmin.secrets.deleteSuccess'));
    } catch (err) {
      onError(err);
    }
  };

  return (
    <div style={s.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem' }}>
          {t('enforcementAdmin.secrets.title')}
        </h2>
        <button style={s.btnSuccess} onClick={onOpenCreateSecret}>
          {t('enforcementAdmin.secrets.addSecret')}
        </button>
      </div>

      {secrets.length === 0 ? (
        <p style={{ color: '#6c757d', marginTop: '1rem' }}>{t('enforcementAdmin.secrets.noSecrets')}</p>
      ) : isMobile ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
          {secrets.map(secret => (
            <div key={secret.id} style={s.mobileCard}>
              <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem' }}>{secret.name}</h3>
              <div style={s.mobileCardField}><strong>ID:</strong> {secret.id}</div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.secrets.keyVersion')}:</strong> {secret.keyVersion}</div>
              <div style={s.mobileCardField}><strong>{t('enforcementAdmin.secrets.updatedAt')}:</strong> {secret.updatedAt || '-'}</div>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                <button style={s.btnWarning} onClick={() => handleRotate(String(secret.id))}>{t('enforcementAdmin.secrets.rotate')}</button>
                <button style={s.btnDanger} onClick={() => handleDelete(String(secret.id))}>{t('common.delete')}</button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ ...s.tableWrapper, marginTop: '1rem' }}>
          <table style={s.table}>
            <thead>
              <tr style={s.thead}>
                <th style={s.th}>{t('enforcementAdmin.secrets.id')}</th>
                <th style={s.th}>{t('enforcementAdmin.secrets.name')}</th>
                <th style={s.th}>{t('enforcementAdmin.secrets.keyVersion')}</th>
                <th style={s.th}>{t('enforcementAdmin.secrets.updatedAt')}</th>
                <th style={s.th}>{t('enforcementAdmin.secrets.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {secrets.map(secret => (
                <tr key={secret.id} style={s.tr}>
                  <td style={s.td}>{secret.id}</td>
                  <td style={s.td}>{secret.name}</td>
                  <td style={s.td}>{secret.keyVersion}</td>
                  <td style={s.td}>{secret.updatedAt || '-'}</td>
                  <td style={s.td}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button style={s.btnWarning} onClick={() => handleRotate(String(secret.id))}>{t('enforcementAdmin.secrets.rotate')}</button>
                      <button style={s.btnDanger} onClick={() => handleDelete(String(secret.id))}>{t('common.delete')}</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
