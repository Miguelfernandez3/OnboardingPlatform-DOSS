import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CreateDeviceFromDSPInput } from '../../../core/ports';
import { useToast } from '../../../infrastructure/notifications/useToast';

interface DeviceCreateFormProps {
  onCreate: (data: CreateDeviceFromDSPInput) => Promise<void>;
  onCancel: () => void;
}

type FormField =
  | 'deviceId'
  | 'idspId'
  | 'model'
  | 'name'
  | 'type'
  | 'manufacturer'
  | 'ip'
  | 'mac'
  | 'edk';

type FieldErrors = Partial<Record<FormField, string>>;

const INPUT_STYLE: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem',
  border: '1px solid #ced4da',
  borderRadius: '4px',
  fontSize: '1rem',
};

const ERROR_INPUT_STYLE: React.CSSProperties = {
  ...INPUT_STYLE,
  borderColor: '#dc3545',
};

/**
 * DeviceCreateForm - Formulario modal para crear un dispositivo desde DSP.
 */
export default function DeviceCreateForm({ onCreate, onCancel }: DeviceCreateFormProps): JSX.Element {
  const { t } = useTranslation();
  const { showApiError } = useToast();
  const [formData, setFormData] = useState({
    deviceId: '',
    idspId: '',
    model: '',
    name: '',
    type: '',
    manufacturer: '',
    ip: '',
    mac: '',
    edk: '',
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = originalStyle;
    };
  }, []);

  const validateIP = (ip: string): boolean => {
    if (!ip) return true;
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(ip)) return false;
    const parts = ip.split('.').map(Number);
    return parts.every((part) => part >= 0 && part <= 255);
  };

  const validateMAC = (mac: string): boolean => {
    if (!mac) return true;
    const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
    return macRegex.test(mac);
  };

  const validateForm = (): FieldErrors => {
    const errors: FieldErrors = {};

    if (!formData.deviceId.trim()) {
      errors.deviceId = t('device.create.deviceIdRequired');
    }
    if (!formData.idspId.trim()) {
      errors.idspId = t('device.create.idspIdRequired');
    }
    if (formData.ip.trim() && !validateIP(formData.ip.trim())) {
      errors.ip = t('device.info.invalidIP');
    }
    if (formData.mac.trim() && !validateMAC(formData.mac.trim())) {
      errors.mac = t('device.info.invalidMAC');
    }

    return errors;
  };

  const clearFieldError = (field: FormField): void => {
    setFieldErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const updateField = (field: FormField, value: string): void => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (submitAttempted || fieldErrors[field]) {
      clearFieldError(field);
    }
  };

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setSubmitAttempted(true);

    const errors = validateForm();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    try {
      setLoading(true);
      await onCreate({
        deviceId: formData.deviceId.trim(),
        idspId: formData.idspId.trim(),
        model: formData.model.trim() || undefined,
        name: formData.name.trim() || undefined,
        type: formData.type.trim() || undefined,
        manufacturer: formData.manufacturer.trim() || undefined,
        ip: formData.ip.trim() || undefined,
        mac: formData.mac.trim() || undefined,
        edk: formData.edk.trim() || undefined,
      });
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

  const getInputStyle = (field: FormField): React.CSSProperties =>
    fieldErrors[field] ? ERROR_INPUT_STYLE : INPUT_STYLE;

  const optionalSuffix = (
    <span style={{ fontWeight: 'normal', color: '#6c757d' }}>
      {' '}({t('common.optional')})
    </span>
  );

  const renderField = (
    field: FormField,
    label: string,
    options: {
      optional?: boolean;
      placeholder?: string;
      autoComplete?: string;
    } = {},
  ): JSX.Element => {
    const inputId = `device-create-${field}`;
    const errorId = `${inputId}-error`;

    return (
      <div>
        <label htmlFor={inputId} style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
          {label}:{options.optional ? optionalSuffix : null}
        </label>
        <input
          id={inputId}
          type="text"
          value={formData[field]}
          onChange={(e) => updateField(field, e.target.value)}
          onBlur={() => {
            if (!submitAttempted) return;
            const errors = validateForm();
            setFieldErrors((prev) => {
              const next = { ...prev };
              if (errors[field]) {
                next[field] = errors[field];
              } else {
                delete next[field];
              }
              return next;
            });
          }}
          placeholder={options.placeholder}
          autoComplete={options.autoComplete ?? 'off'}
          aria-invalid={fieldErrors[field] ? true : undefined}
          aria-describedby={fieldErrors[field] ? errorId : undefined}
          data-lpignore="true"
          data-form-type="other"
          disabled={loading}
          style={getInputStyle(field)}
        />
        {fieldErrors[field] && (
          <div id={errorId} role="alert" style={{ color: '#dc3545', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {fieldErrors[field]}
          </div>
        )}
      </div>
    );
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
        overflow: 'hidden',
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
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ marginTop: 0, marginBottom: '0.75rem' }}>{t('device.create.title')}</h2>
        <p style={{ marginTop: 0, marginBottom: '1.5rem', color: '#495057', lineHeight: 1.5 }}>
          {t('device.create.description')}
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {renderField('deviceId', t('device.create.deviceId'), {
              placeholder: t('device.create.deviceIdPlaceholder'),
            })}
            {renderField('idspId', t('device.create.idspId'), {
              placeholder: t('device.create.idspIdPlaceholder'),
            })}
            {renderField('model', t('common.model'), {
              optional: true,
              placeholder: t('device.info.modelPlaceholder'),
            })}
            {renderField('name', t('device.info.name'), {
              optional: true,
              placeholder: t('device.info.namePlaceholder'),
            })}
            {renderField('type', t('device.info.type'), {
              optional: true,
              placeholder: t('device.info.typePlaceholder'),
            })}
            {renderField('manufacturer', t('device.info.manufacturer'), {
              optional: true,
              placeholder: t('device.info.manufacturerPlaceholder'),
            })}
            {renderField('ip', t('device.info.ip'), {
              optional: true,
              placeholder: '192.168.1.100',
            })}
            {renderField('mac', t('device.info.mac'), {
              optional: true,
              placeholder: '00:1B:44:11:3A:B7',
            })}
            {renderField('edk', t('device.info.edk'), {
              optional: true,
              placeholder: t('device.create.edkPlaceholder'),
            })}
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '1rem',
              marginTop: '2rem',
            }}
          >
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
                fontSize: '1rem',
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
                fontSize: '1rem',
              }}
            >
              {loading ? t('device.create.creating') : t('device.create.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
