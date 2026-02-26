import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Device } from '../../../core/domain/entities/Device';
import { useToast } from '../../../infrastructure/notifications/useToast';

interface DeviceEditFormProps {
  device: Device;
  onSave: (data: Partial<Device>) => Promise<void>;
  onCancel: () => void;
}

/**
 * DeviceEditForm - Formulario modal para editar dispositivo
 */
export default function DeviceEditForm({ device, onSave, onCancel }: DeviceEditFormProps): JSX.Element {
  const { t } = useTranslation();
  const { showTranslated, showApiError } = useToast();
  const [formData, setFormData] = useState({
    name: device.name || '',
    type: device.type || '',
    manufacturer: device.manufacturer || '',
    ip: device.ip || '',
    mac: device.mac || '',
    model: device.model || '',
    mudurl: device.mudurl || ''
  });
  const [loading, setLoading] = useState<boolean>(false);

  // Bloquear scroll del body cuando el modal está abierto
  useEffect(() => {
    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = 'hidden';
    
    return () => {
      document.body.style.overflow = originalStyle;
    };
  }, []);

  const validateIP = (ip: string): boolean => {
    if (!ip) return true; // Opcional
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(ip)) return false;
    const parts = ip.split('.').map(Number);
    return parts.every(part => part >= 0 && part <= 255);
  };

  const validateMAC = (mac: string): boolean => {
    if (!mac) return true; // Opcional
    const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
    return macRegex.test(mac);
  };

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();

    // Validaciones
    if (formData.ip && !validateIP(formData.ip)) {
      showTranslated('device.info.invalidIP', 'error');
      return;
    }

    if (formData.mac && !validateMAC(formData.mac)) {
      showTranslated('device.info.invalidMAC', 'error');
      return;
    }

    try {
      setLoading(true);
      await onSave(formData);
    } catch (err) {
      showApiError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    if (e.target === e.currentTarget && !loading) {
      onCancel();
    }
  };

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
          maxWidth: '500px',
          width: '90%',
          maxHeight: '90vh',
          overflowY: 'auto',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ marginTop: 0, marginBottom: '1rem' }}>{t('device.info.editTitle')}</h2>

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('device.info.name')}:
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder={t('device.info.namePlaceholder')}
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('device.info.type')}:
              </label>
              <input
                type="text"
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                placeholder={t('device.info.typePlaceholder')}
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('device.info.manufacturer')}:
              </label>
              <input
                type="text"
                value={formData.manufacturer}
                onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                placeholder={t('device.info.manufacturerPlaceholder')}
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('common.model')}:
              </label>
              <input
                type="text"
                value={formData.model}
                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                placeholder={t('device.info.modelPlaceholder')}
                required
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold'}}>
                {t('device.info.ip')}:
              </label>
              <input
                type="text"
                value={formData.ip}
                onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
                placeholder="192.168.1.100"
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('device.info.mac')}:
              </label>
              <input
                type="text"
                value={formData.mac}
                onChange={(e) => setFormData({ ...formData, mac: e.target.value })}
                placeholder="00:1B:44:11:3A:B7"
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('device.info.mudUrl')}:
              </label>
              <input
                type="url"
                value={formData.mudurl}
                onChange={(e) => setFormData({ ...formData, mudurl: e.target.value })}
                placeholder="https://example.com/mud/device.json"
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>

          <div style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '1rem',
            marginTop: '2rem'
          }}>
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '1rem'
              }}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '1rem'
              }}
            >
              {loading ? t('common.loading') : t('common.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
