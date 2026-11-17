import { useTranslation } from 'react-i18next';
import { EnforcementProfileData } from '../../../core/ports';
import * as s from './styles';

interface Props {
  profiles: EnforcementProfileData[];
  isMobile: boolean;
  onOpenCreateProfile: () => void;
  onToggleProfileActive: (id: string) => Promise<void>;
  onEdit: (profile: EnforcementProfileData) => void;
  onDelete: (id: string) => Promise<void>;
  onSuccess: (key: string) => void;
  onError: (err: unknown) => void;
}

export default function ProfilesSection({
  profiles, isMobile,
  onOpenCreateProfile, onToggleProfileActive,
  onEdit, onDelete, onSuccess, onError
}: Props): JSX.Element {
  const { t } = useTranslation();

  const handleToggleActive = async (id: string) => {
    try {
      await onToggleProfileActive(id);
      onSuccess(t('enforcementAdmin.profiles.updateSuccess'));
    } catch (err) {
      onError(err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('enforcementAdmin.profiles.confirmDelete', { id }))) return;
    try {
      await onDelete(id);
      onSuccess(t('enforcementAdmin.profiles.deleteSuccess'));
    } catch (err) {
      onError(err);
    }
  };

  const activeBadge = (val: boolean) => (
    <span style={val ? s.badgeActive : s.badgeInactive}>
      {val ? t('enforcementAdmin.profiles.active') : t('enforcementAdmin.profiles.inactive')}
    </span>
  );

  const yesNo = (val: boolean) => (
    <span style={val ? s.badgeSuccess : { ...s.badgeInactive, backgroundColor: '#e9ecef', color: '#6c757d' }}>
      {val ? t('enforcementAdmin.profiles.yes') : t('enforcementAdmin.profiles.no')}
    </span>
  );

  return (
    <div style={s.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem' }}>
          {t('enforcementAdmin.profiles.title')}
        </h2>
        <button style={s.btnSuccess} onClick={onOpenCreateProfile}>
          {t('enforcementAdmin.profiles.create')}
        </button>
      </div>

      {/* List of existing profiles first */}
      {profiles.length > 0 && (
        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.profiles.id')} · {t('enforcementAdmin.profiles.profileCount', { count: profiles.length })}</div>
          {isMobile ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {profiles.map(profile => (
                <div key={profile.id} style={s.mobileCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <h3 style={{ margin: 0, fontSize: '1rem' }}>{profile.name}</h3>
                    {activeBadge(profile.isActive)}
                  </div>
                  <div style={s.mobileCardField}><strong>ID:</strong> {profile.id}</div>
                  <div style={s.mobileCardField}><strong>{t('enforcementAdmin.profiles.mode')}:</strong> {profile.mode}</div>
                  <div style={s.mobileCardField}><strong>{t('enforcementAdmin.profiles.method')}:</strong> {profile.method}</div>
                  <div style={s.mobileCardField}><strong>{t('enforcementAdmin.profiles.default')}:</strong> {yesNo(profile.isDefault)}</div>
                  <div style={s.mobileCardField}><strong>{t('enforcementAdmin.profiles.autoEnforce')}:</strong> {yesNo(profile.autoEnforceOnRegistration)}</div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                    <button style={profile.isActive ? s.btnSecondary : s.btnSuccess} onClick={() => handleToggleActive(String(profile.id))}>
                      {profile.isActive ? t('enforcementAdmin.profiles.deactivate') : t('enforcementAdmin.profiles.activate')}
                    </button>
                    <button style={s.btnPrimary} onClick={() => onEdit(profile)}>{t('common.edit')}</button>
                    <button style={s.btnDanger} onClick={() => handleDelete(String(profile.id))}>{t('common.delete')}</button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={s.tableWrapper}>
              <table style={s.table}>
                <thead>
                  <tr style={s.thead}>
                    <th style={s.th}>{t('enforcementAdmin.profiles.id')}</th>
                    <th style={s.th}>{t('enforcementAdmin.profiles.name')}</th>
                    <th style={s.th}>{t('enforcementAdmin.profiles.mode')}</th>
                    <th style={s.th}>{t('enforcementAdmin.profiles.method')}</th>
                    <th style={s.th}>{t('enforcementAdmin.profiles.default')}</th>
                    <th style={s.th}>{t('common.status')}</th>
                    <th style={s.th}>{t('enforcementAdmin.profiles.autoEnforce')}</th>
                    <th style={s.th}>{t('enforcementAdmin.profiles.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {profiles.map(profile => (
                    <tr key={profile.id} style={s.tr}>
                      <td style={s.td}>{profile.id}</td>
                      <td style={s.td}>{profile.name}</td>
                      <td style={s.td}>{profile.mode}</td>
                      <td style={s.td}>{profile.method}</td>
                      <td style={s.td}>{yesNo(profile.isDefault)}</td>
                      <td style={s.td}>{activeBadge(profile.isActive)}</td>
                      <td style={s.td}>{yesNo(profile.autoEnforceOnRegistration)}</td>
                      <td style={s.td}>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <button style={profile.isActive ? s.btnSecondary : s.btnSuccess} onClick={() => handleToggleActive(String(profile.id))}>
                            {profile.isActive ? t('enforcementAdmin.profiles.deactivate') : t('enforcementAdmin.profiles.activate')}
                          </button>
                          <button style={s.btnPrimary} onClick={() => onEdit(profile)}>{t('common.edit')}</button>
                          <button style={s.btnDanger} onClick={() => handleDelete(String(profile.id))}>{t('common.delete')}</button>
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

      {profiles.length === 0 && (
        <p style={{ color: '#6c757d', marginBottom: '1.25rem' }}>{t('enforcementAdmin.profiles.noProfiles')}</p>
      )}

    </div>
  );
}
