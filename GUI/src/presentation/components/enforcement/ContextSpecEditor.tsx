import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import * as s from './styles';

type RequirementRow = {
  key: string;
  label: string;
  source: string;
  sensitive: boolean;
  optional: boolean;
  bearerForAuth: boolean;
};

const emptyRow = (): RequirementRow => ({
  key: '',
  label: '',
  source: 'device',
  sensitive: false,
  optional: false,
  bearerForAuth: false
});

function parseContextSpec(
  value: string
):
  | { ok: true; requireStored: boolean; requirements: RequirementRow[]; hadOtherKeys: boolean }
  | { ok: false; error: string } {
  const trimmed = value.trim();
  if (!trimmed) {
    return { ok: true, requireStored: false, requirements: [], hadOtherKeys: false };
  }
  try {
    const data = JSON.parse(trimmed) as unknown;
    if (Array.isArray(data)) {
      const requirements = data
        .filter((x): x is Record<string, unknown> => x != null && typeof x === 'object')
        .map(x => ({
          key: String(x.key ?? ''),
          label: String(x.label ?? ''),
          source: String(x.source ?? 'device'),
          sensitive: Boolean(x.sensitive),
          optional: Boolean(x.optional),
          bearerForAuth: Boolean(x.bearerForAuth)
        }));
      return { ok: true, requireStored: false, requirements, hadOtherKeys: false };
    }
    if (data != null && typeof data === 'object') {
      const o = data as Record<string, unknown>;
      const opts = o.options;
      const requireStored =
        opts != null && typeof opts === 'object' && 'requireStoredDeviceBearer' in opts
          ? Boolean((opts as Record<string, unknown>).requireStoredDeviceBearer)
          : false;
      const req = o.requirements;
      const requirements: RequirementRow[] = Array.isArray(req)
        ? req
            .filter((x): x is Record<string, unknown> => x != null && typeof x === 'object')
            .map(x => ({
              key: String(x.key ?? ''),
              label: String(x.label ?? ''),
              source: String(x.source ?? 'device'),
              sensitive: Boolean(x.sensitive),
              optional: Boolean(x.optional),
              bearerForAuth: Boolean(x.bearerForAuth)
            }))
        : [];
      const hadOtherKeys = Object.keys(o).some(k => k !== 'options' && k !== 'requirements');
      return { ok: true, requireStored, requirements, hadOtherKeys };
    }
    return { ok: false, error: 'notObject' };
  } catch {
    return { ok: false, error: 'json' };
  }
}

function serialize(
  requireStored: boolean,
  requirements: RequirementRow[],
  includeBearerFlags: boolean
): string {
  const spec: Record<string, unknown> = {
    options: { requireStoredDeviceBearer: requireStored },
    requirements: requirements.map(r => ({
      key: r.key.trim(),
      ...(r.label.trim() ? { label: r.label.trim() } : {}),
      ...(r.source.trim() ? { source: r.source.trim() } : { source: 'device' }),
      ...(r.sensitive ? { sensitive: true } : {}),
      ...(r.optional ? { optional: true } : {}),
      ...(includeBearerFlags && r.bearerForAuth ? { bearerForAuth: true } : {})
    }))
  };
  return JSON.stringify(spec, null, 2);
}

interface ContextSpecEditorProps {
  value: string;
  onChange: (next: string) => void;
  /** Bearer sin secreto del gestor: mostrar columna para elegir la clave de contexto del token. */
  showBearerKeyColumn?: boolean;
}

/**
 * Edición estructurada de context_spec (requisitos + opciones) con vista JSON avanzada opcional.
 */
export default function ContextSpecEditor({
  value,
  onChange,
  showBearerKeyColumn = false
}: ContextSpecEditorProps): JSX.Element {
  const { t } = useTranslation();
  const [rawMode, setRawMode] = useState(false);
  const [rawText, setRawText] = useState(value);
  const [requireStored, setRequireStored] = useState(false);
  const [requirements, setRequirements] = useState<RequirementRow[]>([]);
  const [initError, setInitError] = useState<string | null>(null);
  const prevShowBearerKeyColumnRef = useRef(showBearerKeyColumn);

  useEffect(() => {
    setRawText(value);
    if (rawMode) {
      return;
    }
    const p = parseContextSpec(value);
    if (!p.ok) {
      setInitError(p.error);
      setRawMode(true);
      return;
    }
    setInitError(null);
    setRequireStored(p.requireStored);
    setRequirements(p.requirements.length > 0 ? p.requirements : []);
    if (p.hadOtherKeys) {
      setRawMode(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- rawMode read inside but must not retrigger
  }, [value]);

  /**
   * Al ocultar la columna Bearer (p. ej. al elegir secreto del gestor), el JSON debe pasar a
   * serialize(..., includeBearerFlags=false). No usar un efecto amplio value↔requirements: en el mismo
   * tick el segundo efecto veía requirements obsoleto y machacaba context_spec (parpadeo / bucle).
   */
  useEffect(() => {
    if (rawMode) return;
    const prev = prevShowBearerKeyColumnRef.current;
    prevShowBearerKeyColumnRef.current = showBearerKeyColumn;
    if (prev === true && showBearerKeyColumn === false) {
      const next = serialize(requireStored, requirements, false);
      if (next !== value) {
        onChange(next);
      }
    }
  }, [showBearerKeyColumn, rawMode, requireStored, requirements, value, onChange]);

  const pushChange = (nextRequire: boolean, nextReq: RequirementRow[]) => {
    onChange(serialize(nextRequire, nextReq, showBearerKeyColumn));
  };

  const handleRequireChange = (checked: boolean) => {
    setRequireStored(checked);
    pushChange(checked, requirements);
  };

  const updateRow = (i: number, patch: Partial<RequirementRow>) => {
    const next = requirements.map((r, j) => (j === i ? { ...r, ...patch } : r));
    setRequirements(next);
    pushChange(requireStored, next);
  };

  const setBearerRowOnly = (i: number) => {
    const next = requirements.map((r, j) => ({ ...r, bearerForAuth: j === i }));
    setRequirements(next);
    pushChange(requireStored, next);
  };

  const addRow = () => {
    const next = [...requirements, emptyRow()];
    setRequirements(next);
    pushChange(requireStored, next);
  };

  const removeRow = (i: number) => {
    const next = requirements.filter((_, j) => j !== i);
    setRequirements(next);
    pushChange(requireStored, next);
  };

  const handleRawBlur = () => {
    onChange(rawText);
    const p = parseContextSpec(rawText);
    if (p.ok) {
      setInitError(null);
    } else {
      setInitError(p.error);
    }
  };

  const tryBackToForm = () => {
    const p = parseContextSpec(rawText);
    if (p.ok) {
      setInitError(null);
      onChange(rawText);
      setRequireStored(p.requireStored);
      setRequirements(p.requirements.length > 0 ? p.requirements : []);
      setRawMode(false);
    } else {
      setInitError(p.error);
    }
  };

  if (rawMode) {
    return (
      <div>
        {initError != null && (
          <p style={{ color: '#856404', fontSize: '0.875rem', margin: '0 0 0.5rem 0' }}>
            {initError === 'json'
              ? t('enforcementAdmin.profiles.contextSpecInvalidJson')
              : t('enforcementAdmin.profiles.contextSpecInvalidShape')}
          </p>
        )}
        <div style={s.formLabel}>{t('enforcementAdmin.profiles.contextSpec')}</div>
        <textarea
          style={{ ...s.textarea, minHeight: '120px', fontFamily: 'monospace', fontSize: '0.8125rem' }}
          value={rawText}
          onChange={e => setRawText(e.target.value)}
          onBlur={handleRawBlur}
          rows={8}
        />
        <div style={s.optionHint}>{t('enforcementAdmin.profiles.contextSpecJsonAdvancedHint')}</div>
        <button type="button" style={s.btnSecondary} onClick={tryBackToForm}>
          {t('enforcementAdmin.profiles.contextSpecBackToForm')}
        </button>
      </div>
    );
  }

  return (
    <div>
      <div style={s.optionsCard}>
        <div style={{ ...s.optionItem, gap: '0.375rem', marginBottom: 0 }}>
          <label style={s.optionLabel}>
            <input
              type="checkbox"
              checked={requireStored}
              onChange={e => handleRequireChange(e.target.checked)}
            />{' '}
            {t('enforcementAdmin.profiles.requireStoredDeviceBearer')}
          </label>
          <div style={s.optionHintFlush}>{t('enforcementAdmin.profiles.requireStoredDeviceBearerHint')}</div>
        </div>
      </div>
      <div style={s.contextRequirementsSection}>
        <div style={s.formLabel}>{t('enforcementAdmin.profiles.contextRequirements')}</div>
        {showBearerKeyColumn && (
          <p style={{ ...s.optionHintFlush, marginBottom: '0.5rem' }}>
            {t('enforcementAdmin.profiles.reqBearerFieldHint')}
          </p>
        )}
        <div style={s.contextSpecTableWrap}>
          <table style={s.contextSpecTable}>
            <colgroup>
              {showBearerKeyColumn ? (
                <>
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '18%' }} />
                  <col style={{ width: '16%' }} />
                  <col style={{ width: '8%' }} />
                  <col style={{ width: '10%' }} />
                  <col style={{ width: '18%' }} />
                </>
              ) : (
                <>
                  <col style={{ width: '26%' }} />
                  <col style={{ width: '26%' }} />
                  <col style={{ width: '22%' }} />
                  <col style={{ width: '10%' }} />
                  <col style={{ width: '16%' }} />
                </>
              )}
            </colgroup>
            <thead>
              <tr>
                <th style={s.contextSpecTh}>{t('enforcementAdmin.profiles.reqKey')}</th>
                <th style={s.contextSpecTh}>{t('enforcementAdmin.profiles.reqLabel')}</th>
                <th style={s.contextSpecTh}>{t('enforcementAdmin.profiles.reqSource')}</th>
                <th style={{ ...s.contextSpecTh, textAlign: 'center' }}>{t('enforcementAdmin.profiles.reqSensitive')}</th>
                {showBearerKeyColumn && (
                  <th style={{ ...s.contextSpecTh, textAlign: 'center' }}>
                    {t('enforcementAdmin.profiles.reqBearerField')}
                  </th>
                )}
                <th style={s.contextSpecTh} aria-hidden />
              </tr>
            </thead>
            <tbody>
              {requirements.map((row, i) => (
                <tr key={i}>
                  <td style={s.contextSpecTd}>
                    <input
                      style={s.contextSpecRowInput}
                      value={row.key}
                      onChange={e => updateRow(i, { key: e.target.value })}
                    />
                  </td>
                  <td style={s.contextSpecTd}>
                    <input
                      style={s.contextSpecRowInput}
                      value={row.label}
                      onChange={e => updateRow(i, { label: e.target.value })}
                    />
                  </td>
                  <td style={s.contextSpecTd}>
                    <input
                      style={s.contextSpecRowInput}
                      value={row.source}
                      onChange={e => updateRow(i, { source: e.target.value })}
                    />
                  </td>
                  <td style={{ ...s.contextSpecTd, textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      checked={row.sensitive}
                      onChange={e => updateRow(i, { sensitive: e.target.checked })}
                    />
                  </td>
                  {showBearerKeyColumn && (
                    <td style={{ ...s.contextSpecTd, textAlign: 'center' }}>
                      <input
                        type="radio"
                        name="context-spec-bearer-field"
                        checked={row.bearerForAuth}
                        onChange={() => setBearerRowOnly(i)}
                        aria-label={t('enforcementAdmin.profiles.reqBearerField')}
                      />
                    </td>
                  )}
                  <td style={s.contextSpecTd}>
                    <button type="button" style={s.contextReqRemoveBtn} onClick={() => removeRow(i)}>
                      {t('enforcementAdmin.profiles.reqRemove')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={s.contextSpecActionsRow}>
          <button type="button" style={s.btnSuccess} onClick={addRow}>
            {t('enforcementAdmin.profiles.reqAdd')}
          </button>
          <button
            type="button"
            style={s.btnSecondary}
            onClick={() => {
              setRawText(value);
              setRawMode(true);
            }}
          >
            {t('enforcementAdmin.profiles.contextSpecOpenJson')}
          </button>
        </div>
        <div style={s.contextSpecFooterHint}>{t('enforcementAdmin.profiles.contextSpecFormHint')}</div>
      </div>
    </div>
  );
}
