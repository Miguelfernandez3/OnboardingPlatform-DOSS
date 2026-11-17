import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { EnforcementSecretMetadata } from '../../../core/ports';
import ContextSpecEditor from './ContextSpecEditor';
import { hasValidBearerForAuthSpec, isRequireStoredDeviceBearerFromSpec } from './contextSpecUtils';
import * as s from './styles';

export interface ProfileFormState {
  name: string;
  mode: 'rest' | 'era';
  method: string;
  endpointTemplate: string;
  headersTemplate: string;
  payloadTemplate: string;
  timeoutSeconds: number;
  dryRun: boolean;
  isDefault: boolean;
  isActive: boolean;
  autoEnforceOnRegistration: boolean;
  authType: 'none' | 'bearer';
  authSecretId: string;
  allowMsplToken: boolean;
  contextSpec: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  form: ProfileFormState;
  setForm: React.Dispatch<React.SetStateAction<ProfileFormState>>;
  editingId: string | null;
  secrets: EnforcementSecretMetadata[];
  onSave: () => Promise<void>;
  onValidationError: (msg: string) => void;
  isMobile: boolean;
  onSuccess?: (msg: string) => void;
}

export default function ProfileFormModal({
  isOpen,
  onClose,
  form,
  setForm,
  editingId,
  secrets,
  onSave,
  onValidationError,
  isMobile,
  onSuccess
}: Props): JSX.Element | null {
  const { t } = useTranslation();

  const handleContextSpecChange = useCallback(
    (next: string) => {
      setForm(prev => ({ ...prev, contextSpec: next }));
    },
    [setForm]
  );

  const isEraMode = form.mode === 'era';
  const showAuthSecret = form.authType === 'bearer';
  const bearerFromDevice = isRequireStoredDeviceBearerFromSpec(form.contextSpec);
  /** Secreto del gestor obligatorio si hay Bearer, el token no viene del dispositivo y no hay fallback MSPL. */
  const needManagerSecret = showAuthSecret && !bearerFromDevice && !form.allowMsplToken;

  const validateForm = (): string | null => {
    if (!form.name.trim()) {
      return t('enforcementAdmin.profiles.validationNameRequired');
    }
    if (isEraMode) {
      return null;
    }
    if (!form.endpointTemplate.trim()) {
      return t('enforcementAdmin.profiles.validationEndpointRequired');
    }
    if (needManagerSecret && !form.authSecretId.trim()) {
      return t('enforcementAdmin.profiles.validationAuthSecretRequired');
    }
    if (showAuthSecret && !form.authSecretId.trim() && !hasValidBearerForAuthSpec(form.contextSpec)) {
      return t('enforcementAdmin.profiles.validationBearerContextKey');
    }
    const timeout = Number(form.timeoutSeconds);
    if (Number.isNaN(timeout) || timeout < 1 || timeout > 300) {
      return t('enforcementAdmin.profiles.validationTimeoutRange');
    }
    if (form.headersTemplate.trim()) {
      try {
        JSON.parse(form.headersTemplate);
      } catch {
        return t('enforcementAdmin.profiles.validationInvalidJson', { field: t('enforcementAdmin.profiles.headersTemplate') });
      }
    }
    if (form.payloadTemplate.trim()) {
      try {
        JSON.parse(form.payloadTemplate);
      } catch {
        return t('enforcementAdmin.profiles.validationInvalidJson', { field: t('enforcementAdmin.profiles.payloadTemplate') });
      }
    }
    if (form.contextSpec.trim()) {
      try {
        JSON.parse(form.contextSpec);
      } catch {
        return t('enforcementAdmin.profiles.validationContextSpecJson');
      }
    }
    return null;
  };

  const handleSave = async () => {
    const validationError = validateForm();
    if (validationError) {
      onValidationError(validationError);
      return;
    }
    try {
      await onSave();
      onSuccess?.(editingId
        ? t('enforcementAdmin.profiles.updateSuccess')
        : t('enforcementAdmin.profiles.createSuccess'));
      onClose();
    } catch {
      // Error handled by parent (showApiError)
    }
  };

  const updateField = <K extends keyof ProfileFormState>(key: K, value: ProfileFormState[K]) => {
    setForm(prev => ({ ...prev, [key]: value }));
  };

  if (!isOpen) return null;

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
        padding: isMobile ? '1rem' : '0',
      }}
      onMouseDown={onClose}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '1.25rem',
          width: '50%',
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: '#495057' }}>
          {editingId ? t('enforcementAdmin.profiles.formTitleEdit') : t('enforcementAdmin.profiles.formTitleNew')}
        </h3>

        {/* Basic */}
        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.profiles.sectionBasic')}</div>
          <div style={s.formRow}>
            <div>
              <div style={s.formLabel}>{t('enforcementAdmin.profiles.name')}</div>
              <input
                style={s.input}
                placeholder={t('enforcementAdmin.profiles.namePlaceholder')}
                value={form.name}
                onChange={e => updateField('name', e.target.value)}
              />
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.nameHint')}</div>
            </div>
            <div>
              <div style={s.formLabel}>{t('enforcementAdmin.profiles.mode')}</div>
              <select style={s.select} value={form.mode} onChange={e => updateField('mode', e.target.value as 'rest' | 'era')}>
                <option value="rest">REST</option>
                <option value="era">ERA</option>
              </select>
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.modeHint')}</div>
            </div>
          </div>
        </div>

        {!isEraMode && (
        <>
        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.profiles.sectionRequest')}</div>
          <div style={s.formRow}>
            <div>
              <div style={s.formLabel}>{t('enforcementAdmin.profiles.method')}</div>
              <select style={s.select} value={form.method} onChange={e => updateField('method', e.target.value)}>
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="PATCH">PATCH</option>
                <option value="DELETE">DELETE</option>
              </select>
            </div>
            <div style={{ gridColumn: isMobile ? '1' : 'span 2' }}>
              <div style={s.formLabel}>{t('enforcementAdmin.profiles.endpointTemplate')}</div>
              <input
                style={s.input}
                placeholder={t('enforcementAdmin.profiles.endpointPlaceholder')}
                value={form.endpointTemplate}
                onChange={e => updateField('endpointTemplate', e.target.value)}
              />
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.endpointHint')}</div>
            </div>
            <div>
              <div style={s.formLabel}>{t('enforcementAdmin.profiles.timeout')}</div>
              <input
                style={s.input}
                type="number"
                min={1}
                max={300}
                value={form.timeoutSeconds}
                onChange={e => updateField('timeoutSeconds', Number(e.target.value) || 10)}
              />
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.timeoutHint')}</div>
            </div>
          </div>
        </div>

        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.profiles.sectionTemplates')}</div>
          <div style={s.formRow}>
            <div style={s.formFieldFull}>
              <div style={s.formLabel}>{t('enforcementAdmin.profiles.headersTemplate')}</div>
              <textarea
                style={{ ...s.textarea, minHeight: '72px' }}
                placeholder={t('enforcementAdmin.profiles.headersPlaceholder')}
                value={form.headersTemplate}
                onChange={e => updateField('headersTemplate', e.target.value)}
                rows={3}
              />
            </div>
            <div style={s.formFieldFull}>
              <div style={s.formLabel}>{t('enforcementAdmin.profiles.payloadTemplate')}</div>
              <textarea
                style={{ ...s.textarea, minHeight: '72px' }}
                placeholder={t('enforcementAdmin.profiles.payloadPlaceholder')}
                value={form.payloadTemplate}
                onChange={e => updateField('payloadTemplate', e.target.value)}
                rows={3}
              />
            </div>
          </div>
        </div>

        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.profiles.sectionContextAndAuth')}</div>
          <p style={s.sectionIntroMuted}>{t('enforcementAdmin.profiles.sectionContextAndAuthIntro')}</p>
          <div style={s.mergedContextAuthPanel}>
            <div>
              <div style={s.formSubsectionTitle}>{t('enforcementAdmin.profiles.sectionContextSpec')}</div>
              <div style={s.formFieldFull} key={editingId ?? 'new'}>
                <ContextSpecEditor
                  value={form.contextSpec}
                  onChange={handleContextSpecChange}
                  showBearerKeyColumn={form.authType === 'bearer' && !form.authSecretId.trim()}
                />
              </div>
            </div>

            <div style={s.mergedContextAuthDivider}>
              <div style={s.formSubsectionTitle}>{t('enforcementAdmin.profiles.sectionAuth')}</div>
              <p
                style={{
                  ...s.bearerStrategySummary,
                  ...(showAuthSecret
                    ? bearerFromDevice
                      ? {
                          backgroundColor: '#d1ecf1',
                          color: '#0c5460',
                          borderColor: '#bee5eb',
                        }
                      : {
                          backgroundColor: '#fff3cd',
                          color: '#664d03',
                          borderColor: '#ffe69c',
                        }
                    : {
                        backgroundColor: '#e9ecef',
                        color: '#495057',
                        borderColor: '#dee2e6',
                      }),
                }}
              >
                {showAuthSecret
                  ? bearerFromDevice
                    ? t('enforcementAdmin.profiles.bearerStrategySummaryDevice')
                    : t('enforcementAdmin.profiles.bearerStrategySummaryManager')
                  : t('enforcementAdmin.profiles.bearerStrategySummaryNone')}
              </p>
              {showAuthSecret && bearerFromDevice && (
                <p style={{ ...s.optionHintFlush, marginBottom: '0.75rem', marginTop: 0 }}>
                  {t('enforcementAdmin.profiles.bearerDeviceWhereToSetHint')}
                </p>
              )}
              <div style={s.authSectionStack}>
                <div style={s.authFieldColumn}>
                  <div style={{ ...s.formLabel, marginBottom: 0 }}>{t('enforcementAdmin.profiles.authType')}</div>
                  <select style={s.select} value={form.authType} onChange={e => updateField('authType', e.target.value as 'none' | 'bearer')}>
                    <option value="none">{t('enforcementAdmin.profiles.authTypeNone')}</option>
                    <option value="bearer">{t('enforcementAdmin.profiles.authTypeBearer')}</option>
                  </select>
                </div>
                {showAuthSecret && (
                  <div style={s.authSecretColumn}>
                    <div style={{ ...s.formLabel, marginBottom: 0 }}>{t('enforcementAdmin.profiles.authSecret')}</div>
                    {bearerFromDevice && (
                      <p style={s.authInfoBanner}>
                        {t('enforcementAdmin.profiles.authSecretBearerFromDeviceInfo')}
                      </p>
                    )}
                    {secrets.length === 0 && !bearerFromDevice ? (
                      <>
                        <p style={s.authWarningBanner}>
                          {t('enforcementAdmin.profiles.authSecretNoSecrets')}
                        </p>
                        <div style={s.optionHintFlush}>{t('enforcementAdmin.profiles.authSecretHint')}</div>
                      </>
                    ) : (
                      <>
                        <select
                          style={s.select}
                          value={form.authSecretId}
                          onChange={e => updateField('authSecretId', e.target.value)}
                        >
                          <option value="">
                            {bearerFromDevice
                              ? t('enforcementAdmin.profiles.authSecretPlaceholderDevice')
                              : t('enforcementAdmin.profiles.authSecretPlaceholder')}
                          </option>
                          {secrets.map(secret => (
                            <option key={secret.id} value={String(secret.id)}>
                              {secret.name} (ID: {secret.id})
                            </option>
                          ))}
                        </select>
                        <div style={s.optionHintFlush}>
                          {bearerFromDevice
                            ? t('enforcementAdmin.profiles.authSecretHintBearerFromDevice')
                            : t('enforcementAdmin.profiles.authSecretHint')}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div style={s.mergedContextAuthDivider}>
              <div style={s.formSubsectionTitle}>{t('enforcementAdmin.profiles.subsectionBearerExtras')}</div>
              <div style={{ ...s.optionsCard, backgroundColor: '#fff' }}>
                <div style={{ ...s.optionItem, marginBottom: 0 }}>
                  <label style={s.optionLabel}>
                    <input type="checkbox" checked={form.allowMsplToken} onChange={e => updateField('allowMsplToken', e.target.checked)} />{' '}
                    {t('enforcementAdmin.profiles.allowMsplToken')}
                  </label>
                  <div style={s.optionHint}>{t('enforcementAdmin.profiles.allowMsplTokenHint')}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        </>
        )}

        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.profiles.sectionOptions')}</div>
          <div style={s.optionsCard}>
            {!isEraMode && (
            <div style={s.optionItem}>
              <label style={s.optionLabel}>
                <input type="checkbox" checked={form.dryRun} onChange={e => updateField('dryRun', e.target.checked)} />{' '}
                {t('enforcementAdmin.profiles.dryRun')}
              </label>
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.dryRunHint')}</div>
            </div>
            )}
            <div style={s.optionItem}>
              <label style={s.optionLabel}>
                <input type="checkbox" checked={form.isDefault} onChange={e => updateField('isDefault', e.target.checked)} />{' '}
                {t('enforcementAdmin.profiles.default')}
              </label>
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.defaultHint')}</div>
            </div>
            <div style={s.optionItem}>
              <label style={s.optionLabel}>
                <input type="checkbox" checked={form.isActive} onChange={e => updateField('isActive', e.target.checked)} />{' '}
                {t('enforcementAdmin.profiles.active')}
              </label>
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.activeHint')}</div>
            </div>
            <div style={s.optionItem}>
              <label style={s.optionLabel}>
                <input type="checkbox" checked={form.autoEnforceOnRegistration} onChange={e => updateField('autoEnforceOnRegistration', e.target.checked)} />{' '}
                {t('enforcementAdmin.profiles.autoEnforce')}
              </label>
              <div style={s.optionHint}>{t('enforcementAdmin.profiles.autoEnforceHint')}</div>
            </div>
          </div>
        </div>

        <div style={s.buttonRow}>
          <button style={editingId ? s.btnPrimary : s.btnSuccess} onClick={handleSave}>
            {editingId ? t('enforcementAdmin.profiles.update') : t('enforcementAdmin.profiles.create')}
          </button>
          <button style={s.btnSecondary} type="button" onClick={onClose}>
            {t('enforcementAdmin.profiles.cancelEdit')}
          </button>
        </div>
      </div>
    </div>
  );
}
