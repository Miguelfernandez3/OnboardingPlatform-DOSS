import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import type { MissingItem } from '../../utils/enforcementContextForm';

export interface EnforceContextModalProps {
  open: boolean;
  title?: string;
  missing: MissingItem[];
  onCancel: () => void;
  onSubmit: (form: Record<string, string>) => Promise<void>;
}

const btnBase: React.CSSProperties = {
  padding: '0.5rem 1rem',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontWeight: 600
};

/**
 * Formulario modal para rellenar placeholders de enforcement faltantes.
 */
export default function EnforceContextModal({
  open,
  title,
  missing,
  onCancel,
  onSubmit
}: EnforceContextModalProps): JSX.Element | null {
  const { t } = useTranslation();
  const [form, setForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setForm({});
      setError(null);
      return;
    }
    const init: Record<string, string> = {};
    for (const m of missing) {
      const k = m.key != null ? String(m.key) : '';
      if (k) init[k] = '';
    }
    setForm(init);
  }, [open, missing]);

  if (!open) {
    return null;
  }

  const handleChange = (key: string, value: string): void => {
    setForm((f) => ({ ...f, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);
    for (const m of missing) {
      const k = m.key != null ? String(m.key) : '';
      if (k && !m.sensitive && (!form[k] || !form[k].trim())) {
        setError(t('enforceContext.fieldRequired', { field: m.label || k }));
        return;
      }
    }
    setSaving(true);
    try {
      await onSubmit(form);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000
      }}
      role="dialog"
      aria-modal="true"
    >
      <form
        onSubmit={(e) => void handleSubmit(e)}
        style={{
          background: '#fff',
          borderRadius: 8,
          padding: '1.25rem',
          minWidth: 'min(400px, 92vw)',
          maxHeight: '90vh',
          overflow: 'auto',
          boxShadow: '0 4px 24px rgba(0,0,0,0.15)'
        }}
      >
        <h2 style={{ margin: '0 0 0.75rem', fontSize: '1.15rem' }}>
          {title || t('enforceContext.title')}
        </h2>
        <p style={{ margin: '0 0 1rem', fontSize: '0.9rem', color: '#555' }}>{t('enforceContext.hint')}</p>
        {error && (
          <div style={{ color: '#b00020', marginBottom: '0.75rem', fontSize: '0.9rem' }}>{error}</div>
        )}
        {missing.map((m) => {
          const k = m.key != null ? String(m.key) : '';
          if (!k) return null;
          return (
            <div key={k} style={{ marginBottom: '0.85rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                {m.label || k}
                {m.sensitive ? ` (${t('enforceContext.sensitive')})` : ''}
              </label>
              <input
                type={m.sensitive ? 'password' : 'text'}
                autoComplete="off"
                value={form[k] ?? ''}
                onChange={(e) => handleChange(k, e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.65rem',
                  border: '1px solid #ced4da',
                  borderRadius: 4
                }}
              />
            </div>
          );
        })}
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            style={{ ...btnBase, background: '#6c757d', color: '#fff' }}
          >
            {t('enforceContext.cancel')}
          </button>
          <button
            type="submit"
            disabled={saving}
            style={{ ...btnBase, background: '#0d6efd', color: '#fff' }}
          >
            {saving ? t('enforceContext.saving') : t('enforceContext.saveAndEnforce')}
          </button>
        </div>
      </form>
    </div>
  );
}
