import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import JsonViewer from '../common/JsonViewer';

interface ThreatMudModalProps {
  threatMudFile: string;
  threatIdentifier: string;
  onClose: () => void;
}

/**
 * ThreatMudModal - Modal para mostrar el archivo MUD de un threat
 */
export default function ThreatMudModal({ threatMudFile, threatIdentifier, onClose }: ThreatMudModalProps): JSX.Element {
  const { t } = useTranslation();

  // Bloquear scroll del body cuando el modal está abierto
  useEffect(() => {
    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = 'hidden';
    
    return () => {
      document.body.style.overflow = originalStyle;
    };
  }, []);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Intentar parsear el JSON, si falla mostrar como texto plano
  let mudData: unknown;
  try {
    mudData = JSON.parse(threatMudFile);
  } catch {
    mudData = threatMudFile;
  }

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
        overflow: 'hidden'
      }}
      onClick={handleOverlayClick}
    >
      <div 
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '2rem',
          maxWidth: '800px',
          width: '90%',
          maxHeight: '90vh',
          overflowY: 'auto',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem'
        }}>
          <h2 style={{ margin: 0 }}>
            {t('device.threats.mudModalTitle')} - {threatIdentifier}
          </h2>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '1rem'
            }}
          >
            {t('common.close')}
          </button>
        </div>

        <JsonViewer 
          data={mudData} 
          title={t('device.threats.threatMudFile')}
        />
      </div>
    </div>
  );
}
