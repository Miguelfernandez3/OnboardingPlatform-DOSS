import { useTranslation } from 'react-i18next';

interface LoadingSpinnerProps {
  message?: string;
}

/**
 * LoadingSpinner - Componente de carga
 */
export default function LoadingSpinner({ message }: LoadingSpinnerProps): JSX.Element {
  const { t } = useTranslation();
  const displayMessage = message || t('common.loading');
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      padding: '2rem'
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        border: '4px solid #f3f3f3',
        borderTop: '4px solid #3498db',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite'
      }}></div>
      <p style={{ marginTop: '1rem', color: '#666' }}>{displayMessage}</p>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

