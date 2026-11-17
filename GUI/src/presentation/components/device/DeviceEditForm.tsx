import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Device } from '../../../core/domain/entities/Device';
import { useToast } from '../../../infrastructure/notifications/useToast';

type EncRow = { key: string; value: string };

function buildEncRows(device: Device): EncRow[] {
  const ctx = device.enforcementContext;
  if (!ctx || typeof ctx !== 'object') return [];
  return Object.entries(ctx as Record<string, unknown>).map(([k, v]) => ({
    key: k,
    value: v == null ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v)
  }));
}

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
  const [encRows, setEncRows] = useState<EncRow[]>(() => buildEncRows(device));
  const [bearerInput, setBearerInput] = useState('');
  const [removeBearer, setRemoveBearer] = useState(false);
  const [loading, setLoading] = useState<boolean>(false);

  const showBearerHint = useMemo(
    () => Boolean(device.bearerTokenConfigured) && !bearerInput.trim() && !removeBearer,
    [device.bearerTokenConfigured, bearerInput, removeBearer]
  );

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
      const enc: Record<string, unknown> = {};
      for (const row of encRows) {
        const k = row.key.trim();
        if (!k) continue;
        const raw = row.value;
        if (raw.trim() === '') {
          enc[k] = '';
        } else {
          try {
            enc[k] = JSON.parse(raw) as unknown;
          } catch {
            enc[k] = raw;
          }
        }
      }
      const payload: Partial<Device> = {
        name: formData.name,
        type: formData.type,
        manufacturer: formData.manufacturer,
        model: formData.model,
        ip: formData.ip,
        mac: formData.mac,
        mudurl: formData.mudurl,
        enforcementContext: enc
      };
      if (bearerInput.trim()) {
        (payload as Record<string, unknown>).bearerToken = bearerInput.trim();
      } else if (removeBearer) {
        (payload as Record<string, unknown>).bearerToken = '';
      }
      await onSave(payload);
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
          maxWidth: '560px',
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

            <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid #e9ecef' }}>
              <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem' }}>{t('device.info.enforcementSection')}</h3>
              <p style={{ fontSize: '0.875rem', color: '#6c757d', margin: '0 0 0.75rem 0' }}>
                {t('device.info.enforcementContextHint')}
              </p>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>
                      <th style={{ padding: '0.35rem' }}>{t('device.info.enforcementKey')}</th>
                      <th style={{ padding: '0.35rem' }}>{t('device.info.enforcementValue')}</th>
                      <th style={{ padding: '0.35rem' }} />
                    </tr>
                  </thead>
                  <tbody>
                    {encRows.map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f1f3f4' }}>
                        <td style={{ padding: '0.35rem', verticalAlign: 'top' }}>
                          <input
                            type="text"
                            value={row.key}
                            onChange={e => {
                              const next = encRows.map((r, j) => (j === i ? { ...r, key: e.target.value } : r));
                              setEncRows(next);
                            }}
                            style={{ width: '100%', minWidth: '100px', padding: '0.4rem', border: '1px solid #ced4da', borderRadius: '4px' }}
                            autoComplete="off"
                            data-lpignore="true"
                            data-form-type="other"
                          />
                        </td>
                        <td style={{ padding: '0.35rem', verticalAlign: 'top' }}>
                          <input
                            type="text"
                            value={row.value}
                            onChange={e => {
                              const next = encRows.map((r, j) => (j === i ? { ...r, value: e.target.value } : r));
                              setEncRows(next);
                            }}
                            style={{ width: '100%', minWidth: '120px', padding: '0.4rem', border: '1px solid #ced4da', borderRadius: '4px' }}
                            autoComplete="off"
                            data-lpignore="true"
                            data-form-type="other"
                          />
                        </td>
                        <td style={{ padding: '0.35rem', verticalAlign: 'top' }}>
                          <button
                            type="button"
                            onClick={() => setEncRows(encRows.filter((_, j) => j !== i))}
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                          >
                            {t('device.info.enforcementRemoveRow')}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button
                type="button"
                onClick={() => setEncRows([...encRows, { key: '', value: '' }])}
                style={{ marginTop: '0.5rem', padding: '0.4rem 0.75rem', fontSize: '0.875rem' }}
              >
                {t('device.info.enforcementAddRow')}
              </button>
            </div>

            <div style={{ marginTop: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {t('device.info.bearerTokenLabel')}
              </label>
              <p style={{ fontSize: '0.8rem', color: '#6c757d', margin: '0 0 0.5rem 0' }}>
                {t('device.info.bearerTokenHint')}
              </p>
              {showBearerHint && (
                <p style={{ fontSize: '0.8rem', color: '#155724', background: '#d4edda', padding: '0.5rem', borderRadius: '4px' }}>
                  {t('device.info.bearerTokenConfigured')}
                </p>
              )}
              <input
                type="password"
                value={bearerInput}
                onChange={e => {
                  setBearerInput(e.target.value);
                  if (e.target.value) setRemoveBearer(false);
                }}
                placeholder={t('device.info.bearerTokenNewPlaceholder')}
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '1rem',
                  marginTop: '0.5rem'
                }}
              />
              {device.bearerTokenConfigured && (
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', fontSize: '0.875rem' }}>
                  <input
                    type="checkbox"
                    checked={removeBearer}
                    onChange={e => {
                      setRemoveBearer(e.target.checked);
                      if (e.target.checked) setBearerInput('');
                    }}
                  />
                  {t('device.info.bearerTokenRemove')}
                </label>
              )}
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
