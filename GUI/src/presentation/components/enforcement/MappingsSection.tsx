import { useTranslation } from 'react-i18next';
import { EnforcementMappingData } from '../../../core/ports';
import * as s from './styles';

interface Props {
  mappings: EnforcementMappingData[];
  isMobile: boolean;
  onOpenCreateMapping: () => void;
  onToggleMappingActive: (id: string) => Promise<void>;
  onEdit: (mapping: EnforcementMappingData) => void;
  onDelete: (id: string) => Promise<void>;
  onSuccess: (msg: string) => void;
  onError: (err: unknown) => void;
}

export default function MappingsSection({
  mappings, isMobile,
  onOpenCreateMapping, onToggleMappingActive,
  onEdit, onDelete, onSuccess, onError
}: Props): JSX.Element {
  const { t } = useTranslation();

  const handleToggleActive = async (id: string) => {
    try {
      await onToggleMappingActive(id);
      onSuccess(t('enforcementAdmin.mappings.updateSuccess'));
    } catch (err) {
      onError(err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('enforcementAdmin.mappings.confirmDelete', { id }))) return;
    try {
      await onDelete(id);
      onSuccess(t('enforcementAdmin.mappings.deleteSuccess'));
    } catch (err) {
      onError(err);
    }
  };

  const activeBadge = (val: boolean) => (
    <span style={val ? s.badgeActive : s.badgeInactive}>
      {val ? t('enforcementAdmin.mappings.active') : t('enforcementAdmin.mappings.inactive')}
    </span>
  );

  return (
    <div style={s.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem' }}>
          {t('enforcementAdmin.mappings.title')}
        </h2>
        <button style={s.btnSuccess} onClick={onOpenCreateMapping}>
          {t('enforcementAdmin.mappings.create')}
        </button>
      </div>

      {/* List of existing mappings first */}
      {mappings.length > 0 && (
        <div style={s.formSection}>
          <div style={s.formSectionTitle}>
            {t('enforcementAdmin.mappings.id')} · {t('enforcementAdmin.mappings.mappingCount', { count: mappings.length })}
          </div>
          {isMobile ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {mappings.map(mapping => (
                <div key={mapping.id} style={s.mobileCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <strong style={{ fontSize: '0.95rem' }}>{mapping.matchKind}: {mapping.matchValue}</strong>
                    {activeBadge(mapping.isActive)}
                  </div>
                  <div style={s.mobileCardField}><strong>ID:</strong> {mapping.id}</div>
                  <div style={s.mobileCardField}><strong>{t('enforcementAdmin.mappings.profile')}:</strong> {mapping.profileId}</div>
                  <div style={s.mobileCardField}><strong>{t('enforcementAdmin.mappings.priority')}:</strong> {mapping.priority}</div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                    <button style={mapping.isActive ? s.btnSecondary : s.btnSuccess} onClick={() => handleToggleActive(String(mapping.id))}>
                      {mapping.isActive ? t('enforcementAdmin.mappings.deactivate') : t('enforcementAdmin.mappings.activate')}
                    </button>
                    <button style={s.btnPrimary} onClick={() => onEdit(mapping)}>{t('common.edit')}</button>
                    <button style={s.btnDanger} onClick={() => handleDelete(String(mapping.id))}>{t('common.delete')}</button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={s.tableWrapper}>
              <table style={s.table}>
                <thead>
                  <tr style={s.thead}>
                    <th style={s.th}>{t('enforcementAdmin.mappings.id')}</th>
                    <th style={s.th}>{t('enforcementAdmin.mappings.matchKind')}</th>
                    <th style={s.th}>{t('enforcementAdmin.mappings.matchValue')}</th>
                    <th style={s.th}>{t('enforcementAdmin.mappings.profile')}</th>
                    <th style={s.th}>{t('enforcementAdmin.mappings.priority')}</th>
                    <th style={s.th}>{t('common.status')}</th>
                    <th style={s.th}>{t('enforcementAdmin.mappings.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {mappings.map(mapping => (
                    <tr key={mapping.id} style={s.tr}>
                      <td style={s.td}>{mapping.id}</td>
                      <td style={s.td}>{mapping.matchKind}</td>
                      <td style={s.td}>{mapping.matchValue}</td>
                      <td style={s.td}>{mapping.profileId}</td>
                      <td style={s.td}>{mapping.priority}</td>
                      <td style={s.td}>{activeBadge(mapping.isActive)}</td>
                      <td style={s.td}>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <button style={mapping.isActive ? s.btnSecondary : s.btnSuccess} onClick={() => handleToggleActive(String(mapping.id))}>
                            {mapping.isActive ? t('enforcementAdmin.mappings.deactivate') : t('enforcementAdmin.mappings.activate')}
                          </button>
                          <button style={s.btnPrimary} onClick={() => onEdit(mapping)}>{t('common.edit')}</button>
                          <button style={s.btnDanger} onClick={() => handleDelete(String(mapping.id))}>{t('common.delete')}</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {mappings.length === 0 && (
        <p style={{ color: '#6c757d', marginBottom: '1.25rem' }}>{t('enforcementAdmin.mappings.noMappings')}</p>
      )}

    </div>
  );
}
