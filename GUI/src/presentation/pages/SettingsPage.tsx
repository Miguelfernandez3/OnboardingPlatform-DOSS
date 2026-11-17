import { type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import LoadingSpinner from '../components/common/LoadingSpinner';
import LanguageSelector from '../components/common/LanguageSelector';
import { useIsMobile, useNotificationSettings } from '../hooks';
import { useToast } from '../../infrastructure/notifications/useToast';
import type { TelegramLinkTokenResponse } from '../../core/ports';

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { showTranslated } = useToast();
  const {
    settings,
    isLoading,
    isError,
    error,
    putSettingsMutation,
    createTelegramLinkMutation,
    unlinkTelegramMutation
  } = useNotificationSettings();

  const saveNotificationToggles = (
    patch: Partial<{ telegramEnabled: boolean; inAppNotificationsEnabled: boolean }>
  ): void => {
    if (!settings) return;
    putSettingsMutation.mutate(
      {
        telegramEnabled: patch.telegramEnabled ?? settings.telegramEnabled,
        inAppNotificationsEnabled: patch.inAppNotificationsEnabled ?? settings.inAppNotificationsEnabled
      },
      {
        onSuccess: () => showTranslated('notifications.settingsSaved', 'success'),
        onError: () => showTranslated('notifications.settingsError', 'error')
      }
    );
  };

  const connectTelegram = (): void => {
    createTelegramLinkMutation.mutate(undefined, {
      onSuccess: (res: TelegramLinkTokenResponse) => {
        window.open(res.startUrl, '_blank', 'noopener,noreferrer');
        showTranslated('notifications.telegramLinkOpened', 'success');
      },
      onError: () => showTranslated('notifications.telegramLinkError', 'error')
    });
  };

  const unlinkTelegram = (): void => {
    unlinkTelegramMutation.mutate(undefined, {
      onSuccess: () => showTranslated('notifications.telegramUnlinked', 'success'),
      onError: () => showTranslated('notifications.telegramUnlinkError', 'error')
    });
  };

  const cardStyle: CSSProperties = {
    maxWidth: 560,
    padding: isMobile ? '1.25rem' : '1.5rem 1.75rem',
    borderRadius: 12,
    border: '1px solid #e9ecef',
    backgroundColor: '#ffffff',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
  };

  if (isError && !settings) {
    return (
      <div style={{ padding: isMobile ? '1rem' : '2rem', maxWidth: 720 }}>
        <h1 style={{ fontSize: isMobile ? '1.5rem' : '1.85rem', margin: '0 0 0.35rem', color: '#212529' }}>
          {t('settings.title')}
        </h1>
        <section style={{ ...cardStyle, marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.05rem', margin: '0 0 0.5rem', color: '#343a40' }}>{t('settings.languageSection')}</h2>
          <p style={{ margin: '0 0 1rem', fontSize: '0.875rem', color: '#868e96' }}>{t('settings.languageHint')}</p>
          <LanguageSelector variant="light" />
        </section>
        <div style={{ padding: '2rem', color: '#721c24' }}>
          <strong>{t('common.error')}:</strong> {(error as Error)?.message ?? String(error)}
        </div>
      </div>
    );
  }

  const rowStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.75rem',
    padding: '0.65rem 0',
    borderBottom: '1px solid #f1f3f5',
    lineHeight: 1.45
  };

  const btnPrimary: CSSProperties = {
    padding: '0.55rem 1.1rem',
    backgroundColor: '#198754',
    color: 'white',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '0.9rem'
  };

  const btnDanger: CSSProperties = {
    ...btnPrimary,
    backgroundColor: '#dc3545'
  };

  const savingToggles = putSettingsMutation.isPending;

  return (
    <div style={{ padding: isMobile ? '1rem' : '2rem', maxWidth: 720 }}>
      <h1 style={{ fontSize: isMobile ? '1.5rem' : '1.85rem', margin: '0 0 0.35rem', color: '#212529' }}>
        {t('settings.title')}
      </h1>
      <p style={{ margin: '0 0 1.5rem', color: '#6c757d', fontSize: '0.95rem' }}>
        {t('settings.subtitle')}
      </p>

      <section style={{ ...cardStyle, marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.05rem', margin: '0 0 0.25rem', color: '#343a40' }}>
          {t('settings.languageSection')}
        </h2>
        <p style={{ margin: '0 0 1rem', fontSize: '0.875rem', color: '#868e96' }}>{t('settings.languageHint')}</p>
        <LanguageSelector variant="light" />
      </section>

      {isLoading && !settings && <LoadingSpinner message={t('settings.loading')} />}

      {settings && (
        <section style={cardStyle}>
          <h2 style={{ fontSize: '1.05rem', margin: '0 0 0.25rem', color: '#343a40' }}>
            {t('settings.notificationsSection')}
          </h2>
          <p style={{ margin: '0 0 1rem', fontSize: '0.875rem', color: '#868e96' }}>
            {t('settings.notificationsHint')}
          </p>

          <label
            style={{
              ...rowStyle,
              borderBottom: 'none',
              paddingTop: 0,
              cursor: savingToggles ? 'wait' : 'pointer',
              opacity: savingToggles ? 0.7 : 1
            }}
          >
            <input
              type="checkbox"
              disabled={savingToggles}
              checked={settings.inAppNotificationsEnabled}
              onChange={e => saveNotificationToggles({ inAppNotificationsEnabled: e.target.checked })}
              style={{ marginTop: '0.2rem', width: '1.1rem', height: '1.1rem', flexShrink: 0 }}
            />
            <span style={{ fontWeight: 500, color: '#212529' }}>{t('notifications.inAppEnabled')}</span>
          </label>

          <label
            style={{ ...rowStyle, cursor: savingToggles ? 'wait' : 'pointer', opacity: savingToggles ? 0.7 : 1 }}
          >
            <input
              type="checkbox"
              disabled={savingToggles}
              checked={settings.telegramEnabled}
              onChange={e => saveNotificationToggles({ telegramEnabled: e.target.checked })}
              style={{ marginTop: '0.2rem', width: '1.1rem', height: '1.1rem', flexShrink: 0 }}
            />
            <span style={{ fontWeight: 500, color: '#212529' }}>{t('notifications.telegramEnabled')}</span>
          </label>

          <div
            style={{
              marginTop: '0.5rem',
              paddingTop: '1rem',
              borderTop: '1px solid #e9ecef'
            }}
          >
            <p style={{ fontSize: '0.875rem', color: '#495057', margin: '0 0 0.75rem' }}>
              {t('notifications.telegramStatus', {
                linked: settings.telegramLinked ? t('notifications.linked') : t('notifications.notLinked')
              })}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}>
              <button
                type="button"
                disabled={createTelegramLinkMutation.isPending}
                onClick={() => connectTelegram()}
                style={{ ...btnPrimary, opacity: createTelegramLinkMutation.isPending ? 0.7 : 1 }}
              >
                {t('notifications.connectTelegram')}
              </button>
              {settings.telegramLinked && (
                <button
                  type="button"
                  disabled={unlinkTelegramMutation.isPending}
                  onClick={() => unlinkTelegram()}
                  style={{ ...btnDanger, opacity: unlinkTelegramMutation.isPending ? 0.7 : 1 }}
                >
                  {t('notifications.unlinkTelegram')}
                </button>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
