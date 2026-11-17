import { apiClient } from '../../config';
import type { UserUiSettings } from '../../core/ports';
import i18n from '../../i18n/config';

/**
 * Preferencias de UI del usuario (idioma, etc.) — backend `/api/users/me/settings`.
 */
export const userSettingsService = {
  get: (): Promise<UserUiSettings> => apiClient.getUserUiSettings(),

  putLanguage: (language: string): Promise<UserUiSettings> =>
    apiClient.putUserUiSettings({ language })
};

/**
 * Aplica el idioma guardado en el servidor a i18next (silencioso si no hay sesión).
 */
export async function syncUiLanguageFromServer(): Promise<void> {
  try {
    const { language } = await userSettingsService.get();
    const base = (language || 'es').toLowerCase().split('-')[0];
    if (base === 'es' || base === 'en') {
      await i18n.changeLanguage(base);
    }
  } catch {
    /* 401 / sin token / red: mantener idioma del detector */
  }
}
