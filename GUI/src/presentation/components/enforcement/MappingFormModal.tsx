import { useTranslation } from 'react-i18next';
import * as s from './styles';

export interface MappingFormState {
  matchKind: 'explicitProfile' | 'policyType' | 'capability';
  matchValue: string;
  profileId: string;
  priority: number;
  isActive: boolean;
}

const MATCH_KIND_KEYS: Record<MappingFormState['matchKind'], { label: string; hint: string }> = {
  policyType: { label: 'matchKindPolicyType', hint: 'matchKindPolicyTypeHint' },
  capability: { label: 'matchKindCapability', hint: 'matchKindCapabilityHint' },
  explicitProfile: { label: 'matchKindExplicitProfile', hint: 'matchKindExplicitProfileHint' },
};

interface Props {
  isOpen: boolean;
  onClose: () => void;
  form: MappingFormState;
  setForm: React.Dispatch<React.SetStateAction<MappingFormState>>;
  editingId: string | null;
  profileOptions: { value: string; label: string }[];
  onSave: () => Promise<void>;
  onValidationError: (msg: string) => void;
  isMobile: boolean;
  onSuccess?: (msg: string) => void;
}

export default function MappingFormModal({
  isOpen,
  onClose,
  form,
  setForm,
  editingId,
  profileOptions,
  onSave,
  onValidationError,
  isMobile,
  onSuccess
}: Props): JSX.Element | null {
  const { t } = useTranslation();

  const validateForm = (): string | null => {
    if (!form.matchValue.trim()) {
      return t('enforcementAdmin.mappings.validationMatchValueRequired');
    }
    if (!form.profileId.trim()) {
      return t('enforcementAdmin.mappings.validationProfileRequired');
    }
    const priority = Number(form.priority);
    if (Number.isNaN(priority) || priority < 0 || priority > 9999) {
      return t('enforcementAdmin.mappings.validationPriorityRange');
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
        ? t('enforcementAdmin.mappings.updateSuccess')
        : t('enforcementAdmin.mappings.createSuccess'));
      onClose();
    } catch {
      // Error handled by parent
    }
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
          {editingId ? t('enforcementAdmin.mappings.formTitleEdit') : t('enforcementAdmin.mappings.formTitleNew')}
        </h3>

        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.mappings.sectionMatchRule')}</div>
          <p style={{ fontSize: '0.8125rem', color: '#6c757d', margin: '0 0 0.75rem 0' }}>
            {t('enforcementAdmin.mappings.sectionMatchRuleHint')}
          </p>
          <div style={s.formRow}>
            <div>
              <div style={s.formLabel}>{t('enforcementAdmin.mappings.matchKind')}</div>
              <select
                style={s.select}
                value={form.matchKind}
                onChange={e => setForm(prev => ({ ...prev, matchKind: e.target.value as MappingFormState['matchKind'] }))}
              >
                {(Object.keys(MATCH_KIND_KEYS) as MappingFormState['matchKind'][]).map(kind => (
                  <option key={kind} value={kind}>
                    {t(`enforcementAdmin.mappings.${MATCH_KIND_KEYS[kind].label}`)}
                  </option>
                ))}
              </select>
              <div style={s.optionHint}>
                {t(`enforcementAdmin.mappings.${MATCH_KIND_KEYS[form.matchKind].hint}`)}
              </div>
            </div>
            <div>
              <div style={s.formLabel}>{t('enforcementAdmin.mappings.matchValue')}</div>
              <input
                style={s.input}
                placeholder={t('enforcementAdmin.mappings.matchValuePlaceholder')}
                value={form.matchValue}
                onChange={e => setForm(prev => ({ ...prev, matchValue: e.target.value }))}
              />
              <div style={s.optionHint}>{t('enforcementAdmin.mappings.matchValueHint')}</div>
            </div>
          </div>
        </div>

        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.mappings.sectionTarget')}</div>
          <div style={s.formRow}>
            <div style={{ gridColumn: isMobile ? '1' : 'span 1' }}>
              <div style={s.formLabel}>{t('enforcementAdmin.mappings.profile')}</div>
              <select
                style={s.select}
                value={form.profileId}
                onChange={e => setForm(prev => ({ ...prev, profileId: e.target.value }))}
              >
                <option value="">{t('enforcementAdmin.mappings.selectProfile')}</option>
                {profileOptions.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <div style={s.optionHint}>{t('enforcementAdmin.mappings.profileHint')}</div>
            </div>
            <div>
              <div style={s.formLabel}>{t('enforcementAdmin.mappings.priority')}</div>
              <input
                style={s.input}
                type="number"
                min={0}
                max={9999}
                value={form.priority}
                onChange={e => setForm(prev => ({ ...prev, priority: Number(e.target.value) || 0 }))}
              />
              <div style={s.optionHint}>{t('enforcementAdmin.mappings.priorityHint')}</div>
            </div>
          </div>
        </div>

        <div style={s.formSection}>
          <div style={s.formSectionTitle}>{t('enforcementAdmin.mappings.sectionOptions')}</div>
          <div style={s.optionsCard}>
            <div style={s.optionItem}>
              <label style={s.optionLabel}>
                <input
                  type="checkbox"
                  checked={form.isActive}
                  onChange={e => setForm(prev => ({ ...prev, isActive: e.target.checked }))}
                />{' '}
                {t('enforcementAdmin.mappings.active')}
              </label>
              <div style={s.optionHint}>{t('enforcementAdmin.mappings.activeHint')}</div>
            </div>
          </div>
        </div>

        <div style={s.buttonRow}>
          <button style={editingId ? s.btnPrimary : s.btnSuccess} onClick={handleSave}>
            {editingId ? t('enforcementAdmin.mappings.update') : t('enforcementAdmin.mappings.create')}
          </button>
          <button style={s.btnSecondary} type="button" onClick={onClose}>
            {t('enforcementAdmin.mappings.cancelEdit')}
          </button>
        </div>
      </div>
    </div>
  );
}
