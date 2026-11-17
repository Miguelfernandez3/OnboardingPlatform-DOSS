import { useTranslation } from 'react-i18next';

interface LoadingSpinnerProps {
  message?: string;
}

/**
 * LoadingSpinner - Componente de carga a pantalla completa / sección
 */
export default function LoadingSpinner({ message }: LoadingSpinnerProps): JSX.Element {
  const { t } = useTranslation();
  const displayMessage = message || t('common.loading');

  return (
    <div className="loading-spinner-page" role="status" aria-live="polite">
      <span className="loading-spinner-ring" aria-hidden />
      <p>{displayMessage}</p>
    </div>
  );
}
