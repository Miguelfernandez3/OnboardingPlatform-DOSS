/**
 * Lee `options.requireStoredDeviceBearer` desde el JSON de `context_spec`.
 */
export function isRequireStoredDeviceBearerFromSpec(contextSpec: string): boolean {
  const t = contextSpec.trim();
  if (!t) return false;
  try {
    const data = JSON.parse(t) as unknown;
    if (data == null || typeof data !== 'object' || Array.isArray(data)) return false;
    const o = data as Record<string, unknown>;
    const opts = o.options;
    if (opts == null || typeof opts !== 'object' || Array.isArray(opts)) return false;
    return Boolean((opts as Record<string, unknown>).requireStoredDeviceBearer);
  } catch {
    return false;
  }
}

function requirementsFromParsed(data: unknown): Record<string, unknown>[] {
  if (Array.isArray(data)) {
    return data.filter((x): x is Record<string, unknown> => x != null && typeof x === 'object');
  }
  if (data != null && typeof data === 'object' && !Array.isArray(data)) {
    const req = (data as Record<string, unknown>).requirements;
    if (Array.isArray(req)) {
      return req.filter((x): x is Record<string, unknown> => x != null && typeof x === 'object');
    }
  }
  return [];
}

function isBearerForAuthFlag(v: unknown): boolean {
  if (v === true) return true;
  if (typeof v === 'string' && ['1', 'true', 'yes'].includes(v.trim().toLowerCase())) return true;
  return false;
}

/**
 * Perfil Bearer sin secreto del gestor: exactamente un requisito con bearerForAuth y key no vacía.
 */
export function hasValidBearerForAuthSpec(contextSpec: string): boolean {
  const t = contextSpec.trim();
  if (!t) return false;
  try {
    const data = JSON.parse(t) as unknown;
    const list = requirementsFromParsed(data);
    const marked = list.filter(
      r => isBearerForAuthFlag(r.bearerForAuth) && String(r.key ?? '').trim().length > 0
    );
    return marked.length === 1;
  } catch {
    return false;
  }
}
