import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Device } from '../../../core/domain/entities/Device';

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
  const [formData, setFormData] = useState({
    ip: device.ip || '',
    mac: device.mac || '',
    model: device.model || '',
    mudurl: device.mudurl || ''
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

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
    setError(null);

    // Validaciones
    if (formData.ip && !validateIP(formData.ip)) {
      setError(t('device.info.invalidIP'));
      return;
    }

    if (formData.mac && !validateMAC(formData.mac)) {
      setError(t('device.info.invalidMAC'));
      return;
    }

    try {
      setLoading(true);
      await onSave(formData);
    } catch (err) {
      setError((err as Error).message || t('device.info.saveError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '2rem',
        maxWidth: '500px',
        width: '90%',
        maxHeight: '90vh',
        overflowY: 'auto'
      }}>
        <h2 style={{ marginTop: 0 }}>{t('device.info.editTitle')}</h2>

        {error && (
          <div style={{
            marginBottom: '1rem',
            padding: '1rem',
            backgroundColor: '#f8d7da',
            color: '#721c24',
            borderRadius: '4px',
            border: '1px solid #f5c6cb'
          }}>
            <strong>{t('common.error')}:</strong> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('device.info.ip')}:
              </label>
              <input
                type="text"
                value={formData.ip}
                onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
                placeholder="192.168.1.100"
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
                required
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
