import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { ErrorCode } from '../api/errors/ErrorCode';
import { extractApiError } from '../api/errors/errorUtils';

type ToastVariant = 'success' | 'error' | 'warning' | 'info';

/**
 * Hook personalizado para mostrar notificaciones toast con soporte i18n
 */
export function useToast() {
  const { t } = useTranslation();

  /**
   * Muestra un toast de éxito
   */
  const showSuccess = (message: string, duration?: number) => {
    toast.success(message, { duration });
  };

  /**
   * Muestra un toast de error
   */
  const showError = (message: string, duration?: number) => {
    toast.error(message, { duration });
  };

  /**
   * Muestra un toast de advertencia
   */
  const showWarning = (message: string, duration?: number) => {
    toast(message, {
      icon: '⚠️',
      duration,
      style: {
        background: '#f59e0b',
        color: '#fff',
      },
    });
  };

  /**
   * Muestra un toast de información
   */
  const showInfo = (message: string, duration?: number) => {
    toast(message, {
      icon: 'ℹ️',
      duration,
      style: {
        background: '#3b82f6',
        color: '#fff',
      },
    });
  };

  /**
   * Muestra un error de API con traducción automática
   * Busca la traducción en: errors.{code} o errors.GENERIC
   */
  const showApiError = (error: unknown, customMessage?: string) => {
    const apiError = extractApiError(error);
    
    // Si hay un mensaje personalizado, usarlo
    if (customMessage) {
      showError(customMessage);
      return;
    }

    // Intentar traducir el código de error
    const translationKey = `errors.${apiError.code}`;
    const translatedMessage = t(translationKey, { 
      defaultValue: apiError.message || t('errors.GENERIC'),
      ...apiError.details 
    });

    // Si la traducción existe y es diferente a la key, usarla
    if (translatedMessage !== translationKey) {
      showError(translatedMessage);
    } else {
      // Si no hay traducción, usar el mensaje del error
      showError(apiError.message || t('errors.GENERIC'));
    }
  };

  /**
   * Muestra un error con código específico y traducción
   */
  const showErrorByCode = (code: ErrorCode | string, fallbackMessage?: string) => {
    const translationKey = `errors.${code}`;
    const message = t(translationKey, { 
      defaultValue: fallbackMessage || t('errors.GENERIC')
    });
    showError(message);
  };

  /**
   * Muestra un mensaje genérico con traducción
   */
  const showTranslated = (key: string, type: ToastVariant = 'info', options?: Record<string, string>) => {
    const message = t(key, options);
    switch (type) {
      case 'success':
        showSuccess(message);
        break;
      case 'error':
        showError(message);
        break;
      case 'warning':
        showWarning(message);
        break;
      default:
        showInfo(message);
    }
  };

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showApiError,
    showErrorByCode,
    showTranslated,
  };
}
