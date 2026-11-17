import { useState, useEffect } from 'react';
import { useIsMobile, useDevices } from '../../hooks';
import { userService } from '../../../infrastructure/services/userService';
import { useToast } from '../../../infrastructure/notifications/useToast';
import { UserData, DeviceAccessRule, AccessRuleKind } from '../../../core/ports';

interface AccessRulesModalProps {
  isOpen: boolean;
  user: UserData | null;
  onClose: () => void;
}

const KIND_LABEL: Record<AccessRuleKind, string> = {
  device: 'Dispositivo concreto',
  manufacturer: 'Fabricante (automático)',
  idsp: 'gDSP id (automático)',
};

/**
 * AccessRulesModal - gestiona las reglas de acceso a dispositivos de un usuario.
 * Reglas 'manufacturer'/'idsp' se evalúan al vuelo: los dispositivos que las cumplan
 * aparecen automáticamente en la lista del usuario.
 */
export default function AccessRulesModal({ isOpen, user, onClose }: AccessRulesModalProps): JSX.Element | null {
  const isMobile = useIsMobile();
  const { showApiError } = useToast();
  const { devices } = useDevices();

  const [rules, setRules] = useState<DeviceAccessRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [matchKind, setMatchKind] = useState<AccessRuleKind>('device');
  const [matchValue, setMatchValue] = useState('');

  const load = async (userId: string) => {
    setLoading(true);
    try {
      setRules(await userService.getAccessRules(userId));
    } catch (err) {
      showApiError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && user) {
      load(user.id);
      setMatchKind('device');
      setMatchValue('');
    }
  }, [isOpen, user]);

  if (!isOpen || !user) return null;

  const manufacturers = Array.from(
    new Set(devices.map((d) => d.manufacturer).filter(Boolean))
  ) as string[];

  const handleAdd = async () => {
    const value = matchValue.trim();
    if (!value) return;
    setSaving(true);
    try {
      await userService.createAccessRule(user.id, matchKind, value);
      setMatchValue('');
      await load(user.id);
    } catch (err) {
      showApiError(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (ruleId: number) => {
    try {
      await userService.deleteAccessRule(user.id, ruleId);
      await load(user.id);
    } catch (err) {
      showApiError(err);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '0.6rem',
    borderRadius: '4px',
    border: '1px solid #dee2e6',
    fontSize: '0.95rem',
    boxSizing: 'border-box' as const,
    backgroundColor: 'white',
  };

  return (
    <div
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        padding: isMobile ? '1rem' : '0',
      }}
      onMouseDown={onClose}
    >
      <div
        style={{
          backgroundColor: 'white', borderRadius: '8px',
          padding: isMobile ? '1.5rem' : '2rem', width: '100%', maxWidth: '520px',
          maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 style={{ marginTop: 0, marginBottom: '0.25rem', fontSize: isMobile ? '1.2rem' : '1.4rem' }}>
          Accesos a dispositivos
        </h2>
        <p style={{ marginTop: 0, color: '#666', fontSize: '0.9rem' }}>{user.email}</p>

        {/* Reglas actuales */}
        <div style={{ margin: '1rem 0' }}>
          {loading ? (
            <p style={{ color: '#666' }}>Cargando…</p>
          ) : rules.length === 0 ? (
            <p style={{ color: '#856404', backgroundColor: '#fff3cd', padding: '0.6rem', borderRadius: '4px', fontSize: '0.875rem' }}>
              Sin reglas: este usuario no ve ningún dispositivo.
            </p>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {rules.map((r) => (
                <span
                  key={r.id}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                    padding: '0.35rem 0.6rem', borderRadius: '16px',
                    backgroundColor: '#e7f1ff', color: '#0a58ca', fontSize: '0.8rem',
                  }}
                >
                  <strong>{KIND_LABEL[r.matchKind]}:</strong> {r.matchValue}
                  <button
                    onClick={() => handleDelete(r.id)}
                    aria-label="Eliminar regla"
                    style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#0a58ca', fontSize: '1rem', lineHeight: 1 }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Añadir regla */}
        <div style={{ borderTop: '1px solid #eee', paddingTop: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.4rem', fontWeight: 500, fontSize: '0.9rem' }}>Añadir regla</label>
          <select
            value={matchKind}
            onChange={(e) => { setMatchKind(e.target.value as AccessRuleKind); setMatchValue(''); }}
            style={{ ...inputStyle, marginBottom: '0.6rem' }}
          >
            <option value="device">{KIND_LABEL.device}</option>
            <option value="manufacturer">{KIND_LABEL.manufacturer}</option>
            <option value="idsp">{KIND_LABEL.idsp}</option>
          </select>

          {matchKind === 'device' && (
            <select value={matchValue} onChange={(e) => setMatchValue(e.target.value)} style={inputStyle}>
              <option value="">Selecciona un dispositivo…</option>
              {devices.map((d) => (
                <option key={d.id} value={d.identifier || d.id}>
                  {d.name || d.identifier || d.id}{d.manufacturer ? ` — ${d.manufacturer}` : ''}
                </option>
              ))}
            </select>
          )}

          {matchKind === 'manufacturer' && (
            <>
              <input
                list="am-manufacturers"
                value={matchValue}
                onChange={(e) => setMatchValue(e.target.value)}
                placeholder="p. ej. Cisco"
                style={inputStyle}
              />
              <datalist id="am-manufacturers">
                {manufacturers.map((m) => <option key={m} value={m} />)}
              </datalist>
            </>
          )}

          {matchKind === 'idsp' && (
            <select value={matchValue} onChange={(e) => setMatchValue(e.target.value)} style={inputStyle}>
              <option value="">Selecciona un gDSP id…</option>
              {Array.from(new Set(devices.map((d) => d.inventory_id).filter(Boolean))).map((v) => (
                <option key={v as string} value={v as string}>{v as string}</option>
              ))}
            </select>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem' }}>
            <button
              onClick={onClose}
              style={{ padding: '0.6rem 1.25rem', borderRadius: '4px', border: '1px solid #dee2e6', backgroundColor: 'white', cursor: 'pointer' }}
            >
              Cerrar
            </button>
            <button
              onClick={handleAdd}
              disabled={saving || !matchValue.trim()}
              style={{
                padding: '0.6rem 1.25rem', borderRadius: '4px', border: 'none', color: 'white',
                backgroundColor: (saving || !matchValue.trim()) ? '#6c757d' : '#28a745',
                cursor: (saving || !matchValue.trim()) ? 'not-allowed' : 'pointer',
              }}
            >
              {saving ? 'Añadiendo…' : 'Añadir'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
