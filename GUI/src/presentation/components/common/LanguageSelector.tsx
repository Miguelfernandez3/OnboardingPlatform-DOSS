import { useState, type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { userSettingsService } from '../../../infrastructure/services/userSettingsService';
import { useToast } from '../../../infrastructure/notifications/useToast';

export type LanguageSelectorVariant = 'navbar' | 'light';

interface LanguageSelectorProps {
  /** `navbar`: texto claro sobre fondo oscuro. `light`: para fondos claros (p. ej. Ajustes). */
  variant?: LanguageSelectorVariant;
}

/**
 * LanguageSelector - Cambia el idioma de la UI y lo persiste en el servidor.
 */
export default function LanguageSelector({ variant = 'navbar' }: LanguageSelectorProps): JSX.Element {
  const { i18n, t } = useTranslation();
  const { showTranslated } = useToast();
  const [saving, setSaving] = useState(false);
  const isLight = variant === 'light';

  const changeLanguage = async (lng: string): Promise<void> => {
    if (saving) return;
    const base = lng.toLowerCase().split('-')[0];
    if (base !== 'es' && base !== 'en') return;
    setSaving(true);
    try {
      await userSettingsService.putLanguage(base);
      await i18n.changeLanguage(base);
    } catch {
      showTranslated('navbar.languageSaveError', 'error');
    } finally {
      setSaving(false);
    }
  };

  const activeEn = i18n.language === 'en' || i18n.language.startsWith('en');
  const activeEs = i18n.language === 'es' || i18n.language.startsWith('es');

  const btn = (active: boolean): CSSProperties => ({
    padding: '0.5rem 1rem',
    backgroundColor: active ? '#0d6efd' : isLight ? '#f8f9fa' : 'transparent',
    color: active ? '#fff' : isLight ? '#212529' : 'white',
    border: isLight ? '1px solid #ced4da' : '1px solid white',
    borderRadius: '4px',
    cursor: saving ? 'wait' : 'pointer',
    fontSize: '0.875rem',
    fontWeight: active ? 'bold' : 'normal',
    opacity: saving ? 0.7 : 1
  });

  return (
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <button type="button" disabled={saving} onClick={() => void changeLanguage('en')} style={btn(activeEn)}>
        EN
      </button>
      <button type="button" disabled={saving} onClick={() => void changeLanguage('es')} style={btn(activeEs)}>
        ES
      </button>
      {saving && (
        <span style={{ fontSize: '0.75rem', color: isLight ? '#6c757d' : 'rgba(255,255,255,0.85)' }}>
          {t('navbar.savingLanguage')}
        </span>
      )}
    </div>
  );
}
